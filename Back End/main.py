# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #08 — Tích hợp Web Database (SQLite session persistence)
Tích hợp Web Database (SQLite session persistence)
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
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except Exception:
        pass

import os
import re
import uuid
import time
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

# Thêm Web Database vào Python path
_WEB_DB_DIR = Path(__file__).parent.parent / "Web Database"
sys.path.insert(0, str(_WEB_DB_DIR))

# Đường dẫn thư mục Front End
FRONTEND_DIR = Path(__file__).parent.parent / "Front End"

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    HOST, PORT, SAMPLE_JSON,
    GEMINI_FLASH, GEMINI_FALLBACK, EMBEDDING_MODEL, ALPHA, TOP_K,
)
from models import ChatRequest, ChatResponse, BuyRequest, BookResult, HealthResponse
from rag_engine import (
    run_rag, is_chroma_ready, _get_books, get_author_recommendations,
    _HYPE_ENABLED, InputRuleHarness, OutputRuleHarness,
)

# ── 1. TÍCH HỢP SQLITE SESSION DATABASE ───────────────────────────────────────
init_db: Any = None
create_or_get_user: Any = None
db_create_session: Any = None
ensure_session: Any = None
db_get_session: Any = None
save_message: Any = None
get_session_history: Any = None
save_book: Any = None
get_saved_books: Any = None
save_uploaded_doc: Any = None
get_uploaded_docs: Any = None
get_uploaded_doc_by_id: Any = None
delete_uploaded_doc: Any = None
cleanup_duplicate_uploaded_docs: Any = None
get_db_stats: Any = None
auth_router: Any = None
books_router: Any = None
analytics_router: Any = None

try:
    from db_manager import (  # type: ignore
        init_db,
        create_or_get_user, create_session as db_create_session,
        ensure_session,
        get_session as db_get_session, save_message, get_session_history,
        save_book, get_saved_books,
        save_uploaded_doc, get_uploaded_docs, get_uploaded_doc_by_id,
        delete_uploaded_doc, cleanup_duplicate_uploaded_docs,
        get_db_stats,
    )
    from session_routes import router as auth_router, books_router, analytics_router  # type: ignore
    _DB_ENABLED = True
except Exception as _db_err:
    _DB_ENABLED = False
    print(f"[WARN] Web Database không nạp được: {_db_err}")


# ── 2. VÒNG ĐỜI ỨNG DỤNG FASTAPI (LIFESPAN MANAGER) ───────────────────────────
async def _periodic_session_cleanup() -> None:
    """
    FIX: dọn RAM định kỳ bằng asyncio task thay vì threading.Thread lúc import.
    Code cũ dùng thread nền truy cập `_sessions` trong khi request async cũng sửa dict đó
    (race: cleanup pop đúng lúc request đang append history), và gây side-effect khi import
    module trong test. Task này chạy cùng Event Loop, dọn dưới `_sessions_lock` nên an toàn.
    """
    while True:
        await asyncio.sleep(600)
        try:
            async with _sessions_lock:
                now = time.time()
                expired = [
                    sid for sid, s in _sessions.items()
                    if now - s.get("_last_active", now) > _SESSION_TTL_SECONDS
                ]
                for sid in expired:
                    _sessions.pop(sid, None)
                if expired:
                    print(f"[SessionCleanup] Đã giải phóng {len(expired)} phiên làm việc hết hạn khỏi RAM.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[WARN] SessionCleanup lỗi: {e}")


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
            cleaned = cleanup_duplicate_uploaded_docs()
            if cleaned > 0:
                print(f"[INFO] Đã dọn dẹp {cleaned} tài liệu PDF trùng lặp trong sessions.db.")
        except Exception as e:
            print(f"[WARN] Không thể khởi tạo SQLite Database: {e}")
    cleanup_task = asyncio.create_task(_periodic_session_cleanup())
    try:
        yield
    finally:
        cleanup_task.cancel()


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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# ── 4. XỬ LÝ NGOẠI LỆ TOÀN CỤC (GLOBAL EXCEPTION SHIELD) ──────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Bắt và đóng gói các lỗi hệ thống không mong muốn, tránh lộ Traceback ra Client."""
    # FIX: Không nuốt HTTPException (404/400/401...) — để FastAPI trả đúng status code.
    # Trước đây handler này bắt cả HTTPException (vì HTTPException kế thừa Exception)
    # khiến mọi lỗi 4xx (sách không tồn tại, thiếu param...) đều biến thành 500.
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    print(f"[ERROR] Ngoại lệ chưa xử lý tại {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Hệ thống đang xử lý yêu cầu khác, vui lòng thử lại sau giây lát."},
    )

# ── 5. CẤU HÌNH BẢO MẬT NGUỒN GỐC (CORS MIDDLEWARE) ───────────────────────────
# FIX: tắt allow_credentials — frontend chỉ dùng header X-Session-Id + localStorage,
# không dùng cookie nên không cần credentials. Combo cũ (regex allow-all + credentials)
# vừa yếu bảo mật vừa bị trình duyệt chặn trong một số trường hợp.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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


# ─────────────────────────────────────────────────────────────────────────────
# ĐỊNH NGHĨA CÁC ĐIỂM CUỐI GIAO TIẾP (API ENDPOINTS)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Phục vụ trực tiếp giao diện Web đơn trang (SPA) tại địa chỉ gốc."""
    html_path = FRONTEND_DIR / "index.html"
    # FIX: kiểm tra tồn tại trước khi trả file — trước đây thiếu file sẽ nổ 500 (RuntimeError).
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
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
    books = _get_books()
    chroma_ok = is_chroma_ready()

    hype_status = "enabled" if _HYPE_ENABLED else "disabled (torch/geoopt missing)"
    db_status = "enabled" if _DB_ENABLED else "disabled"
    db_msg_count = 0
    if _DB_ENABLED:
        try:
            db_msg_count = get_db_stats().get("total_messages", 0)  # type: ignore
        except Exception:
            pass

    rule_input  = "enabled" if InputRuleHarness else "disabled"
    rule_output = "enabled" if OutputRuleHarness else "disabled"

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
    category: Optional[str] = None,
    in_stock: Optional[bool] = None,
    min_rating: Optional[float] = None,
    max_price: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Truy xuất danh mục sách trong kho có hỗ trợ bộ lọc đa điều kiện và phân trang dữ liệu (Pagination).
    """
    # FIX: chặn limit/offset âm hoặc quá lớn (trước đây offset=-5 sẽ slice từ cuối,
    # limit=10**9 ép server serialize toàn bộ kho vào response).
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    books = _get_books()
    filtered = books

    def _safe_float(v: Any, default: float = 0.0) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _safe_int(v: Any, default: int = 0) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    if category:
        filtered = [b for b in filtered if category.lower() in str(b.get("category", "")).lower()]
    if in_stock is not None:
        filtered = [b for b in filtered if b.get("in_stock") == in_stock]
    if min_rating is not None:
        filtered = [b for b in filtered if _safe_float(b.get("rating", 0)) >= min_rating]
    if max_price is not None:
        filtered = [b for b in filtered if _safe_int(b.get("price", 0)) <= max_price]

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
    # FIX: db_manager dùng sqlite3 đồng bộ (blocking) — phải offload sang thread pool,
    # nếu không mỗi request /chat sẽ block toàn bộ Event Loop (mọi user khác đứng chờ).
    if _DB_ENABLED:
        if not session.get("db_session_id"):
            anon_user = await asyncio.to_thread(create_or_get_user, "anonymous", "Anonymous User")
            await asyncio.to_thread(ensure_session, session_id, anon_user["user_id"], "web-client")
            session["db_session_id"] = session_id
            session["db_user_id"] = anon_user["user_id"]

    db_session_id = session.get("db_session_id")
    # Nếu RAM chưa có lịch sử (sau khi server khởi động lại) nhưng DB có, khôi phục từ DB
    if _DB_ENABLED and db_session_id and len(session["history"]) <= 1:
        db_history = await asyncio.to_thread(get_session_history, db_session_id, 20)
        if db_history:
            session["history"] = db_history + session["history"]

    # FIX: dùng lịch sử client gửi kèm khi RAM/DB đều trống (client đa tab, mất RAM sau
    # restart mà chưa link DB). Trước đây field `session_history` bị bỏ qua hoàn toàn.
    # Chỉ nhận tối đa 10 mục hợp lệ để tránh client nhồi context khổng lồ vào prompt.
    merged_history = session["history"][-10:]
    if len(merged_history) <= 1 and req.session_history:
        client_hist = []
        for item in req.session_history[-10:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in ("user", "model") or not isinstance(content, str) or not content.strip():
                continue
            client_hist.append({"role": role, "content": content.strip()[:2000]})
        if client_hist:
            merged_history = (client_hist + merged_history)[-10:]

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

    # 4. Lưu vết hội thoại lâu dài vào SQLite (offload sang thread pool — xem chú thích ở bước 2)
    if _DB_ENABLED and db_session_id:
        db_user_id = session.get("db_user_id", "anonymous")
        book_ids   = [b.get("id", "") for b in result.get("books", [])]
        await asyncio.to_thread(save_message, db_session_id, db_user_id, "user", req.message,
                     query_type=result.get("query_type", ""), latency_ms=0)
        await asyncio.to_thread(save_message, db_session_id, db_user_id, "model", result["answer"],
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
            reason=b.get("reason", ""),
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
        db_sess = await asyncio.to_thread(db_get_session, db_sid)
        if not db_sess:
            raise HTTPException(status_code=403, detail="DB session không tồn tại hoặc đã hết hạn.")
        if db_uid and db_sess.get("user_id") != db_uid:
            raise HTTPException(status_code=403, detail="db_user_id không khớp với session. Truy cập bị từ chối.")

    session = await get_session(ram_id)
    session["db_session_id"] = db_sid
    session["db_user_id"]    = db_uid

    if _DB_ENABLED:
        history = await asyncio.to_thread(get_session_history, db_sid, 20)
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
    _sessions.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}



# ── DOC READER: Lazy import để không block startup nếu PyMuPDF vắng mặt ──────
process_upload: Any = None
list_session_files: Any = None
get_markdown_content: Any = None
get_pdf_path: Any = None
get_document_details: Any = None
MAX_FILES: int = 5
index_session_docs: Any = None
chat_with_doc: Any = None
summarize_doc: Any = None
generate_quiz: Any = None

try:
    from doc_pipeline import (
        process_upload, list_session_files, get_markdown_content,
        get_pdf_path, get_document_details, reuse_saved_document, MAX_FILES,
    )
    from doc_rag import index_session_docs, chat_with_doc, summarize_doc, generate_quiz
    _DOC_ENABLED = True
except ImportError as _doc_err:
    _DOC_ENABLED = False
    print(f"[WARN] Document RAG không nạp được: {_doc_err}")


# ── 9. DOC READER ENDPOINTS ─────────────────────────────────────────────────


@app.post("/api/doc/upload", tags=["Document RAG"])
async def doc_upload(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Upload tối đa 5 file PDF, tự động transcript sang Markdown và index vào ChromaDB phiên.
    Form fields: session_id (string), files (multipart, tối đa 5 file .pdf)
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng (thiếu thư viện pymupdf).")
    if not files:
        raise HTTPException(400, "Vui lòng chọn ít nhất 1 file PDF.")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Tối đa {MAX_FILES} file mỗi lần upload.")

    results = []
    md_contents, filenames = [], []

    for upload in files:
        fname = upload.filename or ""
        ext = fname.lower()
        if not (ext.endswith(".pdf") or ext.endswith(".docx")):
            results.append({"filename": fname, "error": "Chỉ chấp nhận file .pdf hoặc .docx"})
            continue
        pdf_bytes = await upload.read()
        # FIX: chặn file rỗng và file quá lớn trước khi ghi đĩa / embed.
        # Trước đây đọc toàn bộ bytes vào RAM không giới hạn → 1 file vài trăm MB
        # có thể làm OOM server dùng chung cho mọi user.
        if not pdf_bytes:
            results.append({"filename": fname, "error": "File rỗng, vui lòng chọn file khác."})
            continue
        if len(pdf_bytes) > 30 * 1024 * 1024:
            results.append({"filename": fname, "error": "File vượt quá 30MB, vui lòng chia nhỏ tài liệu."})
            continue
        try:
            info = await asyncio.to_thread(process_upload, pdf_bytes, fname, session_id)
            results.append(info)
            # Đọc nội dung Markdown vừa trích xuất để lập chỉ mục vector
            md_path = info["md_path"]
            md_text = Path(md_path).read_text(encoding="utf-8")
            md_contents.append(md_text)
            filenames.append(info["pdf_name"])
        except Exception as e:
            results.append({"filename": upload.filename, "error": str(e)})

    if md_contents:
        index_msg = await asyncio.to_thread(index_session_docs, session_id, md_contents, filenames)
    else:
        index_msg = "Không có tài liệu nào được index."

    # Tổng hợp thông báo nếu có tài liệu trùng lặp được hệ thống dọn dẹp
    dup_notices = []
    for r in results:
        if r.get("is_duplicate"):
            dup_notices.append(f"Tài liệu '{r.get('pdf_name')}' đã từng được tải lên trước đó. Hệ thống đã tự động dọn dẹp {r.get('replaced_count', 1)} bản lưu cũ trong database để tránh đầy bộ nhớ.")

    return {
        "uploaded": results,
        "index_status": index_msg,
        "duplicate_notice": " | ".join(dup_notices) if dup_notices else None
    }



@app.post("/api/doc/chat", tags=["Document RAG"])
async def doc_chat(payload: dict):
    """
    Hỏi đáp về tài liệu đã upload. Body JSON: {"session_id": "...", "query": "..."}
    Trả về câu trả lời kèm số trang trích dẫn [Xem trang X].
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    session_id = payload.get("session_id", "")
    query      = payload.get("query", "").strip()
    if not session_id or not query:
        raise HTTPException(400, "Cần có session_id và query.")
    answer = await asyncio.to_thread(chat_with_doc, session_id, query)
    return {"answer": answer}


@app.post("/api/doc/summarize", tags=["Document RAG"])
async def doc_summarize(payload: dict):
    """
    Tóm tắt tài liệu 3 cấp (Ý tưởng – Luận điểm – Kết luận).
    Body JSON: {"session_id": "...", "target": "chương 1"} (target có thể để rỗng)
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    session_id = payload.get("session_id", "")
    target     = payload.get("target", "")
    if not session_id:
        raise HTTPException(400, "Cần có session_id.")
    summary = await asyncio.to_thread(summarize_doc, session_id, target)
    return {"summary": summary}


@app.post("/api/doc/quiz", tags=["Document RAG"])
async def doc_quiz(payload: dict):
    """
    Tạo câu trắc nghiệm JSON (5, 10, 15, 20... câu).
    Body JSON: {"session_id": "...", "topic": "quang học", "count": 15}
    Returns JSON array: [{question, options, answer, page_ref, explanation}]
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    session_id = str(payload.get("session_id") or "").strip()
    topic      = str(payload.get("topic") or "").strip()
    try:
        # FIX: đồng nhất trần với doc_rag.generate_quiz (tối đa 30) — trước đây main cho 50
        # nhưng engine ép xuống 30, client tưởng tạo 50 câu nhưng thực tế chỉ nhận ~30.
        count = int(payload.get("count") or payload.get("num_questions") or 5)
        count = max(1, min(count, 30))
    except (ValueError, TypeError):
        count = 5
    if not session_id:
        raise HTTPException(400, "Cần có session_id.")
    quiz_json = await asyncio.to_thread(generate_quiz, session_id, topic, count)
    # Phân tích cú pháp JSON để trả về danh sách đối tượng có cấu trúc
    quiz_data = []
    try:
        quiz_data = json.loads(quiz_json)
        if isinstance(quiz_data, dict):
            quiz_data = quiz_data.get("quiz") or quiz_data.get("questions") or [quiz_data]
    except Exception:
        match = re.search(r"\[\s*\{.*\}\s*\]", str(quiz_json), re.DOTALL)
        if match:
            try:
                quiz_data = json.loads(match.group(0))
            except Exception:
                quiz_data = []
    if not isinstance(quiz_data, list):
        quiz_data = []
    # FIX: cắt đúng số câu client yêu cầu nếu model trả dư (không bao giờ bù câu bịa).
    quiz_data = quiz_data[:count]
    return {"quiz": quiz_data, "count": len(quiz_data)}


@app.get("/api/doc/files/{session_id}", tags=["Document RAG"])
async def doc_list_files(session_id: str):
    """Liệt kê các file PDF và Markdown đã upload trong phiên."""
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    return list_session_files(session_id)


@app.get("/api/doc/pdf/{session_id}/{pdf_filename}", tags=["Document RAG"])
async def doc_serve_pdf(session_id: str, pdf_filename: str):
    """Phục vụ file PDF hoặc DOCX gốc để hiển thị hoặc tải về trong trình duyệt."""
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    path = get_pdf_path(session_id, pdf_filename)
    if path is None:
        raise HTTPException(404, f"Không tìm thấy file: {pdf_filename}")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if str(path).lower().endswith(".docx") else "application/pdf"
    return FileResponse(str(path), media_type=media_type)


@app.get("/api/doc/content/{session_id}/{filename:path}", tags=["Document RAG"])
async def doc_get_content(session_id: str, filename: str):
    """
    Lấy nội dung chi tiết và các trang logic đã bóc tách của file DOCX hoặc PDF
    để phục vụ giao diện xem trước tài liệu trực quan (Document Reader View).
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    details = get_document_details(session_id, filename)
    if details is None:
        raise HTTPException(404, f"Không tìm thấy nội dung đã bóc tách của tài liệu: {filename}")
    return details


@app.get("/api/doc/library", tags=["Document RAG"])
async def doc_library():
    """
    Lấy danh sách toàn bộ file PDF đã upload lên hệ thống từ SQLite database.
    Cho phép người dùng xem lại và tái sử dụng tài liệu cũ mà không cần upload lại.
    """
    if not _DB_ENABLED:
        return {"documents": []}
    try:
        docs = await asyncio.to_thread(get_uploaded_docs, 50)
        return {"documents": docs}
    except Exception as e:
        return {"documents": [], "error": str(e)}


@app.post("/api/doc/library/reuse", tags=["Document RAG"])
async def doc_reuse(payload: dict):
    """
    Tái sử dụng một tài liệu PDF đã upload trước đó cho phiên làm việc hiện tại.
    Body JSON: {"session_id": "...", "doc_id": 1}
    """
    if not _DOC_ENABLED:
        raise HTTPException(503, "Tính năng Document RAG chưa sẵn sàng.")
    session_id = payload.get("session_id", "").strip()
    doc_id = payload.get("doc_id")
    if not session_id or doc_id is None:
        raise HTTPException(400, "Cần có session_id và doc_id.")

    try:
        doc = await asyncio.to_thread(get_uploaded_doc_by_id, int(doc_id))
        if not doc:
            raise HTTPException(404, "Không tìm thấy tài liệu trong cơ sở dữ liệu.")

        # [ponytail] Tái sử dụng trực tiếp file Markdown và file gốc đã lưu, zero duplicate
        info = await asyncio.to_thread(reuse_saved_document, doc, session_id)

        md_text = info.get("md_content") or Path(info["md_path"]).read_text(encoding="utf-8")
        index_msg = await asyncio.to_thread(index_session_docs, session_id, [md_text], [info["pdf_name"]])

        return {
            "status": "ok",
            "document": info,
            "index_status": index_msg,
            "message": f"Đã nạp thành công tài liệu: {doc['filename']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lỗi tái sử dụng tài liệu: {e}")


@app.delete("/api/doc/library/{doc_id}", tags=["Document RAG"])
async def doc_delete_library(doc_id: int):
    """
    Xóa một tài liệu PDF khỏi kho lưu trữ SQLite database và dọn dẹp file vật lý.
    """
    if not _DB_ENABLED:
        raise HTTPException(503, "Cơ sở dữ liệu chưa sẵn sàng.")
    success = await asyncio.to_thread(delete_uploaded_doc, int(doc_id))
    if not success:
        raise HTTPException(404, "Không tìm thấy tài liệu trong cơ sở dữ liệu để xóa.")
    return {"status": "ok", "message": f"Đã xóa tài liệu #{doc_id} khỏi cơ sở dữ liệu thành công."}


@app.post("/api/doc/library/delete", tags=["Document RAG"])
async def doc_delete_library_post(payload: dict):
    """
    Endpoint POST dự phòng để xóa tài liệu PDF khi client không hỗ trợ DELETE method.
    Body JSON: {"doc_id": 1}
    """
    if not _DB_ENABLED:
        raise HTTPException(503, "Cơ sở dữ liệu chưa sẵn sàng.")
    doc_id = payload.get("doc_id")
    if doc_id is None:
        raise HTTPException(400, "Thiếu tham số doc_id.")
    success = await asyncio.to_thread(delete_uploaded_doc, int(doc_id))
    if not success:
        raise HTTPException(404, "Không tìm thấy tài liệu trong cơ sở dữ liệu để xóa.")
    return {"status": "ok", "message": f"Đã xóa tài liệu #{doc_id} khỏi cơ sở dữ liệu thành công."}



# ── OTC GATEKEEPER: Tra cứu an toàn dược phẩm lâm sàng ───────────────────────
check_drug_safety: Any = None
_OTC_DATA: List[Dict[str, Any]] = []
consult_otc_medicine: Any = None

try:
    from med_gatekeeper import check_drug_safety
    from otc_gatekeeper import _OTC_DATA, consult_otc_medicine
    _MED_ENABLED = True
except Exception as _med_err:
    _MED_ENABLED = False
    print(f"[WARN] OTC Gatekeeper không nạp được: {_med_err}")


@app.post("/api/med/check", tags=["OTC Gatekeeper"])
async def med_check(payload: dict):
    """
    POC tra cứu an toàn dược học OTC.
    Body: {"drug": "Hapacol 650", "conditions": ["suy gan"], "age": 25, "gender": "male"}.
    """
    if not _MED_ENABLED:
        raise HTTPException(503, "Phân hệ OTC Gatekeeper chưa sẵn sàng.")
    drug = (payload.get("drug") or "").strip()
    conditions = payload.get("conditions") or []
    age = payload.get("age")
    gender = payload.get("gender")
    if not drug:
        raise HTTPException(400, "Cần có tên thuốc (drug).")
    return await asyncio.to_thread(check_drug_safety, drug, conditions, age, gender)


@app.get("/api/med/all", tags=["OTC Gatekeeper"])
async def med_get_all(limit: int = 50, offset: int = 0):
    """Lấy danh sách tất cả các loại thuốc OTC trong kho dữ liệu tham chiếu Dược Thư."""
    if not _MED_ENABLED:
        raise HTTPException(503, "Phân hệ OTC Gatekeeper chưa sẵn sàng.")
    # FIX: phân trang — trước đây trả toàn bộ KB mỗi lần gọi, phí băng thông khi KB lớn dần.
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return {"medicines": _OTC_DATA[offset:offset + limit], "total": len(_OTC_DATA),
            "limit": limit, "offset": offset}


@app.post("/api/med/consult", tags=["OTC Gatekeeper"])
async def med_consult(payload: dict):
    """
    Tư vấn Dược học lâm sàng OTC thông minh:
    Body: {"query": "sốt đau đầu", "conditions": ["viêm loét dạ dày"], "age": 25, "gender": "female"}.
    """
    if not _MED_ENABLED:
        raise HTTPException(503, "Phân hệ OTC Gatekeeper chưa sẵn sàng.")
    query = (payload.get("query") or "").strip()
    conditions = payload.get("conditions") or []
    age = payload.get("age")
    gender = payload.get("gender")
    if not query:
        raise HTTPException(400, "Cần có nội dung câu hỏi hoặc triệu chứng (query).")
    return await asyncio.to_thread(consult_otc_medicine, query, conditions, age, gender)



# ── 10. KHỞI ĐỘNG MÁY CHỦ UVICORN ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
