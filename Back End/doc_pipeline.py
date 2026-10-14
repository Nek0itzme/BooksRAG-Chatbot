# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #16 — Trích xuất văn bản tài liệu PDF sang Markdown
doc_pipeline.py — Pipeline chuyển đổi PDF → Markdown kèm thẻ Page Anchor
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Nhiệm vụ:
1. Nhận tối đa 5 file PDF, lưu vào database/user_uploads/pdf/{session_id}/
2. Dùng PyMuPDF bóc tách text từng trang, chèn <!-- PAGE_ANCHOR: X --> markers
3. Lưu file .md vào database/user_uploads/markdown/{session_id}/
4. Trả về metadata (tên file, số trang, path PDF/MD) cho client
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Thêm Web Database vào sys.path để gọi db_manager
_WEB_DB_DIR = Path(__file__).parent.parent / "Web Database"
if str(_WEB_DB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DB_DIR))

# Sử dụng PyMuPDF (fitz) bóc tách văn bản PDF sang định dạng Markdown
try:
    import pymupdf as fitz
except ImportError:
    import fitz

# ── PATHS ──────────────────────────────────────────────────────────────────────
_BASE    = Path(__file__).parent.parent
_PDF_DIR = _BASE / "database" / "user_uploads" / "pdf"
_MD_DIR  = _BASE / "database" / "user_uploads" / "markdown"

# Pre-compile để strip header/footer rác (số trang đứng đơn lẻ trên dòng)
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)

MAX_FILES = 5

import zipfile
import xml.etree.ElementTree as ET

_SID_RE = re.compile(r"[^\w\-]")


def _safe_sid(sid: str) -> str:
    return (_SID_RE.sub("_", (sid or "").strip())[:64] or "sess_demo")  # Chuẩn hóa định danh, ngăn chặn ký tự ../ ra ngoài thư mục


def _pdf_to_markdown(pdf_path: Path) -> str:
    """
    Chuyển toàn bộ file PDF sang chuỗi Markdown có thẻ PAGE_ANCHOR.
    Mỗi trang được bọc bởi <!-- PAGE_ANCHOR: X --> ... <!-- PAGE_ANCHOR_END: X -->
    """
    doc = fitz.open(str(pdf_path))
    try:
        parts: list[str] = []
        for page_num, page in enumerate(doc, start=1):  # type: ignore
            # Trích xuất văn bản thuần để tối ưu hiệu năng xử lý
            raw = page.get_text("text") or ""
            # Xóa dòng chỉ chứa số trang (header/footer rác phổ biến)
            cleaned = _PAGE_NUM_RE.sub("", raw).strip()
            if not cleaned:
                continue
            parts.append(
                f"<!-- PAGE_ANCHOR: {page_num} -->\n"
                f"{cleaned}\n"
                f"<!-- PAGE_ANCHOR_END: {page_num} -->"
            )
    finally:
        # FIX: luôn đóng file handle kể cả khi bóc tách giữa chừng bị lỗi —
        # trước đây exception sẽ bỏ qua doc.close() gây leak handle + kẹt file trên Windows.
        doc.close()
    return "\n\n".join(parts)


def _docx_to_markdown(docx_path: Path) -> str:
    """
    [ponytail] Trích xuất văn bản từ file .docx bằng stdlib zipfile + xml.etree.
    Không phụ thuộc thư viện ngoài (stdlib first). Tự động phân trang logic (~350 từ hoặc ngắt trang cứng).
    Hỗ trợ Headings, Bảng biểu (w:tbl) và định dạng văn bản thành Markdown.
    """
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            xml_bytes = z.read("word/document.xml")
    except Exception as e:
        return f"<!-- PAGE_ANCHOR: 1 -->\n(Không đọc được file DOCX: {e})\n<!-- PAGE_ANCHOR_END: 1 -->"

    root = ET.fromstring(xml_bytes)
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = root.find(f"{{{ns_w}}}body")
    if body is None:
        return "<!-- PAGE_ANCHOR: 1 -->\n(Tài liệu rỗng)\n<!-- PAGE_ANCHOR_END: 1 -->"

    blocks: list[tuple[str, bool]] = []

    for elem in body:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "p":
            has_break = any(br.get(f"{{{ns_w}}}type") == "page" for br in elem.iter(f"{{{ns_w}}}br"))
            p_style = elem.find(f"{{{ns_w}}}pPr/{{{ns_w}}}pStyle")
            style_val = p_style.get(f"{{{ns_w}}}val", "").lower() if p_style is not None else ""

            p_text = "".join(node.text for node in elem.iter(f"{{{ns_w}}}t") if node.text).strip()
            if not p_text:
                continue

            if any(k in style_val for k in ["heading1", "heading 1", "tiêu đề 1"]):
                p_text = f"## {p_text}"
            elif any(k in style_val for k in ["heading2", "heading 2", "tiêu đề 2"]):
                p_text = f"### {p_text}"
            elif any(k in style_val for k in ["heading3", "heading 3", "tiêu đề 3"]):
                p_text = f"#### {p_text}"

            blocks.append((p_text, has_break))

        elif tag == "tbl":
            rows_data = []
            for tr in elem.iter(f"{{{ns_w}}}tr"):
                row_cells = []
                for tc in tr.iter(f"{{{ns_w}}}tc"):
                    cell_text = " ".join(node.text for node in tc.iter(f"{{{ns_w}}}t") if node.text).strip()
                    row_cells.append(cell_text.replace("|", "\\|"))
                if row_cells:
                    rows_data.append(row_cells)
            if rows_data:
                col_count = max(len(r) for r in rows_data)
                norm_rows = [r + [""] * (col_count - len(r)) for r in rows_data]
                header_line = "| " + " | ".join(norm_rows[0]) + " |"
                sep_line = "| " + " | ".join(["---"] * col_count) + " |"
                body_lines = ["| " + " | ".join(r) + " |" for r in norm_rows[1:]]
                tbl_md = "\n".join([header_line, sep_line] + body_lines)
                blocks.append((tbl_md, False))

    if not blocks:
        return "<!-- PAGE_ANCHOR: 1 -->\n(Tài liệu rỗng)\n<!-- PAGE_ANCHOR_END: 1 -->"

    pages: list[str] = []
    current_page: list[str] = []
    words = 0

    for text, has_break in blocks:
        current_page.append(text)
        words += len(text.split())
        if has_break or words >= 350:
            pages.append("\n\n".join(current_page))
            current_page = []
            words = 0

    if current_page:
        pages.append("\n\n".join(current_page))

    parts = [
        f"<!-- PAGE_ANCHOR: {idx} -->\n{pg}\n<!-- PAGE_ANCHOR_END: {idx} -->"
        for idx, pg in enumerate(pages, start=1)
    ]
    return "\n\n".join(parts)


def process_upload(
    file_bytes: bytes,
    original_filename: str,
    session_id: str,
) -> dict:
    """
    Lưu một file (PDF hoặc DOCX) và tạo bản transcript Markdown tương ứng.

    Returns:
        dict với các key: pdf_name, filename, file_type, md_name, pdf_path, md_path, page_count
    """
    # Tạo thư mục theo session nếu chưa có
    sid = _safe_sid(session_id)
    doc_session_dir = _PDF_DIR / sid
    md_session_dir  = _MD_DIR  / sid
    doc_session_dir.mkdir(parents=True, exist_ok=True)
    md_session_dir.mkdir(parents=True, exist_ok=True)

    is_docx = original_filename.lower().endswith(".docx")
    ext = ".docx" if is_docx else ".pdf"

    # Làm sạch tên file
    safe_name = re.sub(r"[^\w\-.]", "_", Path(original_filename).stem)
    file_path = doc_session_dir / f"{safe_name}{ext}"
    md_path   = md_session_dir  / f"{safe_name}.md"

    # Lưu file gốc
    file_path.write_bytes(file_bytes)

    # Chuyển sang Markdown
    if is_docx:
        md_content = _docx_to_markdown(file_path)
    else:
        md_content = _pdf_to_markdown(file_path)
    md_path.write_text(md_content, encoding="utf-8")

    # Đếm số trang thực tế từ số thẻ anchor
    page_count = md_content.count("<!-- PAGE_ANCHOR: ")

    # Lưu thông tin tài liệu vào SQLite database để quản lý phiên và chống trùng lặp
    doc_id = None
    is_duplicate = False
    replaced_count = 0
    try:
        from db_manager import save_uploaded_doc
        res = save_uploaded_doc(
            session_id=sid,
            filename=original_filename,
            file_path=str(file_path),
            file_size=len(file_bytes),
            page_count=page_count
        )
        if isinstance(res, (tuple, list)):
            doc_id, replaced_count = res
            is_duplicate = (replaced_count > 0)
        else:
            doc_id = res
    except Exception:
        pass

    return {
        "doc_id":         doc_id,
        "is_duplicate":   is_duplicate,
        "replaced_count": replaced_count,
        "pdf_name":       file_path.name,
        "filename":       file_path.name,
        "file_type":      "docx" if is_docx else "pdf",
        "md_name":        md_path.name,
        "pdf_path":       str(file_path),
        "md_path":        str(md_path),
        "page_count":     page_count,
    }



def list_session_files(session_id: str) -> dict:
    """Liệt kê các file PDF, DOCX và Markdown hiện có trong một phiên."""
    sid = _safe_sid(session_id)
    doc_dir = _PDF_DIR / sid
    md_dir  = _MD_DIR  / sid
    docs = []
    if doc_dir.exists():
        docs = [f.name for f in doc_dir.iterdir() if f.suffix.lower() in [".pdf", ".docx"]]
    return {
        "pdf_files": docs,
        "doc_files": docs,
        "md_files":  [f.name for f in md_dir.glob("*.md")]   if md_dir.exists()  else [],
    }


def get_markdown_content(session_id: str, md_filename: str) -> Optional[str]:
    """Đọc nội dung file Markdown đã transcript, trả về None nếu không tìm thấy."""
    md_path = (_MD_DIR / _safe_sid(session_id) / Path(md_filename).name).resolve()
    if _MD_DIR.resolve() not in md_path.parents:  # Ngăn chặn tấn công path traversal
        return None
    if not md_path.exists():
        return None
    return md_path.read_text(encoding="utf-8")


def get_pdf_path(session_id: str, pdf_filename: str) -> Optional[Path]:
    """Trả về Path tới file PDF gốc để phục vụ PDF Preview, None nếu không tìm thấy."""
    p = (_PDF_DIR / _safe_sid(session_id) / Path(pdf_filename).name).resolve()
    if _PDF_DIR.resolve() not in p.parents:  # Ngăn chặn tấn công path traversal
        return None
    return p if p.exists() else None


def get_document_details(session_id: str, filename: str) -> Optional[dict]:
    """
    [ponytail] Trả về chi tiết nội dung tài liệu (cho cả DOCX và PDF),
    bao gồm danh sách các trang logic đã bóc tách để hiển thị trong Document Reader View.
    """
    sid = _safe_sid(session_id)
    base_stem = Path(filename).stem
    safe_stem = re.sub(r"[^\w\-.]", "_", base_stem)
    md_dir = _MD_DIR / sid

    candidates = [
        md_dir / f"{filename}.md",
        md_dir / f"{safe_stem}.md",
        md_dir / f"{base_stem}.md",
        md_dir / filename,
    ]
    target_md = None
    for c in candidates:
        if c.exists() and _MD_DIR.resolve() in c.resolve().parents:
            target_md = c
            break

    if not target_md and md_dir.exists():
        for f in md_dir.glob("*.md"):
            if safe_stem.lower() in f.stem.lower() or f.stem.lower() in safe_stem.lower():
                target_md = f
                break

    if not target_md or not target_md.exists():
        return None

    raw_text = target_md.read_text(encoding="utf-8")

    # Phân tách theo thẻ <!-- PAGE_ANCHOR: X -->
    pattern = r"<!--\s*PAGE_ANCHOR:\s*(\d+)\s*-->([\s\S]*?)<!--\s*PAGE_ANCHOR_END:\s*\1\s*-->"
    matches = list(re.finditer(pattern, raw_text))

    pages = []
    if matches:
        for m in matches:
            p_num = int(m.group(1))
            p_text = m.group(2).strip()
            pages.append({"page_num": p_num, "content": p_text})
    else:
        simple_splits = re.split(r"<!--\s*PAGE_ANCHOR:\s*(\d+)\s*-->", raw_text)
        if len(simple_splits) > 1:
            for i in range(1, len(simple_splits), 2):
                p_num = int(simple_splits[i])
                p_text = simple_splits[i + 1].split("<!-- PAGE_ANCHOR_END:")[0].strip()
                pages.append({"page_num": p_num, "content": p_text})
        else:
            pages.append({"page_num": 1, "content": raw_text.strip()})

    word_count = len(raw_text.split())

    return {
        "filename": filename,
        "page_count": len(pages),
        "word_count": word_count,
        "char_count": len(raw_text),
        "pages": pages,
        "raw_markdown": raw_text,
    }


def reuse_saved_document(doc: dict, target_session_id: str) -> dict:
    """
    [ponytail] Tái sử dụng tài liệu đã lưu:
    Sử dụng chính file Markdown và file gốc đã lưu trong session trước đó.
    KHÔNG bóc tách lại, KHÔNG duplicate file, KHÔNG chèn thêm bản ghi mới vào database.
    """
    sid = _safe_sid(target_session_id)
    doc_session_dir = _PDF_DIR / sid
    md_session_dir  = _MD_DIR  / sid
    doc_session_dir.mkdir(parents=True, exist_ok=True)
    md_session_dir.mkdir(parents=True, exist_ok=True)

    source_file_path = Path(doc["file_path"]).resolve()
    if not source_file_path.exists():
        raise FileNotFoundError(f"File gốc không tồn tại: {doc.get('filename')}")

    filename = doc["filename"]
    is_docx = filename.lower().endswith(".docx")
    ext = ".docx" if is_docx else ".pdf"
    safe_name = re.sub(r"[^\w\-.]", "_", Path(filename).stem)

    target_file = doc_session_dir / f"{safe_name}{ext}"
    target_md   = md_session_dir  / f"{safe_name}.md"

    # 1. Tìm và tái sử dụng chính file Markdown đã lưu trước đó
    md_content = None
    old_sid = _safe_sid(doc.get("session_id", ""))
    old_md_candidates = [
        _MD_DIR / old_sid / f"{safe_name}.md",
        _MD_DIR / old_sid / f"{Path(filename).stem}.md",
        Path(str(source_file_path).replace("/pdf/", "/markdown/").replace("\\pdf\\", "\\markdown\\")).with_suffix(".md"),
    ]
    for cand in old_md_candidates:
        if cand.exists():
            try:
                md_content = cand.read_text(encoding="utf-8")
                break
            except Exception:
                pass

    # Nếu vì lý do nào đó file Markdown cũ chưa có, bóc tách dự phòng 1 lần
    if not md_content:
        if is_docx:
            md_content = _docx_to_markdown(source_file_path)
        else:
            md_content = _pdf_to_markdown(source_file_path)

    # Đưa file Markdown vào session hiện tại để phục vụ Chat RAG và Reader View
    target_md.write_text(md_content, encoding="utf-8")

    # 2. Đưa file PDF/DOCX gốc vào session hiện tại (để preview / download) nếu khác đường dẫn
    if source_file_path != target_file.resolve():
        try:
            target_file.write_bytes(source_file_path.read_bytes())
        except Exception:
            pass

    page_count = doc.get("page_count") or md_content.count("<!-- PAGE_ANCHOR: ") or 1

    return {
        "doc_id":         doc.get("id"),
        "is_duplicate":   False,
        "replaced_count": 0,
        "pdf_name":       target_file.name,
        "filename":       target_file.name,
        "file_type":      "docx" if is_docx else "pdf",
        "md_name":        target_md.name,
        "pdf_path":       target_file,
        "md_path":        target_md,
        "page_count":     page_count,
        "md_content":     md_content,
    }
