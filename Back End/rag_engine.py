# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #04 — Tích hợp Hybrid Search (Dense + Sparse Lexical),
# Author Routing & Anti-Hallucination Gate theo plan.md §3.1 & §3.2
rag_engine.py — Lõi thực thi quy trình RAG và tìm kiếm xếp hạng kết hợp (Hybrid RAG Pipeline)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Quy trình xử lý truy vấn:
1. Cổng an toàn đầu vào: Kiểm tra qua InputRuleHarness và lọc độ cụ thể câu hỏi (HyPE Specificity).
2. Phân tích ý định & bẫy sai lệch: Trích xuất tác giả, thể loại, ngân sách và nhận diện câu hỏi bẫy.
3. Lọc cứng (Hard Filter): Lọc theo tình trạng còn hàng, điểm đánh giá tối thiểu và ngân sách người dùng.
4. Tìm kiếm ngữ nghĩa kết hợp (Hybrid Search): Kết hợp Dense Semantic (ChromaDB) + Sparse Lexical + HyPE Entailment.
5. Xếp hạng đa tiêu chí: Tính điểm tổng hợp từ điểm tương đồng ngữ nghĩa và điểm chất lượng thương mại.
6. Tổng hợp phản hồi: Tạo câu trả lời tự nhiên qua LLM Gemini và hậu kiểm bằng OutputRuleHarness.
"""

import json
import math
import re
import time
import unicodedata
from typing import Optional, List, Dict, Any, Tuple

import chromadb
from sentence_transformers import SentenceTransformer

from teen_normalizer import normalize_query
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
    AUTHOR_EXACT_MATCH_SCORE,
)
from gemini_client import parse_intent, generate_answer, combined_gemini_call, analyze_book_image

# ── Tích hợp Bộ quy tắc Guardrail Harness (RAG Rules) ─────────────────────────
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

# ── Tích hợp Bộ lọc Hyperbolic Poincaré Ball (HyPE Filter) ────────────────────
try:
    from hype_filter import get_hype_filter
    _HYPE_ENABLED = True
except Exception as _hype_err:
    _HYPE_ENABLED = False
    print(f"[WARN] HyPE Filter không khởi động được: {_hype_err}")


# ─────────────────────────────────────────────────────────────────────────────
# KHỞI TẠO BỘ NHỚ ĐỆM ĐƠN THỂ (LAZY SINGLETON & CACHE MANAGERS)
# ─────────────────────────────────────────────────────────────────────────────

_embedder: Optional[SentenceTransformer] = None
_chroma_collection = None
_books_cache: List[dict] = []          # Cache toàn bộ sách từ sample.json
_author_index: Dict[str, str] = {}     # Chỉ mục tác giả (chữ thường & không dấu -> Tên chuẩn)
_sold_count_max: int = 1               # Giá trị doanh số cao nhất dùng cho log-normalization
_collection_count_cache: int = 0       # Cache số lượng vector trong ChromaDB


def _remove_accents(text: str) -> str:
    """
    Bỏ dấu tiếng Việt (Unicode Normalization Form D - NFD)
    giúp hỗ trợ khớp chuỗi hoàn hảo khi người dùng gõ không dấu (vd: 'Nguyen Nhat Anh' -> 'nguyen nhat anh').
    """
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(c for c in norm if unicodedata.category(c) != "Mn").lower()


def _get_embedder() -> SentenceTransformer:
    """Tải và trả về đối tượng SentenceTransformer duy nhất trong bộ nhớ RAM."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection():
    """Kết nối và trả về Collection ChromaDB duy nhất."""
    global _chroma_collection, _collection_count_cache
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST)
        _chroma_collection = client.get_collection(CHROMA_COLLECTION)
        _collection_count_cache = _chroma_collection.count()
    return _chroma_collection


def _get_books() -> List[dict]:
    """Nạp và lập chỉ mục nhanh danh mục sách từ sample.json."""
    global _books_cache, _sold_count_max, _author_index
    if not _books_cache:
        with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        _books_cache = raw_data.get("data", raw_data) if isinstance(raw_data, dict) else raw_data
        _sold_count_max = max(b.get("sold_count", 1) for b in _books_cache) or 1

        # Xây dựng chỉ mục tác giả hai chiều (có dấu và không dấu)
        _author_index = {}
        for b in _books_cache:
            author_full = b.get("author", "").strip()
            if not author_full:
                continue
            _author_index[author_full.lower()] = author_full
            _author_index[_remove_accents(author_full)] = author_full
            for sub_a in author_full.split(","):
                sub_a = sub_a.strip()
                if len(sub_a) >= 5 and len(sub_a.split()) >= 2:
                    _author_index[sub_a.lower()] = author_full
                    _author_index[_remove_accents(sub_a)] = author_full
    return _books_cache


def is_chroma_ready() -> bool:
    """Kiểm tra trạng thái sẵn sàng của cơ sở dữ liệu vector."""
    try:
        col = _get_collection()
        return col.count() > 0
    except Exception:
        return False


def is_author_negated(message: str, author: str) -> bool:
    """
    Kiểm tra xem tác giả có bị nhắc tới trong ngữ cảnh phủ định / loại trừ hay không
    (Ví dụ: 'sách khác ngoài Nguyễn Nhật Ánh', 'không đọc sách của Paulo Coelho').
    """
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
        if re.search(p, msg_low) or re.search(_remove_accents(p), msg_no_acc):
            return True
    return False


def extract_recent_author_from_history(session_history: List[dict]) -> Optional[str]:
    """Trích xuất tên tác giả được nhắc đến gần nhất trong lịch sử hội thoại."""
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
    """Nhận diện các mẫu câu yêu cầu đổi chủ đề / đổi tác giả / tìm cuốn khác."""
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
    """
    NHẬN DIỆN TÁC GIẢ BẰNG REGEX WORD BOUNDARY & ACCENT INVARIANCE.
    Hỗ trợ nhận dạng chính xác tên tác giả cả khi gõ có dấu, không dấu hoặc đảo thứ tự.
    """
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

            # Dùng regex boundary \b để không bị khớp nhầm từ con (vd: 'cha' trong 'chăn cừu')
            pattern = rf"\b{re.escape(k)}\b"
            pattern_no_acc = rf"\b{re.escape(k_no_acc)}\b"
            if re.search(pattern, t_low) or re.search(pattern_no_acc, t_no_acc):
                found_author = _author_index[k]
                if check_negation and is_author_negated(query, found_author):
                    continue
                return found_author
    return None


def extract_topic_keywords(query: str, exclude_author: Optional[str] = None) -> List[str]:
    """
    TRÍCH XUẤT TỪ KHÓA NỘI DUNG / CỐT TRUYỆN CỐT LÕI (SPARSE LEXICAL TOKEN EXTRACTION).
    Tự động tách các cụm từ ghép chuyên sâu (Compound Vocabulary) và loại bỏ từ dừng.
    """
    q = query.lower()
    if exclude_author:
        q = q.replace(exclude_author.lower(), " ")
        q_no_acc = _remove_accents(q)
        auth_no_acc = _remove_accents(exclude_author)
        if auth_no_acc in q_no_acc:
            for token in auth_no_acc.split():
                q = re.sub(r"\b" + re.escape(token) + r"\b", " ", q)

    # Lọc bỏ cụm từ chỉ giá tiền/ngân sách (vd: 'dưới 100k', 'tầm 150000đ')
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
# BƯỚC 2: CỔNG LỌC CỨNG (HARD FILTERING GATE - PLAN §3.2)
# ─────────────────────────────────────────────────────────────────────────────

def hard_filter(books: List[dict], budget: int, min_rating: float) -> List[dict]:
    """
    CỔNG LỌC CỨNG ĐẦU VÀO (HARD FILTERING GATE):
    Eligible(b) = 1 nếu và chỉ nếu:
      b.in_stock == True (còn hàng trong kho)
      AND b.rating >= min_rating (chất lượng đánh giá đạt chuẩn)
      AND b.price <= budget (nằm trong khả năng tài chính của độc giả)
    """
    return [
        b for b in books
        if b.get("in_stock", True)
        and float(b.get("rating", 0)) >= min_rating
        and int(b.get("price", 0)) <= budget
    ]


# ─────────────────────────────────────────────────────────────────────────────
# BƯỚC 4: CÔNG THỨC CHẤM ĐIỂM LAI (HYBRID SCORING ENGINE - PLAN §3.2)
# ─────────────────────────────────────────────────────────────────────────────

def score_rating(book: dict) -> float:
    """
    Chuẩn hóa điểm đánh giá sao về thang đo đơn vị [0, 1].
    Công thức: R_hat(b) = (rating - 1.0) / 4.0
    """
    r = float(book.get("rating", 1.0))
    return max(0.0, min(1.0, (r - 1.0) / 4.0))


def score_sales(book: dict) -> float:
    """
    Chuẩn hóa doanh số bán theo hàm Logarit tự nhiên (Diminishing Marginal Returns).
    Công thức: S_hat(b) = ln(1 + sold_count) / ln(1 + sold_count_max)
    """
    s = int(book.get("sold_count", 0))
    if _sold_count_max <= 0:
        return 0.0
    return math.log1p(s) / math.log1p(_sold_count_max)


def score_review_quality(book: dict) -> float:
    """
    Đánh giá độ tin cậy và lọc đánh giá rác (Review Quality Factor).
    Công thức: Q(b) = (valid_reviews / total_reviews) * min(1.0, valid_reviews / 10)
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
    Điểm xếp hạng thương mại tổng hợp từ 3 tiêu chí:
    Score_Ranking = 50% * R_hat + 30% * S_hat + 20% * Q
    """
    return (
        W_RATING  * score_rating(book) +
        W_SALES   * score_sales(book) +
        W_QUALITY * score_review_quality(book)
    )


def hybrid_score(semantic: float, book: dict) -> float:
    """
    ĐIỂM XẾP HẠNG TỔNG HỢP CUỐI CÙNG (HYBRID TOTAL SCORE):
    Score_Total = ALPHA * Score_Semantic + (1 - ALPHA) * Score_Ranking
    Với ALPHA = 0.75 (75% Trọng số ngữ nghĩa, 25% Trọng số chất lượng thương mại).
    """
    return ALPHA * semantic + (1 - ALPHA) * score_ranking(book)


# ─────────────────────────────────────────────────────────────────────────────
# BƯỚC 5: GỢI Ý TÁC PHẨM CÙNG TÁC GIẢ (IN-SESSION RECOMMENDATIONS)
# ─────────────────────────────────────────────────────────────────────────────

def get_author_recommendations(purchased_book_id: str, exclude_ids: List[str] = None) -> List[dict]:
    """
    Khi độc giả chọn mua một cuốn sách -> Hệ thống tự động truy vấn và gợi ý thêm
    AUTHOR_REC_COUNT tác phẩm xuất sắc nhất của cùng tác giả đó còn hàng trong kho.
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
    # Sắp xếp theo số sao đánh giá giảm dần
    same_author.sort(key=lambda b: float(b.get("rating", 0)), reverse=True)
    return same_author[:AUTHOR_REC_COUNT]


# ─────────────────────────────────────────────────────────────────────────────
# QUY TRÌNH THI HÀNH RAG TOÀN DIỆN (MAIN RAG EXECUTION PIPELINE)
# ─────────────────────────────────────────────────────────────────────────────

def run_rag(
    message: str,
    budget: Optional[int] = None,
    session_history: List[dict] = None,
    purchased_book_id: Optional[str] = None,
    image_data: Optional[str] = None,
) -> Dict[str, Any]:
    """
    HÀM ĐIỀU PHỐI CHÍNH CỦA HỆ THỐNG TƯ VẤN RAG.
    Thực hiện trọn vẹn luồng 5 bước: Kiểm duyệt an toàn -> Phân tích ý định -> Lọc cứng -> Tìm kiếm lai -> Sinh câu trả lời.
    """
    timings: Dict[str, int] = {}
    t_total = time.time()
    original_message = message

    # ── [Pre-processing] Chuẩn hóa teencode / tiếng lòng trước khi vào pipeline ──
    message, _mood_hint = normalize_query(message)

    # ── [Vision Analysis] Phân tích ảnh bìa sách nếu người dùng tải ảnh lên ──
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

        # Kiểm tra khớp tựa đề trực tiếp trong kho dữ liệu
        all_books_cache = _get_books()
        if det_title:
            d_raw = det_title.strip()
            d_no_acc = _remove_accents(d_raw.lower())
            if len(d_no_acc) >= 3:
                for b in all_books_cache:
                    b_no_acc = _remove_accents(b.get("title", "").lower().strip())
                    if d_no_acc == b_no_acc or (len(d_no_acc) >= 6 and (d_no_acc in b_no_acc or b_no_acc in d_no_acc)):
                        direct_image_matches.append(b)

        # Bổ sung thông tin OCR bìa vào truy vấn để LLM nắm đầy đủ ngữ cảnh
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

    # ── [Gate 0] Tiền kiểm duyệt an toàn pháp lý & Prompt Injection qua InputRuleHarness ──
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

    # ── [Gate 0B] HyPE Specificity Gate: Chủ động hỏi lại khi truy vấn quá mơ hồ ──
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
                        "• **Cảm xúc bạn muốn**: Chữa lành, truyền cảm hứng, giải trí, học hỏi...?\n"
                        "• **Ngân sách**: Dưới bao nhiêu đồng?\n"
                        "• **Đối tượng**: Sách cho trẻ em, học sinh hay người lớn?\n\n"
                        "Ngoài ra bạn có thể mô tả chi tiết cốt truyện nhớ mang máng hoặc tải ảnh bìa sách lên — tôi sẽ tìm ngay! ✨"
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
            pass

    # ── Bước 1: Phân tích Ý định & Trích xuất Thực thể Nhanh (Fast Intent Extraction) ──
    regex_budget = None
    m_budget = re.search(r"(?:dưới|tầm|khoảng|tối đa|<|<=)\s*(\d+)\s*(k|nghìn|ngàn|đ|vnd|đồng)?", message.lower())
    if m_budget:
        val = int(m_budget.group(1))
        unit = m_budget.group(2) or ""
        regex_budget = val * 1000 if (unit in ("k", "nghìn", "ngàn") or val < 1000) else val

    recent_author = extract_recent_author_from_history(session_history)
    asking_different = is_query_asking_for_different_book_or_author(message)

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

    # ── Bước 2: Lọc cứng theo Ngân sách, Tồn kho và Số sao (Hard Filter) ──────
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
                "điều kiện ngân sách và mức đánh giá bạn yêu cầu. "
                "Bạn thử điều chỉnh ngân sách hoặc mức sao tối thiểu nhé!"
            ),
            "books": [],
            "author_recs": [],
            "query_type": intent.get("query_type", "by_budget"),
            "query_context": f"Ngân sách ≤ {effective_budget:,.0f}đ".replace(",", "."),
            "found": False,
            "latency_ms": timings,
        }

    # ── Bước 2B: Điều hướng Tác giả & Xử lý Chống Bẫy Hallucination ───────────
    if detected_author == exclude_author or (detected_author and is_author_negated(original_message, detected_author)):
        detected_author = None
    topic_kws = extract_topic_keywords(original_message, exclude_author=detected_author or exclude_author)

    # Xác định chủ đề ngữ cảnh hiển thị trên thanh bên UI
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

    # Nếu câu hỏi nhắm đến tác giả cụ thể
    if detected_author:
        author_books = [b for b in eligible if b.get("author") == detected_author]

        # Xử lý bẫy Hallucination tác giả
        if intent.get("is_halluc_trap") and not direct_image_matches:
            available_titles = ", ".join(f"**{b['title']}**" for b in author_books[:4])
            return {
                "answer": (
                    f"📚 Tôi đã tra cứu kỹ kho dữ liệu nhưng tác giả **{detected_author}** "
                    f"**không có** tác phẩm nào như vậy trong hệ thống. "
                    f"Có thể tên sách hoặc sự kết hợp thông tin chưa chính xác.\n\n"
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

        if direct_image_matches:
            author_books = direct_image_matches
        elif topic_kws:
            matched_author_books = []
            for b in author_books:
                b_text = f"{b['title']} {b.get('category', '')} {b.get('description', '')} {' '.join(b.get('tags', []))}".lower()
                b_text_no_acc = _remove_accents(b_text)
                hit_count = sum(
                    1 for kw in topic_kws
                    if re.search(r"\b" + re.escape(kw) + r"\b", b_text)
                    or re.search(r"\b" + re.escape(_remove_accents(kw)) + r"\b", b_text_no_acc)
                )
                if hit_count >= max(1, math.ceil(len(topic_kws) * 0.5)):
                    matched_author_books.append(b)

            if not matched_author_books:
                available_titles = ", ".join(f"**{b['title']}**" for b in author_books[:4])
                return {
                    "answer": (
                        f"Hiện hệ thống chưa tìm thấy tác phẩm nào của tác giả **{detected_author}** "
                        f"khớp với nội dung '{', '.join(topic_kws)}' trong kho sách. "
                        f"Bạn có thể tham khảo một số tác phẩm của **{detected_author}** "
                        f"đang có sẵn như: {available_titles}."
                    ),
                    "books": [],
                    "author_recs": author_books[:AUTHOR_REC_COUNT],
                    "query_type": "anti_halluc",
                    "query_context": query_context,
                    "found": False,
                    "latency_ms": timings,
                }
            author_books = matched_author_books

        scored_author_books = []
        for b in author_books:
            sem_score = AUTHOR_EXACT_MATCH_SCORE
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

        # Hậu kiểm an toàn qua OutputRuleHarness
        output_harness_issues: List[str] = []
        if OutputRuleHarness and top_books:
            try:
                out_check = OutputRuleHarness.verify(answer, top_books)
                if not out_check["verified"]:
                    output_harness_issues = out_check.get("issues", [])
                    if not out_check.get("is_grounded", True):
                        answer = "Lưu ý: Hệ thống chưa tìm thấy dữ liệu đối chiếu chính xác cho yêu cầu này trong kho sách.\n\n" + answer
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

    # Nếu phát hiện bẫy Hallucination chung
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

    # ── Bước 3: Tìm kiếm Ngữ nghĩa Vector (ChromaDB Dense Search) ─────────────
    t0 = time.time()
    embedder   = _get_embedder()
    collection = _get_collection()

    eligible_ids = {b["id"] for b in eligible}
    eligible_map = {b["id"]: b for b in eligible}

    search_query = intent.get("semantic_query") or message
    query_vec    = embedder.encode([search_query])[0].tolist()

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(len(all_books), _collection_count_cache or collection.count()),
        include=["distances", "metadatas"],
    )
    timings["semantic_ms"] = round((time.time() - t0) * 1000)

    # ── Bước 4: Chấm điểm Kết hợp Lai (Dense Cosine + Sparse Lexical + Ranking) ──
    t0 = time.time()
    scored_books = []

    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    all_kws = list(dict.fromkeys(topic_kws + [k.lower() for k in intent.get("keywords", []) if len(k) > 1]))
    intent_cat = (intent.get("category") or "").lower()

    for dist, meta in zip(distances, metadatas):
        book_id = meta.get("id", "")
        if book_id not in eligible_ids:
            continue

        book = eligible_map[book_id]
        dense_sem = max(0.0, min(1.0, 1.0 - dist))

        # Khớp từ khóa thưa (Sparse Lexical Matching)
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

        # Thưởng / phạt theo thể loại yêu cầu
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

        # Lọc nhiễu: Nếu không khớp từ khóa nào và điểm vector quá thấp
        if all_kws and matched_kws == 0 and dense_sem < 0.52 and cat_boost <= 0:
            continue

        rank_score = score_ranking(book)
        total      = hybrid_score(sem_score, book)

        scored_books.append({
            **book,
            "score_semantic": round(sem_score, 4),
            "score_ranking":  round(rank_score, 4),
            "score_total":    round(total, 4),
            "score_hype":     0.0,
        })

    scored_books.sort(key=lambda x: x["score_total"], reverse=True)

    # ── Bước 3B: Lọc Nón Bao Hàm Hyperbolic HyPE (Poincaré Ball Entailment) ──
    if _HYPE_ENABLED and not direct_image_matches and not detected_author and len(scored_books) > 3:
        t_hype = time.time()
        try:
            hype = get_hype_filter(_get_embedder())
            hype_pool = scored_books[:max(TOP_K * 3, 15)]
            hype_query = intent.get("semantic_query") or message
            kept_books, hype_scores = hype.filter(
                query=hype_query,
                books=hype_pool,
                top_k=TOP_K * 2,
            )
            hype_score_map = {b["id"]: s for b, s in zip(kept_books, hype_scores)}
            final_books = []
            for b in scored_books:
                if b["id"] in hype_score_map:
                    b_copy = dict(b)
                    b_copy["score_hype"] = round(hype_score_map[b["id"]], 4)
                    final_books.append(b_copy)
            scored_books = final_books if len(final_books) >= TOP_K else scored_books
            timings["hype_ms"] = round((time.time() - t_hype) * 1000)
        except Exception as _hype_ex:
            print(f"[WARN] HyPE filter bỏ qua do lỗi: {_hype_ex}")
            timings["hype_ms"] = -1

    top_books = scored_books[:TOP_K]

    # Đưa sách nhận diện trùng khớp từ ảnh bìa lên vị trí ưu tiên Top 1
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

    # ── Bước 5: Gợi ý Tác phẩm Cùng Tác giả (In-session Recommendations) ───────
    author_recs = []
    if purchased_book_id:
        top_ids     = [b["id"] for b in top_books]
        author_recs = get_author_recommendations(purchased_book_id, exclude_ids=top_ids)

    # ── Bước 6: Gọi Gemini Kết Hợp & Hậu Kiểm An Toàn Đầu Ra ─────────────────
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
    refined_intent = combined.get("intent", {})
    if refined_intent.get("query_type"):
        intent["query_type"] = refined_intent["query_type"]
    timings["answer_ms"] = round((time.time() - t0) * 1000)

    # Hậu kiểm qua OutputRuleHarness
    output_harness_issues: List[str] = []
    if OutputRuleHarness and top_books:
        try:
            out_check = OutputRuleHarness.verify(answer, top_books)
            if not out_check["verified"]:
                output_harness_issues = out_check.get("issues", [])
                if not out_check.get("is_grounded", True):
                    answer = "Lưu ý: Hệ thống chưa tìm thấy dữ liệu đối chiếu chính xác cho yêu cầu này trong kho sách.\n\n" + answer
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
