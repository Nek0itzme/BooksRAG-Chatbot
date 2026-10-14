# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #16 — Hệ thống RAG chuyên dụng cho tài liệu cá nhân
doc_rag.py — RAG Engine cho tài liệu do người dùng tải lên (PDF → Markdown)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

3 chức năng chính:
1. index_session_docs()  — Chia nhỏ Markdown, embed vào ChromaDB tạm thời theo phiên
2. chat_with_doc()       — Hỏi đáp tự do kèm trích dẫn số trang
3. summarize_doc()       — Tóm tắt tài liệu theo 3 cấp: Ý tưởng – Luận điểm – Kết luận
4. generate_quiz()       — Tạo 5 câu trắc nghiệm JSON có giải thích kèm trang trích dẫn
"""

import re
import json
import hashlib

import chromadb

# Tái sử dụng mô hình embedding singleton từ rag_engine để tối ưu bộ nhớ
from rag_engine import _get_embedder
from gemini_client import _call_gemini  # Sử dụng API client thống nhất có hỗ trợ xoay vòng khóa

# ── ChromaDB ephemeral client (in-memory, không persist) ─────────────────────
# Dùng EphemeralClient trong RAM cho các tài liệu tải lên tạm thời của phiên
_chroma_client = chromadb.EphemeralClient()

# Chunk size mặc định ~800 ký tự, overlap 100 ký tự để không mất ngữ cảnh
_CHUNK_SIZE    = 800
_CHUNK_OVERLAP = 100

_sid_re = re.compile(r"[^\w\-]")


def _safe_sid(sid: str) -> str:
    return (_sid_re.sub("_", (sid or "").strip())[:64] or "sess_demo")  # Đảm bảo định danh khớp với doc_pipeline

# Pre-compile pattern tìm số trang trong anchor tags
_ANCHOR_RE = re.compile(r"<!-- PAGE_ANCHOR: (\d+) -->(.*?)<!-- PAGE_ANCHOR_END: \1 -->", re.DOTALL)


# ─────────────────────────────────────────────────────────────────────────────
# INDEXING
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Chia văn bản thành các đoạn chồng lấp (sliding window)."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def index_session_docs(session_id: str, md_contents: list[str], filenames: list[str]) -> str:
    """
    Chia nhỏ Markdown và embed vào collection ChromaDB riêng của phiên.
    Index CỘNG DỒN: chỉ thay thế chunks của các file vừa upload, giữ nguyên chunks của
    các file đã upload trước đó trong cùng phiên.

    Args:
        session_id:   ID phiên (dùng làm tên collection)
        md_contents:  Danh sách nội dung Markdown đã transcript
        filenames:    Tên file tương ứng (để lưu metadata)

    Returns:
        Chuỗi thông báo số chunk đã index
    """
    collection_name = f"doc_session_{_safe_sid(session_id)}"

    # FIX: code cũ delete_collection rồi tạo mới mỗi lần upload → file upload trước đó vẫn
    # hiện trong list_session_files nhưng đã mất index, hỏi về nó thì RAG trả "chưa có tài liệu".
    # Giờ chỉ xóa chunks thuộc các filename vừa upload (upsert theo file), giữ lại file cũ.
    try:
        collection = _chroma_client.get_collection(collection_name)
    except Exception:
        collection = _chroma_client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    for _fn in dict.fromkeys(filenames):
        try:
            collection.delete(where={"filename": _fn})
        except Exception:
            pass  # collection mới / chưa có chunk của file này

    embedder = _get_embedder()
    all_docs, all_ids, all_metas = [], [], []
    chunk_idx = 0
    sid_safe = _safe_sid(session_id)  # Định danh phiên đồng nhất với Chroma collection

    for filename, md_content in zip(filenames, md_contents):
        # ID ổn định theo file (md5 filename) để re-upload cùng file ghi đè đúng chunks cũ,
        # không bao giờ đụng ID của file khác (code cũ đếm chunk_idx từ 0 mỗi lần gọi).
        file_tag = hashlib.md5(filename.encode("utf-8")).hexdigest()[:8]
        # Tách nội dung theo page anchors để gắn metadata trang chính xác
        for match in _ANCHOR_RE.finditer(md_content):
            page_num  = int(match.group(1))
            page_text = match.group(2).strip()
            if not page_text:
                continue
            # Chia page text thành chunks nhỏ hơn nếu cần
            for chunk in _chunk_text(page_text):
                chunk = chunk.strip()
                if len(chunk) < 20:  # Bỏ qua đoạn văn bản quá ngắn không đủ ngữ cảnh
                    continue
                all_docs.append(chunk)
                all_ids.append(f"{sid_safe}_{file_tag}_{chunk_idx}")
                all_metas.append({"filename": filename, "page": page_num})
                chunk_idx += 1

    if not all_docs:
        return "Không trích xuất được nội dung từ tài liệu."

    # Mã hóa vector theo lô (batch encoding) để tăng tốc độ tính toán
    embeddings = embedder.encode(all_docs, batch_size=64, show_progress_bar=False).tolist()

    # ChromaDB giới hạn số lượng mục nạp mỗi lần gọi, chia lô khi vượt ngưỡng
    BATCH = 500
    for i in range(0, len(all_docs), BATCH):
        collection.upsert(
            documents=all_docs[i:i+BATCH],
            ids=all_ids[i:i+BATCH],
            embeddings=embeddings[i:i+BATCH],
            metadatas=all_metas[i:i+BATCH],
        )

    return f"Đã index {chunk_idx} đoạn từ {len(md_contents)} tài liệu."


def _ensure_session_indexed(session_id: str) -> bool:
    """[ponytail] Tự động nạp và vector hóa tài liệu từ disk nếu RAM collection chưa tồn tại."""
    collection_name = f"doc_session_{_safe_sid(session_id)}"
    try:
        col = _chroma_client.get_collection(collection_name)
        if col.count() > 0:
            return True
    except Exception:
        pass

    try:
        from doc_pipeline import _MD_DIR
        sid = _safe_sid(session_id)
        md_dir = _MD_DIR / sid
        if not md_dir.exists():
            return False
        md_files = [f for f in md_dir.glob("*.md") if f.is_file()]
        if not md_files:
            return False
        md_contents = [f.read_text(encoding="utf-8") for f in md_files]
        filenames = [f.name for f in md_files]
        index_session_docs(session_id, md_contents, filenames)
        return True
    except Exception:
        return False


def _query_collection(session_id: str, query: str, n_results: int = 5) -> list[dict]:
    """
    Truy vấn ChromaDB lấy n_results đoạn phù hợp nhất.
    Tự động hồi phục index từ disk nếu server vừa khởi động lại.
    Trả về list dict: {text, filename, page}
    """
    _ensure_session_indexed(session_id)
    collection_name = f"doc_session_{_safe_sid(session_id)}"
    try:
        collection = _chroma_client.get_collection(collection_name)
    except Exception:
        return []

    embedder    = _get_embedder()
    query_embed = embedder.encode([query]).tolist()

    results = None
    try:
        total = collection.count()
    except Exception:
        return []
    if not total:  # Tránh lỗi khi tập kết quả rỗng
        return []
    results = collection.query(
        query_embeddings=query_embed,
        n_results=min(n_results, total),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    for doc, meta in zip(docs, metas):
        chunks.append({"text": doc, "filename": (meta or {}).get("filename", ""), "page": (meta or {}).get("page", 0)})
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 3 PROMPT MODES
# ─────────────────────────────────────────────────────────────────────────────

def chat_with_doc(session_id: str, user_query: str) -> str:
    """
    Hỏi đáp tự do về tài liệu. Trả lời kèm số trang trích dẫn dạng [Xem trang X].
    """
    chunks = _query_collection(session_id, user_query, n_results=6)
    if not chunks:
        return "Chưa có tài liệu nào được tải lên trong phiên này. Vui lòng upload file PDF trước."

    context_parts = []
    for c in chunks:
        context_parts.append(f"[Trang {c['page']} – {c['filename']}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"Bạn là trợ lý học tập và nghiên cứu khoa học chuyên sâu. Dựa VÀO CHÍNH XÁC các đoạn trích dưới đây từ tài liệu, "
        f"hãy giải đáp câu hỏi của người dùng một cách chi tiết, mạch lạc và chuẩn mực học thuật.\n\n"
        f"YÊU CẦU ĐỊNH DẠNG & CÚ PHÁP:\n"
        f"1. Trích dẫn số trang: Luôn ghi rõ số trang theo định dạng chuẩn [Trang X] để người học dễ dàng đối chiếu.\n"
        f"2. Công thức Toán học & Kỹ thuật: BẮT BUỘC sử dụng cú pháp LaTeX chuẩn, kẹp trong dấu $...$ đối với công thức nội dòng (ví dụ: $a(t) = -9,8$, $\\int f(x)dx = F(x) + C$) hoặc $$...$$ đối với công thức khối riêng biệt.\n"
        f"3. NẾU TÀI LIỆU HOẶC CÂU HỎI LIÊN QUAN ĐẾN TOÁN HỌC, VẬT LÝ, KHOA HỌC DỮ LIỆU:\n"
        f"   - Phân tích bản chất định lý, các bước suy luận toán học hoặc phương pháp giải từng bước rõ ràng, dễ hiểu.\n"
        f"4. TUYỆT ĐỐI không bịa thêm thông tin không có trong đoạn trích.\n\n"
        f"=== CÁC ĐOẠN TRÍCH TỪ TÀI LIỆU ===\n{context}\n\n"
        f"=== CÂU HỎI CỦA NGƯỜI DÙNG ===\n{user_query}"
    )

    try:
        return _call_gemini(prompt) or "Không thể tạo câu trả lời lúc này."
    except Exception as e:
        return f"Lỗi khi gọi Gemini: {e}"


def summarize_doc(session_id: str, target: str = "") -> str:
    """
    Tóm tắt tài liệu theo 3 cấp: Ý tưởng then chốt – Luận điểm chứng minh – Kết luận thực tiễn.
    `target`: Tên chương/phần cần tóm tắt (để trống = tóm tắt toàn bộ).
    """
    query = target if target else "nội dung chính toàn bộ tài liệu"
    chunks = _query_collection(session_id, query, n_results=10)
    if not chunks:
        return "Chưa có tài liệu nào trong phiên này."

    context = "\n\n---\n\n".join(
        f"[Trang {c['page']}] {c['text']}" for c in chunks
    )
    scope = f'chương/phần "{target}"' if target else "toàn bộ tài liệu"

    prompt = (
        f"Bạn là trợ lý tóm tắt học thuật và phân tích tài liệu chuyên sâu. Hãy tóm tắt {scope} từ tài liệu theo cấu trúc chuẩn:\n\n"
        f"### 1. Ý TƯỞNG THEN CHỐT\nLuận điểm trung tâm, bài toán cốt lõi hoặc mục tiêu chính của tài liệu.\n\n"
        f"### 2. LUẬN ĐIỂM & MINH CHỨNG\nCác định lý, công thức, dữ liệu phân tích và bài tập tiêu biểu kèm trích dẫn số trang [Trang X].\n\n"
        f"### 3. KẾT LUẬN THỰC TIỄN\nBài học rút ra, ứng dụng thực tế hoặc phương pháp tiếp cận các dạng bài tương tự.\n\n"
        f"QUY TẮC CÚ PHÁP: Tất cả công thức toán học phải viết bằng cú pháp LaTeX chuẩn kẹp giữa cặp dấu $...$ (nội dòng) hoặc $$...$$ (khối riêng).\n\n"
        f"=== NỘI DUNG TÀI LIỆU ===\n{context}"
    )

    try:
        return _call_gemini(prompt) or "Không thể tóm tắt lúc này."
    except Exception as e:
        return f"Lỗi khi gọi Gemini: {e}"


def generate_quiz(session_id: str, topic: str = "", count: int = 5) -> str:
    """
    Tạo bộ câu hỏi trắc nghiệm (tùy chỉnh 5, 10, 15, 20... câu) dạng JSON.
    Format JSON trả về:
    [{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "B", "page_ref": 14, "explanation": "..."}]
    """
    count = min(max(int(count or 5), 1), 30)
    topic_clean = topic.strip()
    query = topic_clean if len(topic_clean) > 1 else "nội dung quan trọng toàn bộ tài liệu"
    n_results = min(15, max(8, count // 2 + 5))
    chunks = _query_collection(session_id, query, n_results=n_results)

    # Nếu query theo topic hẹp không ra kết quả, thử truy vấn toàn tài liệu
    if not chunks and query != "nội dung quan trọng toàn bộ tài liệu":
        chunks = _query_collection(session_id, "nội dung quan trọng toàn bộ tài liệu", n_results=n_results)

    # [ponytail] Fallback: Nếu ChromaDB rỗng/lỗi, đọc trực tiếp các trang từ file Markdown trên đĩa
    if not chunks:
        try:
            from doc_pipeline import _MD_DIR
            sid = _safe_sid(session_id)
            md_dir = _MD_DIR / sid
            if md_dir.exists():
                for md_file in md_dir.glob("*.md"):
                    content = md_file.read_text(encoding="utf-8")
                    for m in _ANCHOR_RE.finditer(content):
                        p_num = int(m.group(1))
                        p_txt = m.group(2).strip()
                        if p_txt:
                            chunks.append({"text": p_txt[:1200], "filename": md_file.name, "page": p_num})
                    if not chunks and content.strip():
                        chunks.append({"text": content[:3500], "filename": md_file.name, "page": 1})
        except Exception:
            pass

    if not chunks:
        return json.dumps([], ensure_ascii=False)

    context = "\n\n---\n\n".join(
        f"[Trang {c['page']}] {c['text']}" for c in chunks
    )
    scope = f'chủ đề "{topic_clean}"' if topic_clean else "toàn bộ tài liệu"

    prompt = (
        f"Bạn là giáo viên ra đề thi học thuật. Hãy tạo ĐÚNG {count} câu trắc nghiệm 4 đáp án (A, B, C, D) về {scope} từ tài liệu dưới đây.\n"
        f"Yêu cầu: Đầy đủ các cấp độ Nhận biết, Thông hiểu và Vận dụng. Đáp án sai phải có tính đánh lừa hợp lý.\n"
        f"Đối với câu hỏi hoặc các đáp án có công thức toán học/ký hiệu: BẮT BUỘC dùng cú pháp LaTeX kẹp trong $...$ (ví dụ: $\\int x^2 dx$, $f'(x) = 2x$) và giữa chữ với công thức phải có khoảng trắng rõ ràng.\n\n"
        f"Trả về ĐÚNG mảng JSON gồm {count} phần tử sau (không thêm bất kỳ văn bản nào ngoài JSON):\n"
        f'[{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, '
        f'"answer": "B", "page_ref": 14, "explanation": "Giải thích ngắn gọn tại sao B đúng."}}]\n\n'
        f"=== NỘI DUNG TÀI LIỆU ===\n{context}"
    )

    try:
        raw = _call_gemini(prompt) or "[]"
        # Bóc tách JSON array kể cả khi Gemini kèm lời chào mở đầu / kết thúc
        match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        else:
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            raw = re.sub(r"```\s*$", "", raw.strip())
        return raw
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
