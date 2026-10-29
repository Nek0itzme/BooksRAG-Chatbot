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


def _parse_quiz_json(raw: str) -> list[dict]:
    """Phân tích và bóc tách mảng JSON câu hỏi từ phản hồi của Gemini."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            res = data.get("quiz") or data.get("questions") or [data]
            return res if isinstance(res, list) else [res]
    except Exception:
        pass

    match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            res = data.get("quiz") or data.get("questions") or [data]
            return res if isinstance(res, list) else [res]
    except Exception:
        pass
    return []


def generate_quiz(session_id: str, topic: str = "", count: int = 5) -> str:
    """
    Tạo bộ câu hỏi trắc nghiệm (tùy chỉnh 5, 10, 20... đến 50+ câu) dạng JSON.
    Hỗ trợ tài liệu dài: tự động quét đa trang và chia lô xử lý khi số lượng câu hỏi lớn (>= 25 câu).
    Format JSON trả về:
    [{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "B", "page_ref": 14, "explanation": "..."}]
    """
    count = min(max(int(count or 5), 1), 60)
    topic_clean = topic.strip()
    query = topic_clean if len(topic_clean) > 1 else "nội dung quan trọng toàn bộ tài liệu"
    
    # Mở rộng số lượng chunk truy vấn phù hợp với số câu hỏi cần tạo
    n_results = min(40, max(10, count // 2 + 10))
    chunks = _query_collection(session_id, query, n_results=n_results)

    # Nếu query theo topic hẹp không ra kết quả, thử truy vấn toàn tài liệu
    if not chunks and query != "nội dung quan trọng toàn bộ tài liệu":
        chunks = _query_collection(session_id, "nội dung quan trọng toàn bộ tài liệu", n_results=n_results)

    # Đọc trực tiếp các trang từ file Markdown trên đĩa để đảm bảo phủ đều các trang của tài liệu dài
    try:
        from doc_pipeline import _MD_DIR
        sid = _safe_sid(session_id)
        md_dir = _MD_DIR / sid
        if md_dir.exists():
            disk_chunks = []
            for md_file in md_dir.glob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                for m in _ANCHOR_RE.finditer(content):
                    p_num = int(m.group(1))
                    p_txt = m.group(2).strip()
                    if p_txt:
                        disk_chunks.append({"text": p_txt[:1200], "filename": md_file.name, "page": p_num})
                if not disk_chunks and content.strip():
                    disk_chunks.append({"text": content[:3500], "filename": md_file.name, "page": 1})
            
            if not chunks:
                chunks = disk_chunks
            elif len(disk_chunks) > len(chunks) and count >= 20:
                # Bổ sung các trang chưa có trong chunks để bài thi phủ toàn diện tài liệu dài
                existing_pages = {c.get("page") for c in chunks}
                for dc in disk_chunks:
                    if dc.get("page") not in existing_pages:
                        chunks.append(dc)
                        existing_pages.add(dc.get("page"))
    except Exception:
        pass

    if not chunks:
        return json.dumps([], ensure_ascii=False)

    # Sắp xếp lại chunks theo số trang tăng dần để câu hỏi có trình tự logic
    chunks = sorted(chunks, key=lambda c: (c.get("filename", ""), c.get("page", 0)))
    scope = f'chủ đề "{topic_clean}"' if topic_clean else "toàn bộ tài liệu"

    def _call_gemini_quiz(sub_chunks: list[dict], sub_count: int, part_note: str = "") -> list[dict]:
        if not sub_chunks or sub_count <= 0:
            return []
        sub_context = "\n\n---\n\n".join(
            f"[Trang {c['page']}] {c['text']}" for c in sub_chunks
        )
        prompt = (
            f"Bạn là giáo viên ra đề thi học thuật xuất sắc. Hãy tạo ĐÚNG {sub_count} câu trắc nghiệm 4 đáp án (A, B, C, D) về {scope} từ tài liệu dưới đây {part_note}.\n"
            f"Yêu cầu chuyên môn:\n"
            f"- Đầy đủ các cấp độ: Nhận biết, Thông hiểu và Vận dụng.\n"
            f"- 4 phương án A, B, C, D độc lập, đáp án sai phải có tính đánh lừa hợp lý dựa trên nội dung tài liệu.\n"
            f"- BẮT BUỘC chỉ rõ số trang [page_ref] chứa kiến thức của câu hỏi.\n"
            f"- Đối với câu hỏi hoặc các đáp án có công thức toán học/ký hiệu: BẮT BUỘC dùng cú pháp LaTeX kẹp trong $...$ (ví dụ: $\\int x^2 dx$, $f'(x) = 2x$) và giữa chữ với công thức phải có khoảng trắng rõ ràng.\n\n"
            f"Trả về ĐÚNG mảng JSON gồm {sub_count} phần tử sau (không thêm bất kỳ văn bản, lời chào hay ghi chú nào ngoài JSON):\n"
            f'[{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, '
            f'"answer": "B", "page_ref": 14, "explanation": "Giải thích ngắn gọn tại sao B đúng và đối chiếu với tài liệu."}}]\n\n'
            f"=== NỘI DUNG TÀI LIỆU ===\n{sub_context}"
        )
        try:
            raw = _call_gemini(prompt) or "[]"
            return _parse_quiz_json(raw)
        except Exception:
            return []

    # Với số lượng câu lớn (>= 25 câu, ví dụ 50 câu), chia làm 2 đợt gọi để tránh tràn token và bao quát toàn tài liệu dài
    if count >= 25:
        count_1 = count // 2
        count_2 = count - count_1
        mid_idx = max(1, len(chunks) // 2)
        chunks_part1 = chunks[:mid_idx] if len(chunks) > 2 else chunks
        chunks_part2 = chunks[mid_idx:] if len(chunks) > 2 else chunks

        q1 = _call_gemini_quiz(chunks_part1, count_1, "(Đợt 1: Tập trung vào kiến thức nửa đầu tài liệu)")
        q2 = _call_gemini_quiz(chunks_part2, count_2, "(Đợt 2: Tập trung vào kiến thức nửa sau tài liệu hoặc vận dụng)")
        
        all_quiz = q1 + q2
        if len(all_quiz) < count:
            # Nếu còn thiếu một số câu, thử nạp bổ sung để đạt đủ số lượng yêu cầu
            remain = count - len(all_quiz)
            q_extra = _call_gemini_quiz(chunks, remain, "(Bổ sung thêm các câu hỏi vận dụng tổng hợp)")
            all_quiz += q_extra
    else:
        all_quiz = _call_gemini_quiz(chunks, count)

    return json.dumps(all_quiz[:count], ensure_ascii=False)
