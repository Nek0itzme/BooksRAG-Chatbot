# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #08 — Tích hợp Web Database (SQLite session persistence)
main.py — Máy chủ Web API FastAPI và điều phối luồng tư vấn sách RAG
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này cung cấp:
1. Máy chủ REST API bất đồng bộ với FastAPI và Uvicorn.
2. Quản lý phiên làm việc kết hợp: Cache RAM tốc độ cao và lưu trữ bền vững trong SQLite (WAL mode).
3. Bảo mật hệ thống: Giới hạn tần suất gọi (Rate Limiting với SlowAPI), CORS Middleware và xử lý ngoại lệ toàn cục.
4. Điều phối tác vụ tính toán nặng qua ThreadPool (asyncio.to_thread) để không làm nghẽn Event Loop.
5. Endpoints giám sát sức khỏe hệ thống (/health và /health/detailed).
"""

import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import uuid
import time
import json
import asyncio
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

# Thêm Web Database vào Python path
_WEB_DB_DIR = Path(__file__).parent.parent / "Web Database"
sys.path.insert(0, str(_WEB_DB_DIR))

# Đường dẫn thư mục Front End
FRONTEND_DIR = Path(__file__).parent.parent / "Front End"

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    HOST, PORT, SAMPLE_JSON,
    GEMINI_FLASH, GEMINI_FALLBACK, EMBEDDING_MODEL, ALPHA, TOP_K,
)
from models import ChatRequest, ChatResponse, BuyRequest, BookResult, HealthResponse
from rag_engine import run_rag, is_chroma_ready, _get_books, get_author_recommendations

# ── 1. TÍCH HỢP SQLITE SESSION DATABASE ───────────────────────────────────────
try:
    from db_manager import (
        init_db,
        create_or_get_user, create_session as db_create_session,
        ensure_session,
        get_session as db_get_session, save_message, get_session_history,
        save_book, get_saved_books,
    )
    from session_routes import router as auth_router, books_router, analytics_router
    _DB_ENABLED = True
except Exception as _db_err:
    _DB_ENABLED = False
    print(f"[WARN] Web Database không nạp được: {_db_err}")


# ── 2. VÒNG ĐỜI ỨNG DỤNG FASTAPI (LIFESPAN MANAGER) ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý vòng đời khởi động và kết thúc của ứng dụng FastAPI:
    - Khởi động: Tự động khởi tạo cấu trúc cơ sở dữ liệu SQLite nếu chưa có.
    - Kết thúc: Giải phóng tài nguyên an toàn.
    """
    if _DB_ENABLED:
        try:
            init_db()
        except Exception as e:
            print(f"[WARN] Không thể khởi tạo SQLite Database: {e}")
    yield


app = FastAPI(
    title="Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin",
    description=(
        "Hệ thống tư vấn sách ứng dụng kỹ thuật RAG nhằm giảm sai lệch thông tin và hỗ trợ tìm kiếm theo nhu cầu.\n\n"
        "- Dữ liệu sách thực tế: Tiki & Fahasa (697 cuốn)\n"
        "- Mô hình ngôn ngữ: Google Gemini 2.5 Flash & Multimodal Vision\n"
        "- Cơ sở dữ liệu vector: ChromaDB (all-MiniLM-L6-v2)\n"
        "- Lọc hình học không gian: Hyperbolic Poincaré Ball Entailment Cones (HyPE Filter)\n"
        "- Kiểm soát an toàn: Input & Output Rule Guardrail Harness"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── 3. GIỚI HẠN TẦN SUẤT TRUY CẬP (RATE LIMITING) ──────────────────────────────
# Mỗi địa chỉ IP được phép gửi tối đa 20 yêu cầu chat / phút để bảo vệ máy chủ
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── 4. XỬ LÝ NGOẠI LỆ TOÀN CỤC (GLOBAL EXCEPTION SHIELD) ──────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Bắt và đóng gói các lỗi hệ thống không mong muốn, tránh lộ Traceback ra Client."""
    return JSONResponse(
        status_code=500,
        content={"error": "Hệ thống đang xử lý yêu cầu khác, vui lòng thử lại sau giây lát."},
    )

# ── 5. CẤU HÌNH BẢO MẬT NGUỒN GỐC (CORS MIDDLEWARE) ───────────────────────────
_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Id"],
)

# ── 6. GẮN CÁC ROUTER WEB DATABASE ───────────────────────────────────────────
if _DB_ENABLED:
    app.include_router(auth_router)
    app.include_router(books_router)
    app.include_router(analytics_router)
    print("[OK] Đã kích hoạt các Router Database: /auth, /books, /analytics")

# ── 7. BỘ NHỚ PHIÊN TỐC ĐỘ CAO TRONG RAM (IN-MEMORY SESSION STORE) ─────────────
_sessions: Dict[str, dict] = {}
_SESSION_TTL_SECONDS = 7200  # 2 giờ không hoạt động -> Tự động xóa khỏi RAM
_sessions_lock = asyncio.Lock()


async def get_session(session_id: str) -> dict:
    """Truy cập và cập nhật trạng thái phiên an toàn đa luồng (Thread-safe) với asyncio.Lock."""
    async with _sessions_lock:
        if session_id not in _sessions:
            _sessions[session_id] = {"history": [], "purchased": [], "_last_active": time.time()}
        else:
            _sessions[session_id]["_last_active"] = time.time()
        return _sessions[session_id]


def _cleanup_expired_sessions() -> None:
    """Tiến trình ngầm (Daemon Thread) tự động quét và thu hồi bộ nhớ phiên hết hạn định kỳ mỗi 10 phút."""
    while True:
        time.sleep(600)
        now = time.time()
        expired = [
            sid for sid, s in list(_sessions.items())
            if now - s.get("_last_active", now) > _SESSION_TTL_SECONDS
        ]
        for sid in expired:
            _sessions.pop(sid, None)
        if expired:
            print(f"[SessionCleanup] Đã giải phóng {len(expired)} phiên làm việc hết hạn khỏi RAM.")


threading.Thread(target=_cleanup_expired_sessions, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# ĐỊNH NGHĨA CÁC ĐIỂM CUỐI GIAO TIẾP (API ENDPOINTS)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Phục vụ trực tiếp giao diện Web đơn trang (SPA) tại địa chỉ gốc."""
    html_path = FRONTEND_DIR / "index.html"
    return FileResponse(html_path)


@app.get("/avatar.png", include_in_schema=False)
async def serve_avatar():
    """Phục vụ ảnh đại diện avatar người dùng."""
    avatar_path = Path(__file__).parent / "avatar.png"
    if avatar_path.exists():
        return FileResponse(avatar_path)
    raise HTTPException(status_code=404, detail="Avatar not found")


@app.get("/avatar_data.js", include_in_schema=False)
async def serve_avatar_data_js():
    """Phục vụ file script chứa dữ liệu Base64 avatar hỗ trợ hoạt động ngoại tuyến 100%."""
    js_path = FRONTEND_DIR / "avatar_data.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="avatar_data.js not found")


@app.get("/user_black.png", include_in_schema=False)
@app.get("/assets/user_black.png", include_in_schema=False)
async def serve_user_black():
    """Phục vụ icon avatar cho chế độ giao diện tối (Dark Mode)."""
    p = Path(__file__).parent / "user_black.png"
    if p.exists():
        return FileResponse(p)
    p_assets = Path(__file__).parent / "assets" / "user_black.png"
    if p_assets.exists():
        return FileResponse(p_assets)
    raise HTTPException(status_code=404, detail="user_black.png not found")


@app.get("/user_white.png", include_in_schema=False)
@app.get("/assets/user_white.png", include_in_schema=False)
async def serve_user_white():
    """Phục vụ icon avatar cho chế độ giao diện sáng (Light Mode)."""
    p = Path(__file__).parent / "user_white.png"
    if p.exists():
        return FileResponse(p)
    p_assets = Path(__file__).parent / "assets" / "user_white.png"
    if p_assets.exists():
        return FileResponse(p_assets)
    raise HTTPException(status_code=404, detail="user_white.png not found")


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Kiểm tra nhanh trạng thái sẵn sàng của dịch vụ và cơ sở dữ liệu vector."""
    books = _get_books()
    return HealthResponse(
        status="ok",
        total_books=len(books),
        chroma_ready=is_chroma_ready(),
    )


@app.get("/health/detailed", tags=["System"])
async def health_check_detailed():
    """
    KIỂM TRA CHI TIẾT TẤT CẢ CÁC MÔ-ĐUN HỆ THỐNG PHỤC VỤ BÁO CÁO KHOA HỌC:
    Đo lường tính sẵn sàng của ChromaDB, HyPE Filter, SQLite DB, Rule Harness và Gemini.
    """
    from rag_engine import _HYPE_ENABLED, is_chroma_ready, _get_books

    books = _get_books()
    chroma_ok = is_chroma_ready()

    hype_status = "enabled" if _HYPE_ENABLED else "disabled (torch/geoopt missing)"
    db_status = "enabled" if _DB_ENABLED else "disabled"
    db_msg_count = 0
    if _DB_ENABLED:
        try:
            from db_manager import get_db_stats
            db_msg_count = get_db_stats().get("total_messages", 0)
        except Exception:
            pass

    from rag_engine import InputRuleHarness as _IRH, OutputRuleHarness as _ORH
    rule_input  = "enabled" if _IRH else "disabled"
    rule_output = "enabled" if _ORH else "disabled"

    return {
        "status": "ok",
        "modules": {
            "chroma_vector_db": {
                "status": "ok" if chroma_ok else "error",
                "total_books_indexed": len(books) if chroma_ok else 0,
                "total_books_json": len(books),
            },
            "hype_filter": {
                "status": hype_status,
                "description": "Hyperbolic Poincaré Ball Entailment Cone Filter (ECCV 2024)",
            },
            "sqlite_session_db": {
                "status": db_status,
                "total_messages_logged": db_msg_count,
            },
            "rule_harness": {
                "input_harness": rule_input,
                "output_harness": rule_output,
            },
        },
        "config": {
            "llm_primary": GEMINI_FLASH,
            "llm_fallback": GEMINI_FALLBACK,
            "embedding_model": EMBEDDING_MODEL,
            "alpha_semantic_weight": ALPHA,
            "top_k_results": TOP_K,
        },
    }


@app.get("/books", tags=["Data"])
async def list_books(
    category: str = None,
    in_stock: bool = None,
    min_rating: float = None,
    max_price: int = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Truy xuất danh mục sách trong kho có hỗ trợ bộ lọc đa điều kiện và phân trang dữ liệu (Pagination).
    """
    books = _get_books()
    filtered = books

    if category:
        filtered = [b for b in filtered if category.lower() in b.get("category", "").lower()]
    if in_stock is not None:
        filtered = [b for b in filtered if b.get("in_stock") == in_stock]
    if min_rating is not None:
        filtered = [b for b in filtered if float(b.get("rating", 0)) >= min_rating]
    if max_price is not None:
        filtered = [b for b in filtered if int(b.get("price", 0)) <= max_price]

    total = len(filtered)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "books": filtered[offset: offset + limit],
    }


@app.post("/chat", response_model=ChatResponse, tags=["RAG"])
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    """
    ENDPOINT TƯ VẤN SÁCH CỐT LÕI (CORE RAG PIPELINE ENDPOINT).
    Tiếp nhận câu hỏi, điều phối luồng xử lý RAG 5 bước bất đồng bộ và trả về kết quả tư vấn chuẩn xác.
    """
    # 1. Quản lý phiên hội thoại trong RAM
    session_id = req.session_id or str(uuid.uuid4())
    session    = await get_session(session_id)

    # Ghi nhận câu hỏi vào lịch sử RAM
    session["history"].append({"role": "user", "content": req.message})

    # 2. Đồng bộ hóa với cơ sở dữ liệu SQLite
    if _DB_ENABLED:
        if not session.get("db_session_id"):
            anon_user = create_or_get_user("anonymous", "Anonymous User")
            ensure_session(session_id, anon_user["user_id"], "web-client")
            session["db_session_id"] = session_id
            session["db_user_id"] = anon_user["user_id"]

    db_session_id = session.get("db_session_id")
    if _DB_ENABLED and db_session_id:
        db_history = get_session_history(db_session_id, limit=10)
        merged_history = db_history + session["history"][-4:]
    else:
        merged_history = session["history"]

    t0 = time.time()
    # 3. Chạy pipeline RAG trên luồng phụ (Thread Pool) để tránh block Event Loop chính
    result = await asyncio.to_thread(
        run_rag,
        message=req.message,
        budget=req.budget,
        session_history=merged_history,
        purchased_book_id=req.purchased_book_id,
        image_data=req.image_data,
    )
    latency = int((time.time() - t0) * 1000)

    # Ghi câu trả lời vào lịch sử RAM
    session["history"].append({"role": "model", "content": result["answer"]})

    # 4. Lưu vết hội thoại lâu dài vào SQLite
    if _DB_ENABLED and db_session_id:
        db_user_id = session.get("db_user_id", "anonymous")
        book_ids   = [b.get("id", "") for b in result.get("books", [])]
        save_message(db_session_id, db_user_id, "user", req.message,
                     query_type=result.get("query_type", ""), latency_ms=0)
        save_message(db_session_id, db_user_id, "model", result["answer"],
                     query_type=result.get("query_type", ""),
                     book_ids=book_ids, latency_ms=latency)

    # Chuyển đổi sang Pydantic Model BookResult
    def to_book_result(b: dict) -> BookResult:
        return BookResult(
            id=b.get("id", ""),
            title=b.get("title", ""),
            author=b.get("author", ""),
            category=b.get("category", ""),
            publisher=b.get("publisher", ""),
            price=b.get("price", 0),
            original_price=b.get("original_price", b.get("price", 0)),
            rating=b.get("rating", 0),
            sold_count=b.get("sold_count", 0),
            in_stock=b.get("in_stock", True),
            tags=b.get("tags", []),
            description=b.get("description", ""),
            target_audience=b.get("target_audience", ""),
            score_semantic=b.get("score_semantic", 0.0),
            score_ranking=b.get("score_ranking", 0.0),
            score_total=b.get("score_total", 0.0),
            score_hype=b.get("score_hype", 0.0),
        )

    return ChatResponse(
        answer=result["answer"],
        books=[to_book_result(b) for b in result["books"]],
        author_recs=[to_book_result(b) for b in result.get("author_recs", [])],
        session_id=session_id,
        query_type=result.get("query_type", "general"),
        query_context=result.get("query_context", ""),
        found=result.get("found", True),
        vision_info=result.get("vision_info"),
    )


@app.post("/auth/link-session", tags=["Auth"])
async def link_session(body: dict):
    """
    Liên kết phiên làm việc RAM với phiên cơ sở dữ liệu SQLite sau khi người dùng đăng nhập.
    """
    ram_id = body.get("session_id", "")
    db_sid = body.get("db_session_id", "")
    db_uid = body.get("db_user_id", "")

    if not ram_id or not db_sid:
        raise HTTPException(status_code=400, detail="session_id và db_session_id là bắt buộc")

    if _DB_ENABLED and db_sid:
        db_sess = db_get_session(db_sid)
        if not db_sess:
            raise HTTPException(status_code=403, detail="DB session không tồn tại hoặc đã hết hạn.")
        if db_uid and db_sess.get("user_id") != db_uid:
            raise HTTPException(status_code=403, detail="db_user_id không khớp với session. Truy cập bị từ chối.")

    session = await get_session(ram_id)
    session["db_session_id"] = db_sid
    session["db_user_id"]    = db_uid

    if _DB_ENABLED:
        history = get_session_history(db_sid, limit=20)
        session["history"] = history
        return {"status": "linked", "history_loaded": len(history)}

    return {"status": "linked_no_db", "history_loaded": 0}


@app.post("/buy", tags=["In-session"])
async def record_purchase(req: BuyRequest):
    """
    GHI NHẬN HÀNH VI CHỌN MUA SÁCH VÀ KÍCH HOẠT GỢI Ý TÁC GIẢ LIỀN MẠCH.
    """
    all_books = _get_books()
    purchased_book = next((b for b in all_books if b["id"] == req.book_id), None)

    if purchased_book is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy sách với ID '{req.book_id}' trong kho dữ liệu."
        )

    session = await get_session(req.session_id)

    if req.book_id not in session["purchased"]:
        session["purchased"].append(req.book_id)

    exclude = session["purchased"]
    recs = get_author_recommendations(req.book_id, exclude_ids=exclude)

    return {
        "status": "recorded",
        "purchased_book": purchased_book,
        "author_recommendations": recs,
        "message": (
            f"✅ Đã ghi nhận bạn chọn mua '{purchased_book['title']}'. "
            f"Gợi ý thêm {len(recs)} tác phẩm cùng tác giả!"
            if recs else
            f"✅ Đã ghi nhận. Không tìm thêm được tác phẩm cùng tác giả trong kho."
        ),
    }


@app.post("/remove_from_cart", tags=["In-session"])
async def remove_from_cart(req: BuyRequest):
    """Xóa sách khỏi giỏ hàng tạm thời trong phiên."""
    session = await get_session(req.session_id)
    if req.book_id in session["purchased"]:
        session["purchased"].remove(req.book_id)
    return {"status": "removed", "book_id": req.book_id, "remaining_count": len(session["purchased"])}


@app.delete("/session/{session_id}", tags=["System"])
async def clear_session(session_id: str):
    """Xóa lịch sử phiên chat khi người dùng muốn làm mới cuộc trò chuyện."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "cleared", "session_id": session_id}


# ── 8. KHỞI ĐỘNG MÁY CHỦ UVICORN ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
