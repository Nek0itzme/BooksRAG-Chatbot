# -*- coding: utf-8 -*-
"""
rag_engine.py — Trái tim của hệ thống RAG
# [AI-Assisted Code] Prompt #04 — Tích hợp Hybrid Search (Dense + Sparse Lexical),
# Author Routing & Anti-Hallucination Gate theo plan.md §3.1 & §3.2:
  1. Intent Parser & Author Detection (Gemini 2.5 Flash + Local Rule Gate)
  2. Hard Filtering Gate              (in_stock, rating >= 2.0, price <= budget)
  3. Hybrid Semantic Search           (70% ChromaDB Cosine + 30% Sparse Lexical/Category)
  4. Hybrid Scoring                   (Score_Total = α·Sem + (1-α)·Rank)
  5. Author Recommendation            (In-session personalization)
"""

import json
import math
import re
import time
import unicodedata
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    SAMPLE_JSON,
    CHROMA_PERSIST,
    CHROMA_COLLECTION,
    EMBEDDING_MODEL,
    ALPHA,
    W_RATING, W_SALES, W_QUALITY,
    MIN_RATING,
    DEFAULT_BUDGET,
    TOP_K,
    CHROMA_N_RESULTS,
    AUTHOR_REC_COUNT,
)
from gemini_client import parse_intent, generate_answer, combined_gemini_call, analyze_book_image

# Tích hợp bộ quy tắc Rule Harness (RAG Rules)
import sys
from pathlib import Path
_RAG_RULES_DIR = Path(__file__).parent.parent / "RAG Rules"
if str(_RAG_RULES_DIR) not in sys.path:
    sys.path.insert(0, str(_RAG_RULES_DIR))

try:
    from rule_harness import InputRuleHarness, OutputRuleHarness
except Exception:
    InputRuleHarness = None
    OutputRuleHarness = None

# ── Tích hợp HyPE Filter (Hyperbolic Poincaré Entailment) ────────────────────
try:
    from hype_filter import get_hype_filter
    _HYPE_ENABLED = True
except Exception as _hype_err:
    _HYPE_ENABLED = False
    print(f"[WARN] HyPE Filter không load được: {_hype_err}")


# ─────────────────────────────────────────────────────────────────────────────
# Khởi tạo (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────

_embedder: Optional[SentenceTransformer] = None
_chroma_collection = None
_books_cache: list[dict] = []          # toàn bộ sách từ sample.json
_author_index: dict[str, str] = {}     # chữ thường -> tên tác giả chuẩn
_sold_count_max: int = 1               # để tính log-normalize


def _remove_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để hỗ trợ khớp chuỗi khi user gõ không dấu (vd: 'Nguyen Nhat Anh')."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(c for c in norm if unicodedata.category(c) != "Mn").lower()


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST)
        _chroma_collection = client.get_collection(CHROMA_COLLECTION)
    return _chroma_collection


def _get_books() -> list[dict]:
    global _books_cache, _sold_count_max, _author_index
    if not _books_cache:
        with open(SAMPLE_JSON, encoding="utf-8") as f:
            raw_data = json.load(f)
        _books_cache = raw_data.get("data", raw_data) if isinstance(raw_data, dict) else raw_data
        _sold_count_max = max(b.get("sold_count", 1) for b in _books_cache) or 1

        # Xây dựng chỉ mục tác giả (có dấu & không dấu)
        _author_index = {}
        for b in _books_cache:
            author_full = b.get("author", "").strip()
            if not author_full:
                continue
            _author_index[author_full.lower()] = author_full
            _author_index[_remove_accents(author_full)] = author_full
            for sub_a in author_full.split(","):
                sub_a = sub_a.strip()
                # Chỉ lấy cụm tác giả con nếu có từ 2 từ trở lên hoặc độ dài >= 5 để tránh từ đơn như 'cha'
                if len(sub_a) >= 5 and len(sub_a.split()) >= 2:
                    _author_index[sub_a.lower()] = author_full
                    _author_index[_remove_accents(sub_a)] = author_full
    return _books_cache


def is_chroma_ready() -> bool:
    try:
        col = _get_collection()
        return col.count() > 0
    except Exception:
        return False


def is_author_negated(message: str, author: str) -> bool:
    """Kiểm tra xem tác giả được nhắc tới trong ngữ cảnh phủ định / loại trừ hay không."""
    if not author or not message:
        return False
    msg_low = message.lower()
    auth_low = author.lower()
    auth_no_acc = _remove_accents(author)
    msg_no_acc = _remove_accents(message)

    patterns = [
        rf"(?:ngoài|trừ|không\s+(?:phải|muốn|thích|đọc|lấy|xem)|khác\s+(?:với|ngoài)?)\s*(?:nhà\s*văn|tác\s*giả)?\s*{re.escape(auth_low)}",
        rf"{re.escape(auth_low)}\s*(?:thôi|chán|không\s*đọc|không\s*mua|không\s*thích|ra)",
        rf"(?:tác\s*giả|sách)\s*khác.*{re.escape(auth_low)}",
        rf"đổi\s*(?:sang|qua)?.*{re.escape(auth_low)}",
        rf"không\s+.*{re.escape(auth_low)}",
    ]
    for p in patterns:
        if re.search(p, msg_low):
            return True
        p_no_acc = _remove_accents(p)
        if re.search(p_no_acc, msg_no_acc):
            return True
    return False


def extract_recent_author_from_history(session_history: list[dict]) -> Optional[str]:
    """Trích xuất tác giả được nhắc đến gần nhất trong lịch sử hội thoại."""
    if not session_history:
        return None
    _get_books()
    for item in reversed(session_history[-6:]):
        text = item.get("content", "")
        auth = detect_author(text, check_negation=False)
        if auth:
            return auth
    return None


def is_query_asking_for_different_book_or_author(message: str) -> bool:
    """Nhận diện các mẫu câu hỏi yêu cầu đổi sách/đổi tác giả/sách khác."""
    msg_low = message.lower()
    msg_no_acc = _remove_accents(message)
    patterns = [
        r"\bsách khác\b", r"\btác giả khác\b", r"\bcuốn khác\b", r"\bkhác đi\b",
        r"\bngười khác\b", r"\bngoài\b", r"\bkhông lấy\b", r"\bđổi sang\b",
        r"\bkhông xem.*nữa\b", r"\bcòn ai khác\b", r"\bthể loại khác\b",
        r"\bchủ đề khác\b", r"\bkhác nữa không\b", r"\bgiới thiệu.*khác\b",
        r"\btác phẩm khác\b",
    ]
    for p in patterns:
        if re.search(p, msg_low) or re.search(p, msg_no_acc):
            return True
    return False


COMMON_VN_STOPWORDS = {"cha", "con", "anh", "em", "ong", "ba", "me", "toi", "nam", "nu", "hoa", "tam", "minh", "quang", "kim", "dong", "sach"}


def detect_author(query: str, intent_author: Optional[str] = None, check_negation: bool = True) -> Optional[str]:
    """Nhận diện tên tác giả có trong kho sách (hỗ trợ cả có dấu và không dấu, sử dụng regex word boundary)."""
    _get_books()
    candidates = []
    if intent_author:
        candidates.append(intent_author)
    candidates.append(query)

    has_author_cue = bool(re.search(r"(?:tác giả|nhà văn|sách của|viết bởi|của)\s+", query.lower()))
    sorted_keys = sorted(_author_index.keys(), key=len, reverse=True)
    for text in candidates:
        t_low = text.lower()
        t_no_acc = _remove_accents(text)
        for k in sorted_keys:
            k_no_acc = _remove_accents(k)
            if k_no_acc in COMMON_VN_STOPWORDS and not has_author_cue:
                continue
            if len(k) < 3:
                continue

            # Sử dụng word-boundary \b để không bị khớp nhầm vào từ khác (vd: 'cha' trong 'chăn cừu')
            pattern = rf"\b{re.escape(k)}\b"
            pattern_no_acc = rf"\b{re.escape(k_no_acc)}\b"
            if re.search(pattern, t_low) or re.search(pattern_no_acc, t_no_acc):
                found_author = _author_index[k]
                if check_negation and is_author_negated(query, found_author):
                    continue
                return found_author
    return None


def extract_topic_keywords(query: str, exclude_author: Optional[str] = None) -> list[str]:
    """Trích xuất từ khóa nội dung/chủ đề cốt lõi, loại bỏ từ dừng và tên tác giả."""
    q = query.lower()
    if exclude_author:
        q = q.replace(exclude_author.lower(), " ")
        q_no_acc = _remove_accents(q)
        auth_no_acc = _remove_accents(exclude_author)
        if auth_no_acc in q_no_acc:
            # Xóa tên tác giả không dấu nếu user gõ không dấu
            for token in auth_no_acc.split():
                q = re.sub(r"\b" + re.escape(token) + r"\b", " ", q)

    # Xóa cụm ngân sách khỏi từ khóa tìm kiếm (vd: "giá dưới 100k", "100000đ")
    q = re.sub(r"(giá\s*)?(dưới|tầm|khoảng|tối đa|<|<=)?\s*\d+\s*(k|nghìn|ngàn|đ|vnd|đồng)\b", " ", q)

    compound_vocab = [
        "chiến tranh", "kinh tế", "tâm lý học", "tâm lý", "trinh thám", "kho báu",
        "kim tự tháp", "chăn cừu", "sa mạc", "bão tuyết", "án mạng", "chữa lành",
        "khởi nghiệp", "tài chính", "vũ trụ", "lỗ đen", "tuổi thơ", "học trò",
        "kinh doanh", "lãng mạn", "quản trị", "thiếu nhi", "kỹ năng sống",
        "bí quyết trúng số", "trúng số",
    ]
    found_compounds = []
    for cp in compound_vocab:
        if cp in q or _remove_accents(cp) in _remove_accents(q):
            found_compounds.append(cp)
            q = q.replace(cp, " ")

    stop_words = {
        "sách", "cuốn", "tác", "phẩm", "truyện", "tiểu", "thuyết", "cho", "tôi",
        "mình", "bạn", "các", "những", "một", "vài", "của", "về", "ở", "đi", "tìm",
        "kiếm", "muốn", "xem", "có", "là", "và", "với", "trong", "thêm", "nhé",
        "ạ", "giúp", "nào", "gì", "xin", "hay", "nhất", "dễ", "hiểu", "giá", "bao",
        "nhiêu", "tiền", "tác", "giả", "nhà", "văn", "viết", "kể", "nhớ", "mang",
        "máng", "cậu", "bé", "người", "đọc", "gợi", "ý", "tư", "vấn", "mua",
        "cua", "sach", "cuon", "gia", "bao", "nhieu",
    }

    words = re.findall(r"\w+", q)
    unigrams = [w for w in words if len(w) > 1 and w not in stop_words and not w.isdigit()]
    return found_compounds + unigrams


# ─────────────────────────────────────────────────────────────────────────────
# Bước 2 — Hard Filtering Gate  (plan.md §3.2 Giai đoạn 1)
# ─────────────────────────────────────────────────────────────────────────────

def hard_filter(books: list[dict], budget: int, min_rating: float) -> list[dict]:
    """
    Eligible(b) = 1 nếu:
      b.in_stock == True
      AND b.rating >= min_rating
      AND b.price <= budget
    """
    return [
        b for b in books
        if b.get("in_stock", True)
        and float(b.get("rating", 0)) >= min_rating
        and int(b.get("price", 0)) <= budget
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Bước 4 — Hybrid Scoring  (plan.md §3.2 Giai đoạn 2)
# ─────────────────────────────────────────────────────────────────────────────

def score_rating(book: dict) -> float:
    """R̂(b) = (rating - 1.0) / 4.0"""
    r = float(book.get("rating", 1.0))
    return max(0.0, min(1.0, (r - 1.0) / 4.0))


def score_sales(book: dict) -> float:
    """Ŝ(b) = log(1 + sold_count) / log(1 + sold_count_max)"""
    s = int(book.get("sold_count", 0))
    if _sold_count_max <= 0:
        return 0.0
    return math.log1p(s) / math.log1p(_sold_count_max)


def score_review_quality(book: dict) -> float:
    """
    Q(b) = (valid_reviews / total_reviews) * min(1.0, valid_reviews / 10)
    """
    total = int(book.get("total_reviews", 0))
    valid = int(book.get("valid_reviews", 0))
    if total == 0:
        return 0.0
    ratio = valid / total
    confidence = min(1.0, valid / 10)
    return ratio * confidence


def score_ranking(book: dict) -> float:
    """
    Score_Ranking(b) = w_r·R̂ + w_s·Ŝ + w_q·Q
    """
    return (
        W_RATING  * score_rating(book) +
        W_SALES   * score_sales(book) +
        W_QUALITY * score_review_quality(book)
    )


def hybrid_score(semantic: float, book: dict) -> float:
    """
    Score_Total = α·Score_Semantic + (1-α)·Score_Ranking
    """
    return ALPHA * semantic + (1 - ALPHA) * score_ranking(book)


# ─────────────────────────────────────────────────────────────────────────────
# Bước 5 — Author Recommendation  (plan.md §3.1 in-session)
# ─────────────────────────────────────────────────────────────────────────────

def get_author_recommendations(purchased_book_id: str, exclude_ids: list[str] = None) -> list[dict]:
    """
    Khi user mua 1 cuốn sách → gợi ý thêm AUTHOR_REC_COUNT tác phẩm của cùng tác giả.
    """
    books = _get_books()
    purchased = next((b for b in books if b["id"] == purchased_book_id), None)
    if not purchased:
        return []

    author = purchased["author"]
    exclude = set(exclude_ids or []) | {purchased_book_id}

    same_author = [
        b for b in books
        if b["author"] == author
        and b["id"] not in exclude
        and b.get("in_stock", True)
    ]
    same_author.sort(key=lambda b: float(b.get("rating", 0)), reverse=True)
    return same_author[:AUTHOR_REC_COUNT]


# ─────────────────────────────────────────────────────────────────────────────
# Main RAG Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_rag(
    message: str,
    budget: Optional[int] = None,
    session_history: list[dict] = None,
    purchased_book_id: Optional[str] = None,
    image_data: Optional[str] = None,
) -> dict:
    """
    Toàn bộ pipeline RAG 5 bước theo plan.md + Multimodal Vision nhận diện sách.
    """
    timings = {}
    t_total = time.time()
    original_message = message

    # ── [Vision Analysis] Nhận diện thông tin sách từ ảnh nếu có ──
    vision_info = None
    direct_image_matches = []
    if image_data:
        t_v0 = time.time()
        vision_info = analyze_book_image(image_data, user_prompt=message)
        timings["vision_ms"] = round((time.time() - t_v0) * 1000)

        det_title = vision_info.get("detected_title")
        det_author = vision_info.get("detected_author")
        det_genre = vision_info.get("genre")
        det_text = vision_info.get("detected_text", "")

        # Kiểm tra khớp trực tiếp trong kho sách
        all_books_cache = _get_books()
        if det_title:
            d_raw = det_title.strip()
            d_no_acc = _remove_accents(d_raw.lower())
            if len(d_no_acc) >= 3:
                for b in all_books_cache:
                    b_no_acc = _remove_accents(b.get("title", "").lower().strip())
                    if d_no_acc == b_no_acc or (len(d_no_acc) >= 6 and (d_no_acc in b_no_acc or b_no_acc in d_no_acc)):
                        direct_image_matches.append(b)

        # Bổ sung thông tin nhận diện vào truy vấn để LLM nắm rõ bối cảnh ảnh
        v_parts = []
        if det_title:
            v_parts.append(f"Tựa sách trong ảnh: '{det_title}'")
        if det_author:
            v_parts.append(f"Tác giả: {det_author}")
        if det_genre:
            v_parts.append(f"Thể loại: {det_genre}")
        if det_text:
            v_parts.append(f"Chữ trên bìa: {det_text[:120]}")

        prefix_str = " | ".join(v_parts)
        if prefix_str:
            message = f"[ẢNH BÌA SÁCH NHẬN DIỆN: {prefix_str}] {message}"

    # ── [Harness Gate 0] Kiểm duyệt an toàn đầu vào qua InputRuleHarness ──
    if InputRuleHarness:
        rule_eval = InputRuleHarness.evaluate(message)
        if not rule_eval["passed"]:
            timings["total_ms"] = round((time.time() - t_total) * 1000)
            return {
                "answer": rule_eval["response"],
                "books": [],
                "author_recs": [],
                "query_type": "rule_harness_blocked",
                "found": False,
                "latency_ms": timings,
                "vision_info": vision_info,
            }

    # ── [Harness Gate 0B] is_underspecified — hỏi lại nếu query quá mơ hồ ──
    # Chỉ kiểm tra khi: không có ảnh, query đủ ngắn (< 10 từ), không có ngân sách/tác giả rõ ràng
    if _HYPE_ENABLED and not image_data and len(message.split()) < 10:
        try:
            _hype_check = get_hype_filter(_get_embedder())
            if _hype_check.is_underspecified(message, threshold=0.12):
                timings["total_ms"] = round((time.time() - t_total) * 1000)
                return {
                    "answer": (
                        "📚 Bạn ơi, câu hỏi này còn khá mơ hồ — tôi có thể gợi ý chính xác hơn nếu bạn "
                        "cung cấp thêm thông tin như:\n\n"
                        "• **Chủ đề / thể loại**: Văn học, Tâm lý, Kinh tế, Thiếu nhi...?\n"
                        "• **Cảm xúc bạn muốn**: Chữa lành, truyện cảm hứng, giải trí, học hỏi...?\n"
                        "• **Ngân sách**: Dưới bao nhiêu đồng?\n"
                        "• **Đối tượng**: Sách cho trẻ em, teen hay người lớn?\n\n"
                        "Ngoài ra bạn có thể mô tả cốt truyện nhớ máng hoặc tải ảnh bìa sách lên — tôi sẽ tìm ngươi ấy! ✨"
                    ),
                    "books": [],
                    "author_recs": [],
                    "query_type": "underspecified",
                    "query_context": "Câu hỏi cần làm rõ thêm",
                    "found": False,
                    "latency_ms": timings,
                    "vision_info": vision_info,
                }
        except Exception:
            pass  # Nếu HyPE bỏ qua → tiếp tục pipeline bình thường

    # Trích xuất ngân sách tự động từ câu hỏi nếu người dùng gõ "dưới 100k"
    regex_budget = None
    m_budget = re.search(r"(?:dưới|tầm|khoảng|tối đa|<|<=)\s*(\d+)\s*(k|nghìn|ngàn|đ|vnd|đồng)?", message.lower())
    if m_budget:
        val = int(m_budget.group(1))
        unit = m_budget.group(2) or ""
        regex_budget = val * 1000 if (unit in ("k", "nghìn", "ngàn") or val < 1000) else val

    recent_author = extract_recent_author_from_history(session_history)
    asking_different = is_query_asking_for_different_book_or_author(message)

    # Kiểm tra tác giả trong câu hỏi hiện tại
    raw_author = detect_author(message, check_negation=False)
    if raw_author and is_author_negated(message, raw_author):
        exclude_author = raw_author
        detected_author = None
    elif asking_different and recent_author:
        exclude_author = recent_author
        detected_author = raw_author if (raw_author and raw_author != recent_author) else None
    else:
        exclude_author = None
        detected_author = detect_author(message, check_negation=True)

    # ── Bước 1: Intent Parser (heuristic — không tốn Gemini call) ───────────
    # FIX #1: Intent giờ được trích xuất bên trong combined_gemini_call (cuối pipeline)
    # Ở đây chỉ xây intent sơ bộ bằng heuristic để quyết định routing
    t0 = time.time()
    if detected_author and not exclude_author and not asking_different:
        intent = {
            "query_type": "by_author",
            "semantic_query": message,
            "keywords": [],
            "budget_max": regex_budget or DEFAULT_BUDGET,
            "min_rating": MIN_RATING,
            "category": None,
            "author": detected_author,
            "exclude_author": None,
            "is_topic_switch": False,
            "age_group": None,
            "mood": None,
            "is_halluc_trap": False,
        }
    else:
        # Chỉ gọi parse_intent khi cần thiết để author routing hoạt động đúng
        intent = parse_intent(message, session_history or [])
        if intent.get("exclude_author") and not exclude_author:
            exclude_author = intent.get("exclude_author")
        if (intent.get("is_topic_switch") or asking_different) and recent_author and not exclude_author:
            exclude_author = recent_author

        cand_author = intent.get("author") or detect_author(message, check_negation=True)
        if cand_author and (cand_author == exclude_author or is_author_negated(message, cand_author)):
            detected_author = None
        else:
            detected_author = cand_author
    timings["intent_ms"] = round((time.time() - t0) * 1000)

    effective_budget = budget or regex_budget or intent.get("budget_max") or DEFAULT_BUDGET
    min_rating_req   = float(intent.get("min_rating") or MIN_RATING)

    # ── Bước 2: Hard Filtering Gate ──────────────────────────────────────
    t0 = time.time()
    all_books = _get_books()
    eligible  = hard_filter(all_books, effective_budget, min_rating_req)
    if exclude_author:
        eligible = [b for b in eligible if b.get("author") != exclude_author]
    timings["filter_ms"] = round((time.time() - t0) * 1000)

    if not eligible:
        return {
            "answer": (
                "📚 Rất tiếc, hiện kho sách chưa có cuốn nào đáp ứng đầy đủ "
                "điều kiện ngân sách và đánh giá bạn yêu cầu. "
                "Bạn thử điều chỉnh ngân sách hoặc mức sao tối thiểu nhé!"
            ),
            "books": [],
            "author_recs": [],
            "query_type": intent.get("query_type", "by_budget"),
            "query_context": f"Ngân sách ≤ {effective_budget:,.0f}đ".replace(",", "."),
            "found": False,
            "latency_ms": timings,
        }

    # ── Bước 2B: Kiểm tra Tác giả & Chống Hallucination (Author Routing) ──
    if detected_author == exclude_author or (detected_author and is_author_negated(original_message, detected_author)):
        detected_author = None
    topic_kws = extract_topic_keywords(original_message, exclude_author=detected_author or exclude_author)

    # Xác định ngữ cảnh tìm kiếm hiển thị cho thanh bên phải
    if image_data:
        if direct_image_matches:
            query_context = f"Ảnh bìa: {direct_image_matches[0]['title'][:24]}"
        elif vision_info and vision_info.get("detected_title"):
            query_context = f"Ảnh bìa: {vision_info['detected_title'][:24]}"
        else:
            query_context = "Tìm theo ảnh bìa"
    elif detected_author:
        query_context = f"Tác giả: {detected_author}"
    elif intent.get("category"):
        query_context = f"Thể loại: {intent['category'].title()}"
    elif exclude_author:
        query_context = f"Gợi ý mới (ngoài {exclude_author})"
    elif budget or regex_budget:
        b_val = budget or regex_budget
        query_context = f"Ngân sách ≤ {b_val:,.0f}đ".replace(",", ".")
    elif intent.get("age_group"):
        query_context = f"Độ tuổi: {intent['age_group']}"
    else:
        query_context = "Gợi ý phù hợp nhất"

    # Nếu câu hỏi nhắc tới một tác giả có trong kho (VD: "Nguyễn Nhật Ánh")
    if detected_author:
        author_books = [b for b in eligible if b.get("author") == detected_author]

        # Nếu Gemini phát hiện câu bẫy Hallucination (VD: "Bí quyết trúng số của Nguyễn Nhật Ánh")
        if intent.get("is_halluc_trap") and not direct_image_matches:
            available_titles = ", ".join(f"**{b['title']}**" for b in author_books[:4])
            return {
                "answer": (
                    f"📚 Tôi đã tra cứu kỹ kho sách nhưng tác giả **{detected_author}** "
                    f"**không có** tác phẩm nào như vậy trong hệ thống. "
                    f"Có thể tên sách hoặc thông tin kết hợp chưa chính xác.\n\n"
                    f"✨ Bạn có thể tham khảo các tác phẩm chính thức của **{detected_author}** "
                    f"hiện có trong kho: {available_titles}."
                ),
                "books": [],
                "author_recs": author_books[:AUTHOR_REC_COUNT],
                "query_type": "anti_halluc",
                "query_context": query_context,
                "found": False,
                "latency_ms": timings,
            }

        # Kiểm tra xem user có hỏi kèm tên sách/chủ đề cụ thể không
        if direct_image_matches:
            author_books = direct_image_matches
        elif topic_kws:
            matched_author_books = []
            for b in author_books:
                b_text = f"{b['title']} {b.get('category', '')} {b.get('description', '')} {' '.join(b.get('tags', []))}".lower()
                b_text_no_acc = _remove_accents(b_text)
                # Dùng word boundary \b để tránh từ đơn ngắn (như 'bi') khớp nhầm vào 'biếc'
                hit_count = sum(
                    1 for kw in topic_kws
                    if re.search(r"\b" + re.escape(kw) + r"\b", b_text)
                    or re.search(r"\b" + re.escape(_remove_accents(kw)) + r"\b", b_text_no_acc)
                )
                if hit_count >= max(1, math.ceil(len(topic_kws) * 0.5)):
                    matched_author_books.append(b)

            if not matched_author_books:
                # Tác giả có thật nhưng KHÔNG viết cuốn sách/chủ đề này -> Chặn Hallucination!
                available_titles = ", ".join(f"**{b['title']}**" for b in author_books[:4])
                return {
                    "answer": (
                        f"📚 Tôi đã tra cứu kỹ kho sách nhưng tác giả **{detected_author}** "
                        f"**không có** tác phẩm nào khớp với `{', '.join(topic_kws)}` trong hệ thống. "
                        f"Có thể đây là tên sách không có thật hoặc sự kết hợp nhầm lẫn.\n\n"
                        f"✨ Tuy nhiên, bạn có thể tham khảo các tác phẩm chính thức của **{detected_author}** "
                        f"hiện có sẵn trong kho như: {available_titles}."
                    ),
                    "books": [],
                    "author_recs": author_books[:AUTHOR_REC_COUNT],
                    "query_type": "anti_halluc",
                    "query_context": query_context,
                    "found": False,
                    "latency_ms": timings,
                }
            author_books = matched_author_books

        # Chấm điểm Hybrid cho các sách của tác giả đó
        scored_author_books = []
        for b in author_books:
            sem_score = 0.95
            rank_score = score_ranking(b)
            total = hybrid_score(sem_score, b)
            scored_author_books.append({
                **b,
                "score_semantic": round(sem_score, 4),
                "score_ranking": round(rank_score, 4),
                "score_total": round(total, 4),
            })
        scored_author_books.sort(key=lambda x: x["score_total"], reverse=True)
        top_books = scored_author_books[:TOP_K]

        intent["query_type"] = "by_author"
        # FIX #1: 1 Gemini call duy nhất (intent đã có, chỉ cần answer)
        t0 = time.time()
        combined = combined_gemini_call(
            message=message,
            top_books=top_books,
            query_type_hint="by_author",
            author_recs=[],
            session_history=session_history or [],
            fallback_intent=intent,
        )
        answer = combined["answer"]
        timings["answer_ms"] = round((time.time() - t0) * 1000)

        # ── [Harness Gate 3] OutputRuleHarness — đồng bộ với nhánh general ──
        output_harness_issues: list[str] = []
        if OutputRuleHarness and top_books:
            try:
                out_check = OutputRuleHarness.verify(answer, top_books)
                if not out_check["verified"]:
                    output_harness_issues = out_check.get("issues", [])
                    if not out_check.get("is_grounded", True):
                        answer = (
                            "⚠️ *Lưu ý: Phiên này không tìm thấy sách khớp trong kho dữ liệu. "
                            "Thông tin dưới đây có thể chưa chính xác.*\n\n"
                        ) + answer
            except Exception as _out_err:
                print(f"[WARN] OutputRuleHarness (by_author) bỏ qua: {_out_err}")

        timings["total_ms"] = round((time.time() - t_total) * 1000)
        return {
            "answer": answer,
            "books": top_books,
            "author_recs": [],
            "query_type": "by_author",
            "query_context": query_context,
            "found": len(top_books) > 0,
            "latency_ms": timings,
            "output_harness_issues": output_harness_issues,
        }


    # Nếu Gemini phát hiện bẫy Hallucination rõ ràng (is_halluc_trap == True)
    if intent.get("is_halluc_trap"):
        t0 = time.time()
        combined = combined_gemini_call(
            message=message,
            top_books=[],
            query_type_hint="anti_halluc",
            session_history=session_history or [],
            fallback_intent=intent,
        )
        answer = combined["answer"]
        timings["answer_ms"] = round((time.time() - t0) * 1000)
        timings["total_ms"]  = round((time.time() - t_total) * 1000)
        return {
            "answer": answer,
            "books": [],
            "author_recs": [],
            "query_type": "anti_halluc",
            "query_context": query_context,
            "found": False,
            "latency_ms": timings,
        }

    # ── Bước 3: Semantic Search (Dense + Sparse Lexical) ──────────────────
    t0 = time.time()
    embedder   = _get_embedder()
    collection = _get_collection()

    eligible_ids = {b["id"] for b in eligible}
    eligible_map = {b["id"]: b for b in eligible}

    search_query = intent.get("semantic_query") or message
    query_vec    = embedder.encode([search_query])[0].tolist()

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(len(all_books), collection.count()),
        include=["distances", "metadatas"],
    )
    timings["semantic_ms"] = round((time.time() - t0) * 1000)

    # ── Bước 4: Hybrid Scoring (70% Dense Cosine + 30% Sparse Lexical) ────
    t0 = time.time()
    scored_books = []

    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    # Kết hợp từ khóa từ câu gốc và từ khóa Gemini trích xuất
    all_kws = list(dict.fromkeys(topic_kws + [k.lower() for k in intent.get("keywords", []) if len(k) > 1]))
    intent_cat = (intent.get("category") or "").lower()

    for dist, meta in zip(distances, metadatas):
        book_id = meta.get("id", "")
        if book_id not in eligible_ids:
            continue

        book = eligible_map[book_id]
        dense_sem = max(0.0, min(1.0, 1.0 - dist))

        # Sparse Lexical Matching trên title, category, tags, description
        title_low = book.get("title", "").lower()
        cat_low   = book.get("category", "").lower()
        tags_low  = " ".join(book.get("tags", [])).lower()
        desc_low  = book.get("description", "").lower()
        full_text = f"{title_low} {cat_low} {tags_low} {desc_low}"
        full_no_acc = _remove_accents(full_text)

        matched_kws = 0
        if all_kws:
            for kw in all_kws:
                if kw in full_text or _remove_accents(kw) in full_no_acc:
                    matched_kws += 1
            sparse_sem = matched_kws / len(all_kws)
        else:
            sparse_sem = 0.0

        # Thưởng điểm nếu khớp đúng thể loại người dùng yêu cầu (VD: "tâm lý", "trinh thám")
        cat_boost = 0.0
        if intent_cat and (intent_cat in cat_low or _remove_accents(intent_cat) in _remove_accents(cat_low)):
            cat_boost = 0.15
        elif any(c in message.lower() for c in ["tâm lý", "kỹ năng", "kinh tế", "trinh thám", "thiếu nhi", "khoa học", "văn học"]):
            for c in ["tâm lý", "kỹ năng", "kinh tế", "trinh thám", "thiếu nhi", "khoa học", "văn học"]:
                if c in message.lower() and c in cat_low:
                    cat_boost = 0.18
                    break
                elif c in message.lower() and c not in cat_low:
                    cat_boost = -0.15

        sem_score = min(1.0, max(0.0, 0.65 * dense_sem + 0.35 * sparse_sem + cat_boost))

        # Ngưỡng lọc chống nhiễu: nếu hoàn toàn không khớp từ khóa nào và điểm ngữ nghĩa thấp -> loại bỏ
        if all_kws and matched_kws == 0 and dense_sem < 0.52 and cat_boost <= 0:
            continue

        rank_score = score_ranking(book)
        total      = hybrid_score(sem_score, book)

        scored_books.append({
            **book,
            "score_semantic": round(sem_score, 4),
            "score_ranking":  round(rank_score, 4),
            "score_total":    round(total, 4),
            "score_hype":     0.0,  # sẽ được cập nhật sau khi HyPE filter
        })

    scored_books.sort(key=lambda x: x["score_total"], reverse=True)

    # ── Bước 3B: HyPE Entailment Cone Filter (Poincaré Ball) ─────────────────
    # Áp dụng sau Hybrid Scoring để lọc thêm bằng quan hệ bao hàm hyperbolic.
    # Chỉ áp dụng khi: HyPE khả dụng, không phải image search và có đủ sách
    if _HYPE_ENABLED and not direct_image_matches and not detected_author and len(scored_books) > 3:
        t_hype = time.time()
        try:
            hype = get_hype_filter(_get_embedder())
            # Lấy pool rộng hơn TOP_K*3 để HyPE có đủ dữ liệu lọc
            hype_pool = scored_books[:max(TOP_K * 3, 15)]
            hype_query = intent.get("semantic_query") or message
            kept_books, hype_scores = hype.filter(
                query=hype_query,
                books=hype_pool,
                top_k=TOP_K * 2,
            )
            # Gắn hype_score vào từng sách đã lọc
            hype_score_map = {b["id"]: s for b, s in zip(kept_books, hype_scores)}
            # Cập nhật scored_books: giữ sách qua HyPE, gắn score
            final_books = []
            for b in scored_books:
                if b["id"] in hype_score_map:
                    b_copy = dict(b)
                    b_copy["score_hype"] = round(hype_score_map[b["id"]], 4)
                    final_books.append(b_copy)
            # Nếu HyPE lọc quá gắt (< TOP_K sách) → giữ nguyên scored_books
            scored_books = final_books if len(final_books) >= TOP_K else scored_books
            timings["hype_ms"] = round((time.time() - t_hype) * 1000)
        except Exception as _hype_ex:
            print(f"[WARN] HyPE filter bỏ qua do lỗi: {_hype_ex}")
            timings["hype_ms"] = -1

    top_books = scored_books[:TOP_K]

    # Nếu có sách khớp trực tiếp với tựa sách nhận diện từ ảnh bìa, đưa lên vị trí Top 1
    if direct_image_matches:
        d_books_formatted = []
        for db in direct_image_matches:
            d_books_formatted.append({
                **db,
                "score_semantic": 0.99,
                "score_ranking": round(score_ranking(db), 4),
                "score_total": 0.995,
                "reason": "Khớp chính xác với ảnh bìa sách bạn tải lên",
            })
        seen_ids = set()
        merged_books = []
        for b in (d_books_formatted + top_books):
            if b["id"] not in seen_ids:
                seen_ids.add(b["id"])
                merged_books.append(b)
        top_books = merged_books[:TOP_K]

    timings["ranking_ms"] = round((time.time() - t0) * 1000)

    # ── Bước 5: Author Recommendation ─────────────────────────────────────
    author_recs = []
    if purchased_book_id:
        top_ids     = [b["id"] for b in top_books]
        author_recs = get_author_recommendations(purchased_book_id, exclude_ids=top_ids)

    # ── FIX #1: 1 Gemini call duy nhất — intent + answer cùng lúc ──────────
    t0 = time.time()
    combined = combined_gemini_call(
        message=message,
        top_books=top_books,
        query_type_hint="image_search" if image_data else intent.get("query_type", "general"),
        author_recs=author_recs,
        session_history=session_history or [],
        fallback_intent=intent,
    )
    answer = combined["answer"]
    # Cập nhật intent với kết quả Gemini phân tích (chính xác hơn heuristic)
    refined_intent = combined.get("intent", {})
    if refined_intent.get("query_type"):
        intent["query_type"] = refined_intent["query_type"]
    timings["answer_ms"] = round((time.time() - t0) * 1000)

    # ── [Harness Gate 3] OutputRuleHarness — kiểm chứng đầu ra trước khi trả về ──
    output_harness_issues: list[str] = []
    if OutputRuleHarness and top_books:
        try:
            out_check = OutputRuleHarness.verify(answer, top_books)
            if not out_check["verified"]:
                output_harness_issues = out_check.get("issues", [])
                # Nếu không grounded (AI bịa sách) → thêm cảnh báo vào đầu câu trả lời
                if not out_check.get("is_grounded", True):
                    answer = (
                        "⚠️ *Lưu ý: Phiên này không tìm thấy sách khớp trong kho dữ liệu. "
                        "Thông tin dưới đây có thể chưa chính xác.*\n\n"
                    ) + answer
        except Exception as _out_err:
            print(f"[WARN] OutputRuleHarness bỏ qua: {_out_err}")

    timings["total_ms"] = round((time.time() - t_total) * 1000)

    return {
        "answer":      answer,
        "books":       top_books,
        "author_recs": author_recs,
        "query_type":  "image_search" if image_data else intent.get("query_type", "general"),
        "query_context": query_context,
        "found":       len(top_books) > 0,
        "latency_ms":  timings,
        "vision_info": vision_info,
        "output_harness_issues": output_harness_issues,
    }

