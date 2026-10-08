# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
session_routes.py — FastAPI Router cho quản lý phiên người dùng và dữ liệu tương tác
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Các nhóm endpoint:
1. /auth: Đăng nhập, đăng xuất, lấy thông tin tài khoản và lịch sử phiên.
2. /books: Quản lý danh mục sách yêu thích / đã lưu.
3. /analytics: Thống kê thói quen đọc và phân bổ thể loại quan tâm.
"""

import sys
from pathlib import Path

# Thêm Web Database vào path hệ thống
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# Giới hạn tần suất gọi API đăng nhập theo chuẩn an ninh OWASP (Rate Limiting)
# slowapi là optional — cài bằng: pip install slowapi
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _HAS_SLOWAPI = True
    _auth_limiter = Limiter(key_func=get_remote_address)
except ImportError:
    _HAS_SLOWAPI = False
    _auth_limiter = None

from db_manager import (
    create_or_get_user,
    get_user,
    create_session,
    get_session,
    invalidate_session,
    get_session_history,
    get_user_sessions,
    save_message,
    get_user_history_summary,
    save_book,
    get_saved_books,
    remove_saved_book,
)

router = APIRouter(prefix="/auth", tags=["auth"])
books_router = APIRouter(prefix="/books", tags=["books"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Pydantic Models ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Schema tiếp nhận thông tin yêu cầu đăng nhập từ Client."""
    username: str = Field(..., description="Tên đăng nhập hoặc định danh người dùng")
    display_name: Optional[str] = Field("", description="Tên hiển thị trên giao diện người dùng")
    device_info: Optional[str] = Field("", description="Thông tin User-Agent hoặc thiết bị kết nối")


class LoginResponse(BaseModel):
    """Schema phản hồi kết quả phiên làm việc sau khi xác thực thành công."""
    session_id: str
    user_id: str
    username: str
    display_name: str
    avatar_seed: str
    is_new_user: bool


# Schema xác thực cấu trúc dữ liệu sách khi lưu vào mục yêu thích (Wishlist)
class SaveBookData(BaseModel):
    """Dữ liệu chi tiết của cuốn sách được người dùng chọn lưu."""
    id: str = Field("", description="Mã định danh sách chuẩn BKxxxx")
    title: str = Field("", description="Tựa đề cuốn sách")
    author: str = Field("", description="Tên tác giả")
    category: str = Field("", description="Thể loại hoặc danh mục xuất bản")
    publisher: str = Field("", description="Nhà xuất bản")
    price: int = Field(0, description="Giá bìa niêm yết (VNĐ)")
    rating: float = Field(0.0, description="Điểm đánh giá từ độc giả (1.0 - 5.0)")
    image_url: str = Field("", description="URL ảnh bìa sách (hiển thị trong danh sách yêu thích)")


class SaveBookRequest(BaseModel):
    """Schema bao đóng yêu cầu lưu sách yêu thích."""
    book: SaveBookData   # Dữ liệu sách cần lưu


# ── Dependency Helper: Kiểm Tra Phiên Làm Việc (Session Guard) ────────────────

async def _require_session(x_session_id: str = Header(default="")) -> dict:
    """
    FastAPI Dependency: Trích xuất và kiểm tra tính hợp lệ của phiên từ HTTP Header `X-Session-Id`.
    
    Quy trình kiểm duyệt:
    1. Kiểm tra sự tồn tại của header `X-Session-Id`. Nếu thiếu -> HTTP 401 Unauthorized.
    2. Truy vấn session trong SQLite Database (`get_session`).
    3. Kiểm tra TTL (Time-To-Live = 7 ngày) và cờ `is_active`. Nếu hết hạn -> HTTP 401.
    4. Trả về payload session hợp lệ cho các controller nghiệp vụ tiếp theo.
    """
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required (header: X-Session-Id)")
    session = get_session(x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please login again.")
    return session


# ── Phân Hệ 1: Xác Thực & Quản Lý Phiên (Auth Endpoints) ──────────────────────

def _rate_limit_login(func):
    """Áp dụng rate limit 5 req/phút/IP nếu slowapi đã cài, không thì passthrough."""
    if _HAS_SLOWAPI:
        return _auth_limiter.limit("5/minute")(func)
    return func


@router.post("/login", response_model=LoginResponse)
@_rate_limit_login
async def login(request: Request, req: LoginRequest):
    """
    Đăng nhập hoặc khởi tạo tài khoản trải nghiệm (Demo & Nghiên cứu).
    
    Quy trình vận hành:
    1. Tra cứu hoặc tạo mới người dùng trong bảng `users` (`create_or_get_user`).
    2. Cấp phát phiên làm việc mới (UUID v4) với thời hạn 7 ngày trong bảng `sessions`.
    3. Cập nhật mốc thời gian hoạt động gần nhất `last_seen`.
    4. Phản hồi Session ID để client lưu trữ trên LocalStorage.
    """
    user = create_or_get_user(req.username, req.display_name or "")
    is_new = "last_seen" not in user or user.get("created_at") == user.get("last_seen")

    session = create_session(user["user_id"], req.device_info or "")

    return LoginResponse(
        session_id=session["session_id"],
        user_id=user["user_id"],
        username=user["username"],
        display_name=user.get("display_name", req.username),
        avatar_seed=user.get("avatar_seed", req.username[:3].upper()),
        is_new_user=bool(is_new),
    )


@router.post("/logout")
async def logout(x_session_id: str = Header(default="")):
    """
    Hủy kích hoạt phiên làm việc hiện tại (Invalidate Session).
    Chuyển cờ `is_active = 0` trong bảng `sessions` để vô hiệu hóa ngay lập tức token.
    """
    if not x_session_id:
        raise HTTPException(status_code=400, detail="No session to logout from")
    invalidate_session(x_session_id)
    return {"message": "Đã đăng xuất thành công"}


@router.get("/me")
async def get_me(session: dict = Depends(_require_session)):
    """
    Lấy thông tin hồ sơ người dùng hiện tại dựa trên phiên làm việc được xác thực.
    """
    user = get_user(session["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name", ""),
        "avatar_seed": user.get("avatar_seed", ""),
        "created_at": user.get("created_at", ""),
        "last_seen": user.get("last_seen", ""),
    }


# ── Phân Hệ 2: Lịch Sử Tương Tác & Quản Lý Phiên (Session Endpoints) ───────────

@router.get("/session/history")
async def get_history(
    limit: int = 20,
    session: dict = Depends(_require_session),
):
    """
    Truy xuất lịch sử hội thoại gần nhất của phiên hiện tại (mặc định lấy 20 tin nhắn gần nhất).
    Dữ liệu này được đưa vào RAG Context Window để duy trì sự liền mạch ngữ cảnh hội thoại.
    """
    history = get_session_history(session["session_id"], limit=limit)
    return {"session_id": session["session_id"], "history": history, "count": len(history)}


@router.get("/session/list")
async def list_sessions(session: dict = Depends(_require_session)):
    """
    Truy xuất danh sách tất cả các phiên làm việc gần đây của người dùng (phục vụ sidebar chuyển đổi phiên).
    """
    sessions = get_user_sessions(session["user_id"])
    return {"sessions": sessions, "count": len(sessions)}


# ── Phân Hệ 3: Quản Lý Danh Mục Sách Yêu Thích (Books Endpoints) ──────────────

@books_router.post("/save")
async def save_book_endpoint(
    req: SaveBookRequest,
    session: dict = Depends(_require_session),
):
    """
    Lưu cuốn sách được quan tâm vào danh mục sách yêu thích (Wishlist) của người dùng.
    Hỗ trợ cơ chế UPSERT tránh trùng lặp dữ liệu trên SQLite.
    """
    success = save_book(session["user_id"], req.book.model_dump())
    if not success:
        raise HTTPException(status_code=400, detail="Không thể lưu sách")
    return {"message": f"Đã lưu sách '{req.book.title}'"}

@books_router.delete("/save/{book_id}")
async def remove_book_endpoint(
    book_id: str,
    session: dict = Depends(_require_session),
):
    """
    Xóa cuốn sách khỏi danh mục yêu thích của người dùng dựa trên Book ID.
    """
    remove_saved_book(session["user_id"], book_id)
    return {"message": "Đã xóa khỏi danh sách yêu thích"}


@books_router.get("/saved")
async def get_saved_books_endpoint(session: dict = Depends(_require_session)):
    """
    Lấy danh sách tất cả các cuốn sách đang được người dùng lưu trong danh mục yêu thích.
    """
    books = get_saved_books(session["user_id"])
    return {"books": books, "count": len(books)}


# ── Phân Hệ 4: Phân Tích Thống Kê Hành Vi (Analytics Endpoints) ────────────────

@analytics_router.get("/me")
async def my_analytics(
    days: int = 30,
    session: dict = Depends(_require_session),
):
    """
    Tổng hợp báo cáo hành vi đọc sách và tương tác của người dùng trong khoảng thời gian N ngày:
    - Tổng số câu hỏi đã đặt.
    - Thể loại sách được quan tâm nhiều nhất (Top Categories).
    - Tác giả được tìm kiếm nhiều nhất (Top Authors).
    - Phân bổ ngân sách trung bình.
    """
    summary = get_user_history_summary(session["user_id"], days=days)
    return summary

