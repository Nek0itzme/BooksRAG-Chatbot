# -*- coding: utf-8 -*-
"""
main.py — FastAPI application
Hệ Thống Tư Vấn Bán Sách RAG
Chạy server: uvicorn main:app --reload --port 8000
[AI-Assisted Code] Prompt #08 — Tích hợp Web Database (SQLite session persistence)
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

import uuid
import time
import json
import asyncio

from pathlib import Path

# ── Thêm Web Database vào Python path ────────────────────────────────────────
_WEB_DB_DIR = Path(__file__).parent.parent / "Web Database"
sys.path.insert(0, str(_WEB_DB_DIR))

# ── Đường dẫn Frontend (tách biệt với Back End) ───────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "Front End"
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import HOST, PORT, SAMPLE_JSON
from models import ChatRequest, ChatResponse, BuyRequest, BookResult, HealthResponse
from rag_engine import run_rag, is_chroma_ready, _get_books, get_author_recommendations

# ── Web Database imports ──────────────────────────────────────────────────────
try:
    from db_manager import (
        create_or_get_user, create_session as db_create_session,
        ensure_session,
        get_session as db_get_session, save_message, get_session_history,
        save_book, get_saved_books,
    )
    from session_routes import router as auth_router, books_router, analytics_router
    _DB_ENABLED = True
except Exception as _db_err:
    _DB_ENABLED = False
    print(f"[WARN] Web Database not loaded: {_db_err}")

# ── Khởi tạo app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="📚 Hệ Thống Tư Vấn Sách RAG",
    description=(
        "Chatbot tư vấn sách tích hợp RAG — Chống hallucination & Gợi ý cá nhân hóa.\n\n"
        "**Nguồn dữ liệu:** Tiki Books API\n"
        "**LLM:** Google Gemini 2.5 Flash\n"
        "**Vector DB:** ChromaDB\n"
        "**Kế hoạch nghiên cứu:** plan.md §3"
    ),
    version="1.0.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",
)

# ── CORS — cho phép Frontend HTML gọi được ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Development: allow all; Production: set domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Web Database Routers ────────────────────────────────────────────────
if _DB_ENABLED:
    app.include_router(auth_router)
    app.include_router(books_router)
    app.include_router(analytics_router)
    print("[OK] Web Database routers mounted: /auth, /books, /analytics")

# ── In-session storage (RAM, per-session) ─────────────────────────────────────
# Key: session_id (str)  →  Value: {"history": [...], "purchased": [...]}
_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"history": [], "purchased": []}
    return _sessions[session_id]


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Mở trực tiếp giao diện Web tại http://localhost:8000/"""
    html_path = FRONTEND_DIR / "index.html"
    return FileResponse(html_path)


@app.get("/avatar.png", include_in_schema=False)
async def serve_avatar():
    """Phục vụ avatar người dùng"""
    avatar_path = Path(__file__).parent / "avatar.png"
    if avatar_path.exists():
        return FileResponse(avatar_path)
    raise HTTPException(status_code=404, detail="Avatar not found")



@app.get("/avatar_data.js", include_in_schema=False)
async def serve_avatar_data_js():
    """Phục vụ file JS chứa dữ liệu Base64 avatar"""
    js_path = FRONTEND_DIR / "avatar_data.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="avatar_data.js not found")


@app.get("/user_black.png", include_in_schema=False)
@app.get("/assets/user_black.png", include_in_schema=False)
async def serve_user_black():
    """Phục vụ icon avatar cho Black Mode"""
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
    """Phục vụ icon avatar cho White Mode"""
    p = Path(__file__).parent / "user_white.png"
    if p.exists():
        return FileResponse(p)
    p_assets = Path(__file__).parent / "assets" / "user_white.png"
    if p_assets.exists():
        return FileResponse(p_assets)
    raise HTTPException(status_code=404, detail="user_white.png not found")


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Kiểm tra trạng thái hệ thống — ChromaDB, số lượng sách."""
    books = _get_books()
    return HealthResponse(
        status="ok",
        total_books=len(books),
        chroma_ready=is_chroma_ready(),
    )


@app.get("/health/detailed", tags=["System"])
async def health_check_detailed():
    """
    Kiểm tra chi tiết trạng thái tất cả module của hệ thống RAG:
    ChromaDB, HyPE Filter, SQLite DB, Rule Harness, Gemini model.
    """
    from config import GEMINI_FLASH, GEMINI_FALLBACK, EMBEDDING_MODEL, ALPHA, TOP_K
    from rag_engine import _HYPE_ENABLED, is_chroma_ready, _get_books

    books = _get_books()
    chroma_ok = is_chroma_ready()

    # Kiểm tra HyPE
    hype_status = "enabled" if _HYPE_ENABLED else "disabled (torch/geoopt missing)"

    # Kiểm tra SQLite DB
    db_status = "enabled" if _DB_ENABLED else "disabled"
    db_book_count = 0
    if _DB_ENABLED:
        try:
            from db_manager import get_db_stats
            db_book_count = get_db_stats().get("total_messages", 0)
        except Exception:
            pass

    # Kiểm tra Rule Harness
    from rag_engine import InputRuleHarness as _IRH, OutputRuleHarness as _ORH
    rule_input  = "enabled" if _IRH else "disabled"
    rule_output = "enabled" if _ORH else "disabled"

    return {
        "status": "ok",
        "modules": {
            "chroma_vector_db": {
                "status": "ok" if chroma_ok else "error",
                "total_books_indexed": books.__len__() if chroma_ok else 0,
                "total_books_json": len(books),
            },
            "hype_filter": {
                "status": hype_status,
                "description": "Hyperbolic Poincaré Ball Entailment Cone Filter",
            },
            "sqlite_session_db": {
                "status": db_status,
                "total_messages_logged": db_book_count,
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
):
    """
    Xem danh sách sách trong kho với bộ lọc tuỳ chọn.
    Dùng để kiểm tra dữ liệu và test Hard Filter.
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

    return {
        "total": len(filtered),
        "books": filtered[:limit],
    }


@app.post("/chat", response_model=ChatResponse, tags=["RAG"])
async def chat(req: ChatRequest):
    """
    **Endpoint chính** — Nhận câu hỏi, thực hiện RAG pipeline 5 bước và trả gợi ý sách.

    Các loại câu hỏi được hỗ trợ:
    - Nhớ mang máng cốt truyện
    - Tìm theo tác giả / thể loại / ngân sách / tâm trạng / độ tuổi
    - Câu bẫy hallucination → từ chối thay vì bịa
    """
    # Quản lý session (RAM in-session)
    session_id = req.session_id or str(uuid.uuid4())
    session    = get_session(session_id)

    # Ghi nhận câu hỏi vào lịch sử RAM
    session["history"].append({"role": "user", "content": req.message})

    # Đảm bảo session được đồng bộ và lưu vào SQLite Database
    if _DB_ENABLED:
        if not session.get("db_session_id"):
            anon_user = create_or_get_user("anonymous", "Anonymous User")
            ensure_session(session_id, anon_user["user_id"], "web-client")
            session["db_session_id"] = session_id
            session["db_user_id"] = anon_user["user_id"]

    # Nếu DB enabled: load lịch sử từ SQLite để có context xuyên phiên
    db_session_id = session.get("db_session_id")
    if _DB_ENABLED and db_session_id:
        db_history = get_session_history(db_session_id, limit=10)
        # Merge: ưu tiên DB history cho context, RAM cho session hiện tại
        merged_history = db_history + session["history"][-4:]
    else:
        merged_history = session["history"]

    t0 = time.time()
    # Chạy RAG pipeline trong thread pool (tránh block event loop khi chịu tải đồng thời)
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

    # Lưu vào SQLite nếu DB enabled + có db_session_id
    if _DB_ENABLED and db_session_id:
        db_user_id = session.get("db_user_id", "anonymous")
        book_ids   = [b.get("id", "") for b in result.get("books", [])]
        save_message(db_session_id, db_user_id, "user", req.message,
                     query_type=result.get("query_type", ""), latency_ms=0)
        save_message(db_session_id, db_user_id, "model", result["answer"],
                     query_type=result.get("query_type", ""),
                     book_ids=book_ids, latency_ms=latency)

    # Convert sách sang BookResult Pydantic models
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
    Kết nối RAM session với DB session sau khi user đăng nhập.
    Frontend gọi ngay sau /auth/login để gắn db_session_id vào RAM session.

    Body: { "session_id": "...", "db_session_id": "...", "db_user_id": "..." }
    """
    ram_id = body.get("session_id", "")
    db_sid = body.get("db_session_id", "")
    db_uid = body.get("db_user_id", "")

    if not ram_id or not db_sid:
        raise HTTPException(status_code=400, detail="session_id và db_session_id là bắt buộc")

    session = get_session(ram_id)
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
    Ghi nhận sách người dùng đã mua trong phiên.
    Kết quả: trả về gợi ý 2-3 tác phẩm cùng tác giả.
    """
    session = get_session(req.session_id)

    # Tránh ghi nhận trùng
    if req.book_id not in session["purchased"]:
        session["purchased"].append(req.book_id)

    # Lấy gợi ý cùng tác giả
    exclude = session["purchased"]
    recs = get_author_recommendations(req.book_id, exclude_ids=exclude)

    # Tìm sách đã mua để trả thông tin
    all_books = _get_books()
    purchased_book = next((b for b in all_books if b["id"] == req.book_id), None)

    return {
        "status": "recorded",
        "purchased_book": purchased_book,
        "author_recommendations": recs,
        "message": (
            f"✅ Đã ghi nhận bạn chọn mua '{purchased_book['title'] if purchased_book else req.book_id}'. "
            f"Gợi ý thêm {len(recs)} tác phẩm cùng tác giả!"
            if recs else
            f"✅ Đã ghi nhận. Không tìm thêm được tác phẩm cùng tác giả trong kho."
        ),
    }


@app.post("/remove_from_cart", tags=["In-session"])
async def remove_from_cart(req: BuyRequest):
    """Xóa sách khỏi giỏ hàng trong phiên."""
    session = get_session(req.session_id)
    if req.book_id in session["purchased"]:
        session["purchased"].remove(req.book_id)
    return {"status": "removed", "book_id": req.book_id, "remaining_count": len(session["purchased"])}


@app.delete("/session/{session_id}", tags=["System"])
async def clear_session(session_id: str):
    """Xóa lịch sử phiên chat (khi người dùng thoát ra)."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "cleared", "session_id": session_id}


# ── Khởi động server ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
