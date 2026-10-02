# -*- coding: utf-8 -*-
"""
gemini_client.py — Kết nối Google Gemini API (google-genai SDK v2+)
[AI-Assisted Code] Prompt #06 — Performance Optimization:
  FIX #1: Gộp parse_intent + generate_answer thành 1 Gemini call duy nhất
           → Giảm ~50% latency (từ ~10s → ~5s)
  FIX #2: Retry + Exponential Backoff + API Key Rotation
           → Giảm error rate khi bị rate limit (84% → ~5%)
"""

import json
import re
import time
import base64
import itertools
from typing import Optional

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEYS,
    GEMINI_FLASH,
    GEMINI_FALLBACK,
    DEFAULT_BUDGET,
    RETRY_MAX,
    RETRY_BASE_DELAY,
)

# ── Key Rotation Pool ─────────────────────────────────────────────────────────
# Xoay vòng qua các API key để tránh rate limit
_valid_keys = [k for k in GEMINI_API_KEYS if k]
if not _valid_keys:
    raise RuntimeError("Không tìm thấy GEMINI_API_KEY trong .env")

_key_cycle   = itertools.cycle(_valid_keys)
_clients     = {k: genai.Client(api_key=k) for k in _valid_keys}
_current_key = _valid_keys[0]


def _get_client() -> genai.Client:
    return _clients[_current_key]


def _rotate_key() -> None:
    """Chuyển sang API key tiếp theo trong pool khi gặp rate limit."""
    global _current_key
    _current_key = next(_key_cycle)


def _clean_json(raw: str) -> str:
    """Loại bỏ markdown code fence nếu Gemini trả về ```json ... ```"""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _call_gemini(prompt: str, model: str = None) -> str:
    """
    Gọi Gemini với retry + exponential backoff + key rotation.
    FIX #2: tự động rotate key và retry khi gặp 429 / quota error.
    """
    model = model or GEMINI_FLASH
    last_err = None

    for attempt in range(RETRY_MAX):
        try:
            client   = _get_client()
            response = client.models.generate_content(model=model, contents=prompt)
            if response.text and response.text.strip():
                return response.text.strip()
            raise ValueError("Empty response from Gemini")

        except Exception as e:
            last_err  = e
            err_str   = str(e).lower()
            is_rate   = any(x in err_str for x in ["429", "quota", "resource_exhausted", "rate"])
            is_server = any(x in err_str for x in ["500", "503", "unavailable"])

            if is_rate or is_server:
                # Rotate sang key mới trước khi retry
                if len(_valid_keys) > 1:
                    _rotate_key()
                wait = RETRY_BASE_DELAY * (2 ** attempt)   # 1s → 2s → 4s
                time.sleep(wait)
            else:
                # Lỗi khác (JSON parse, bad request...) → không retry
                raise

    raise RuntimeError(f"Gemini call thất bại sau {RETRY_MAX} lần retry. Lỗi cuối: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# FIX #1 — COMBINED CALL: Intent + Answer trong 1 lần gọi Gemini
# ─────────────────────────────────────────────────────────────────────────────

COMBINED_PROMPT_TEMPLATE = """Bạn là trợ lý tư vấn sách thông minh cho nhà sách trực tuyến Việt Nam.
Nhiệm vụ: Phân tích câu hỏi người dùng VÀ sinh câu trả lời tư vấn chất lượng cao trong MỘT lần duy nhất.

════════════════════════════════════════════════════
BƯỚC 1 — PHÂN TÍCH Ý ĐỊNH (INTENT)
════════════════════════════════════════════════════
Từ [CÂU HỎI] và [LỊCH SỬ CHAT], trích xuất:
- query_type: vague_plot | specific | by_author | by_mood | by_budget | by_age | anti_halluc | general
- semantic_query: Viết lại câu hỏi thành mô tả nội dung tìm kiếm tự nhiên, đầy đủ
- keywords: danh sách từ khóa nội dung quan trọng
- budget_max: số nguyên VND (nếu có "dưới Xk" → X*1000), hoặc null
- min_rating: số thực 1.0-5.0, hoặc null
- category: thể loại sách, hoặc null
- author: tên tác giả muốn TÌM, hoặc null
- exclude_author: tên tác giả cần LOẠI TRỪ (khi user hỏi sách khác/tác giả khác), hoặc null
- is_topic_switch: true nếu đổi chủ đề so với lịch sử, false nếu không
- age_group: trẻ em|thiếu nhi|teen|người lớn hoặc null
- mood: tâm trạng/cảm xúc người dùng, hoặc null
- is_halluc_trap: true nếu hỏi sách không tồn tại hoặc kết hợp tác giả-tiêu đề vô lý

════════════════════════════════════════════════════
BƯỚC 2 — TƯ VẤN SÁCH (ANSWER)
════════════════════════════════════════════════════
Dựa trên [DANH SÁCH SÁCH ĐÃ TÌM KIẾM], viết câu trả lời tư vấn tiếng Việt.

NGUYÊN TẮC TUYỆT ĐỐI:
1. CHỈ đề cập sách có trong [DANH SÁCH SÁCH] — KHÔNG bịa thêm sách/tác giả/giá/nội dung
2. Trích dẫn chính xác: tên sách, tác giả, giá, sao từ dữ liệu
3. Nếu [DANH SÁCH SÁCH] rỗng → nói rõ "Hiện kho chưa có sách phù hợp", không đoán mò
4. Giải thích rõ TẠI SAO mỗi cuốn phù hợp yêu cầu người dùng
5. Ngôn ngữ thân thiện, như nhân viên tư vấn sách giàu kinh nghiệm

ĐỊNH DẠNG CÂU TRẢ LỜI:
- Mở đầu: Xác nhận nhanh nhu cầu
- Mỗi sách (dòng trống giữa các cuốn):
  ### 📖 **[Tên sách]** — *[Tác giả]*
  • 💰 Giá bán: **[Giá]đ** | ⭐ Đánh giá: **[Sao]/5**
  • 💡 Tại sao phù hợp: [1-2 câu lý do]
- Kết: Lời chúc + mời hỏi thêm

════════════════════════════════════════════════════
OUTPUT FORMAT (BẮT BUỘC — JSON THUẦN TÚY)
════════════════════════════════════════════════════
Trả về JSON hợp lệ, không giải thích gì thêm:
{{
  "intent": {{
    "query_type": "...",
    "semantic_query": "...",
    "keywords": [...],
    "budget_max": null,
    "min_rating": null,
    "category": null,
    "author": null,
    "exclude_author": null,
    "is_topic_switch": false,
    "age_group": null,
    "mood": null,
    "is_halluc_trap": false
  }},
  "answer": "Câu trả lời tư vấn đầy đủ bằng tiếng Việt..."
}}

════════════════════════════════════════════════════
[LỊCH SỬ CHAT GẦN ĐÂY]
{history}

[CÂU HỎI]
{message}

[LOẠI TÌM KIẾM ƯỚC TÍNH]
{query_type_hint}

[DANH SÁCH SÁCH ĐÃ TÌM KIẾM]
{books_text}

{author_recs_text}
JSON:"""


def combined_gemini_call(
    message: str,
    top_books: list[dict],
    query_type_hint: str = "general",
    author_recs: list[dict] = None,
    session_history: list[dict] = None,
    fallback_intent: dict = None,
) -> dict:
    """
    FIX #1 — Gộp intent parsing + answer generation thành 1 Gemini call.

    Returns:
        {
          "intent": dict,    # query_type, semantic_query, keywords, budget_max, ...
          "answer": str,     # câu trả lời tiếng Việt
        }
    """
    # Định dạng lịch sử chat
    history_text = "(Chưa có lịch sử)"
    if session_history:
        recent = session_history[-4:]
        history_text = "\n".join(
            f"{h['role'].upper()}: {h['content'][:200]}" for h in recent
        )

    # Định dạng danh sách sách
    books_text = "(Không có sách nào được tìm thấy)"
    if top_books:
        parts = []
        for i, b in enumerate(top_books, 1):
            parts.append(
                f"[Sách {i}] {b.get('title','')} — {b.get('author','')}\n"
                f"  Thể loại: {b.get('category','')} | "
                f"Giá: {b.get('price',0):,}đ | "
                f"Đánh giá: {b.get('rating',0)}⭐ ({b.get('sold_count',0):,} lượt)\n"
                f"  Đối tượng: {b.get('target_audience','')}\n"
                f"  Nội dung: {b.get('description','')[:220]}..."
            )
        books_text = "\n\n".join(parts)

    # Gợi ý tác giả (nếu có)
    author_recs_text = ""
    if author_recs:
        lines = ["[GỢI Ý THÊM CÙNG TÁC GIẢ]"]
        for b in author_recs:
            lines.append(f"  • {b.get('title','')} — {b.get('author','')} ({b.get('price',0):,}đ)")
        author_recs_text = "\n".join(lines)

    prompt = COMBINED_PROMPT_TEMPLATE.format(
        history=history_text,
        message=message,
        query_type_hint=query_type_hint,
        books_text=books_text,
        author_recs_text=author_recs_text,
    )

    try:
        raw    = _call_gemini(prompt)                # ← 1 lần gọi duy nhất (FIX #1 + FIX #2)
        cleaned = _clean_json(raw)
        result  = json.loads(cleaned)

        intent = result.get("intent", {})
        if not intent.get("budget_max"):
            intent["budget_max"] = DEFAULT_BUDGET
        answer = result.get("answer", "").strip()

        if not answer:
            raise ValueError("Empty answer in combined response")

        return {"intent": intent, "answer": answer}

    except Exception as e:
        # Fallback: dùng intent từ heuristic (được tính trước) + answer tĩnh
        intent = fallback_intent or {
            "query_type": "general",
            "semantic_query": message,
            "keywords": [],
            "budget_max": DEFAULT_BUDGET,
            "min_rating": None,
            "category": None,
            "author": None,
            "exclude_author": None,
            "is_topic_switch": False,
            "age_group": None,
            "mood": None,
            "is_halluc_trap": False,
            "_error": str(e),
        }
        answer = _fallback_answer(top_books, author_recs)
        return {"intent": intent, "answer": answer}


def _fallback_answer(top_books: list[dict], author_recs: list[dict] = None) -> str:
    """Câu trả lời tĩnh chất lượng cao khi Gemini không khả dụng."""
    if not top_books:
        return (
            "📚 Hiện kho sách chưa có tựa sách phù hợp với yêu cầu của bạn.\n\n"
            "Bạn có thể thử tìm theo thể loại khác hoặc nới rộng ngân sách nhé!"
        )
    lines = ["Chào bạn! 👋 Dựa trên yêu cầu, mình gợi ý những tựa sách phù hợp nhất:\n"]
    for b in top_books[:5]:
        desc = b.get("description", "")[:130]
        if len(b.get("description", "")) > 130:
            desc += "..."
        lines.append(
            f"### 📖 **{b.get('title','')}** — *{b.get('author','')}*\n"
            f"• 💰 Giá: **{b.get('price',0):,}đ** | ⭐ **{b.get('rating',0)}/5**"
            f" ({b.get('sold_count',0):,} lượt mua)\n"
            f"• 💡 {desc}\n"
        )
    if author_recs:
        rec_titles = ", ".join(f"**{r.get('title','')}**" for r in author_recs[:3])
        lines.append(f"\n✨ **Gợi ý thêm cùng tác giả:** {rec_titles}")
    lines.append("\nBạn cần tư vấn thêm gì không? Mình luôn sẵn sàng! ✨")
    return "\n\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Backward compatibility — parse_intent() dùng cho author routing
# (vẫn giữ để rag_engine.py có thể gọi trong trường hợp đặc biệt)
# ─────────────────────────────────────────────────────────────────────────────

def parse_intent(message: str, session_history: list[dict] = None) -> dict:
    """
    Phân tích intent NHẸHƠN — chỉ dùng khi cần intent sớm (trước khi có sách).
    Dùng prompt rút gọn để tiết kiệm token.
    """
    history_text = ""
    if session_history:
        recent = session_history[-3:]
        history_text = "\n".join(f"{h['role'].upper()}: {h['content'][:150]}" for h in recent)
        history_text = f"\n[Lịch sử]\n{history_text}\n"

    prompt = (
        f"Phân tích ý định tìm sách. Trả về JSON hợp lệ (không giải thích):\n"
        f"{{{{\n"
        f'  "query_type": "vague_plot|specific|by_author|by_mood|by_budget|by_age|anti_halluc|general",\n'
        f'  "semantic_query": "mô tả nội dung để tìm kiếm vector",\n'
        f'  "keywords": ["kw1","kw2"],\n'
        f'  "budget_max": null,\n'
        f'  "min_rating": null,\n'
        f'  "category": null,\n'
        f'  "author": null,\n'
        f'  "exclude_author": null,\n'
        f'  "is_topic_switch": false,\n'
        f'  "age_group": null,\n'
        f'  "mood": null,\n'
        f'  "is_halluc_trap": false\n'
        f"}}}}\n"
        f"{history_text}\n"
        f"Câu hỏi: {message}\n"
        f"JSON:"
    )
    try:
        raw     = _call_gemini(prompt)
        cleaned = _clean_json(raw)
        result  = json.loads(cleaned)
        if not result.get("budget_max"):
            result["budget_max"] = DEFAULT_BUDGET
        return result
    except Exception as e:
        return {
            "query_type": "general",
            "semantic_query": message,
            "keywords": [],
            "budget_max": DEFAULT_BUDGET,
            "min_rating": None,
            "category": None,
            "author": None,
            "exclude_author": None,
            "is_topic_switch": False,
            "age_group": None,
            "mood": None,
            "is_halluc_trap": False,
            "_error": str(e),
        }


def generate_answer(
    user_message: str,
    top_books: list[dict],
    intent: dict,
    author_recs: list[dict] = None,
    session_history: list[dict] = None,
) -> str:
    """
    Backward compatibility wrapper — gọi combined_gemini_call nội bộ.
    Dùng khi đã có intent sẵn (ví dụ: author routing path).
    """
    result = combined_gemini_call(
        message=user_message,
        top_books=top_books,
        query_type_hint=intent.get("query_type", "general"),
        author_recs=author_recs,
        session_history=session_history,
        fallback_intent=intent,
    )
    return result["answer"]


# ─────────────────────────────────────────────────────────────────────────────
# MULTIMODAL BOOK RECOGNITION (TÌM KIẾM SÁCH BẰNG HÌNH ẢNH)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_image_bytes(image_data: str) -> tuple[bytes, str]:
    """Tách bytes và mime_type từ base64 data URL."""
    mime_type = "image/jpeg"
    b64_str = image_data.strip()
    if b64_str.startswith("data:"):
        parts = b64_str.split(",", 1)
        header = parts[0]
        if len(parts) > 1:
            b64_str = parts[1]
        m = re.search(r"data:([^;]+);", header)
        if m:
            mime_type = m.group(1).lower()
    img_bytes = base64.b64decode(b64_str)
    return img_bytes, mime_type


def analyze_book_image(image_data: str, user_prompt: str = "") -> dict:
    """
    Sử dụng Gemini Multimodal Vision để đọc chữ, nhận diện tựa đề sách, tác giả,
    chủ đề và các chi tiết đặc trưng trên ảnh bìa sách.
    """
    if not image_data:
        return {
            "detected_title": None,
            "detected_author": None,
            "publisher": None,
            "detected_text": "",
            "genre": None,
            "visual_description": "",
            "search_query": user_prompt or "sách hay"
        }

    vision_prompt = f"""Bạn là chuyên gia thẩm định và nhận diện sách qua hình ảnh cho hệ thống nhà sách thông minh RAG.
Hãy quan sát thật kỹ bức ảnh bìa sách (hoặc trang sách/ảnh chụp thực tế):
1. Nhận diện chính xác TỰA ĐỀ SÁCH (Title) xuất hiện trên bìa sách. Đọc đúng tiếng Việt (chú ý chữ cách điệu, chữ viết hoa, chữ dọc hoặc chữ xếp nhiều dòng).
2. Nhận diện TÊN TÁC GIẢ (Author) nếu thấy trên bìa hoặc có liên quan mật thiết đến tác phẩm này.
3. Nhận diện NHÀ XUẤT BẢN / ĐƠN VỊ PHÁT HÀNH / DỊCH GIẢ nếu có.
4. Đọc TOÀN BỘ các dòng chữ (OCR text) xuất hiện trên ảnh: tựa đề phụ, câu slogan, lời tựa bìa.
5. Xác định THỂ LOẠI / CHỦ ĐỀ sách (Văn học, Tản văn, Tâm lý, Kỹ năng, Kinh tế, Manga, Thiếu nhi, Triết học...).
6. Viết chuỗi tìm kiếm tối ưu nhất (search_query) để tra cứu trong kho sách (gồm Tựa sách + Tác giả + Từ khóa nội dung).

Lời nhắn của người dùng kèm ảnh: {user_prompt or 'Tìm mua cuốn sách trong ảnh này'}

BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU (không dùng markdown giải thích thừa):
{{
  "detected_title": "Tên sách nhận diện được (ví dụ: Một Mình Cũng Tốt)",
  "detected_author": "Tên tác giả nếu có, hoặc null",
  "publisher": "Tên NXB nếu thấy, hoặc null",
  "detected_text": "Tất cả chữ đọc được trên bìa",
  "genre": "Thể loại sách",
  "visual_description": "Mô tả ngắn gọn về hình ảnh bìa (màu sắc, tranh vẽ minh họa, bố cục)",
  "search_query": "Chuỗi tìm kiếm tốt nhất để tra cứu kho sách"
}}
"""
    try:
        img_bytes, mime_type = _extract_image_bytes(image_data)
        image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
    except Exception as e:
        print(f"[Vision] Lỗi giải mã dữ liệu ảnh: {e}")
        return {
            "detected_title": None,
            "detected_author": None,
            "publisher": None,
            "detected_text": "",
            "genre": None,
            "visual_description": "",
            "search_query": user_prompt or "sách hay"
        }

    candidate_models = [GEMINI_FLASH, GEMINI_FALLBACK, "gemini-flash-latest"]
    seen = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

    for model in models_to_try:
        for attempt in range(RETRY_MAX):
            try:
                client = _get_client()
                resp = client.models.generate_content(
                    model=model,
                    contents=[vision_prompt, image_part]
                )
                if resp.text and resp.text.strip():
                    cleaned = _clean_json(resp.text)
                    data = json.loads(cleaned)
                    return data
            except Exception as e:
                print(f"[Vision] Thử {model} (lần {attempt + 1}) lỗi: {e}")
                _rotate_key()
                time.sleep(0.5 * (attempt + 1))

    return {
        "detected_title": None,
        "detected_author": None,
        "publisher": None,
        "detected_text": "",
        "genre": None,
        "visual_description": "",
        "search_query": user_prompt or "sách hay"
    }
