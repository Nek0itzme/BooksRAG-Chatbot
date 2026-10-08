# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
db_manager.py — Quản trị cơ sở dữ liệu SQLite cho phiên làm việc và người dùng
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này cung cấp:
1. Quản lý kết nối SQLite an toàn đa luồng bằng Thread-Local Storage.
2. Tối ưu hiệu năng đọc/ghi đồng thời với chế độ WAL (Write-Ahead Logging).
3. Quản lý tài khoản người dùng, phiên tương tác và lịch sử hội thoại.
4. Quản lý danh sách sách yêu thích / giỏ hàng.
"""

import json
import sqlite3
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any


def _utc_now() -> datetime:
    """
    Trả về mốc thời gian hiện tại chuẩn UTC (naive datetime)
    nhằm đảm bảo tính tương thích đồng bộ với chuỗi ISO 8601 của SQLite và Python 3.12+.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Tự động cấu hình mã hóa UTF-8 cho console Windows
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

# ── ĐƯỜNG DẪN CƠ SỞ DỮ LIỆU & SCHEMA ──────────────────────────────────────────
_THIS_DIR  = Path(__file__).parent
DB_PATH    = _THIS_DIR / "sessions.db"
SCHEMA_SQL = _THIS_DIR / "schema.sql"

# Hạn tồn tại của phiên (TTL): 7 ngày không hoạt động -> Tự động hết hạn
SESSION_TTL_DAYS = 7


# ─────────────────────────────────────────────────────────────────────────────
# QUẢN LÝ BỂ KẾT NỐI THEO LUỒNG (THREAD-LOCAL CONNECTION POOL)
# ─────────────────────────────────────────────────────────────────────────────

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """
    Lấy hoặc khởi tạo kết nối SQLite riêng biệt cho từng luồng (Thread-safe Connection).
    Tự động kích hoạt cơ chế WAL (Write-Ahead Logging) và Khóa ngoại (Foreign Keys).
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row              # Cho phép truy cập cột theo tên dictionary
        _local.conn.execute("PRAGMA foreign_keys = ON")     # Bật ràng buộc toàn vẹn khóa ngoại
        _local.conn.execute("PRAGMA journal_mode = WAL")    # Bật chế độ Write-Ahead Logging tăng tốc độ ghi
    return _local.conn


def init_db() -> None:
    """Khởi tạo cấu trúc các bảng và chỉ mục trong cơ sở dữ liệu nếu chưa tồn tại."""
    schema = SCHEMA_SQL.read_text(encoding="utf-8")
    with _get_conn() as conn:
        conn.executescript(schema)
    print(f"[OK] Cơ sở dữ liệu SQLite đã sẵn sàng tại: {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. QUẢN LÝ NGƯỜI DÙNG (USER MANAGEMENT)
# ─────────────────────────────────────────────────────────────────────────────

def create_or_get_user(username: str, display_name: str = "") -> dict:
    """
    Tìm kiếm người dùng đã có hoặc tự động tạo tài khoản mới nếu chưa tồn tại.
    
    Returns:
        dict: {user_id, username, display_name, avatar_seed, created_at, last_seen}
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if row:
            # Cập nhật thời điểm truy cập gần nhất (last_seen)
            conn.execute(
                "UPDATE users SET last_seen = ? WHERE username = ?",
                (_utc_now().isoformat(), username)
            )
            return dict(row)

        # Tạo tài khoản người dùng mới với UUID v4
        user_id = str(uuid.uuid4())
        avatar_seed = username[:3].upper() if username else "USR"
        now_iso = _utc_now().isoformat()
        conn.execute(
            "INSERT INTO users (user_id, username, display_name, avatar_seed, created_at, last_seen) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, username, display_name or username, avatar_seed, now_iso, now_iso)
        )
        return {
            "user_id": user_id,
            "username": username,
            "display_name": display_name or username,
            "avatar_seed": avatar_seed,
            "created_at": now_iso,
            "last_seen": now_iso,
        }


def get_user(user_id: str) -> Optional[dict]:
    """Truy xuất thông tin người dùng theo mã định danh user_id."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# 2. QUẢN LÝ PHIÊN LÀM VIỆC (SESSION LIFECYCLE MANAGEMENT)
# ─────────────────────────────────────────────────────────────────────────────

def create_session(user_id: str, device_info: str = "") -> dict:
    """Tạo một phiên làm việc mới (session_id) cho người dùng."""
    session_id = str(uuid.uuid4())
    now = _utc_now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, user_id, created_at, last_active, device_info)"
            " VALUES (?,?,?,?,?)",
            (session_id, user_id, now, now, device_info)
        )
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": now,
        "last_active": now,
    }


def ensure_session(session_id: str, user_id: str, device_info: str = "") -> dict:
    """Đảm bảo phiên tồn tại trong cơ sở dữ liệu; nếu chưa có thì tạo mới với ID cho trước."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            touch_session(session_id)
            return dict(row)
        now = _utc_now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, user_id, created_at, last_active, device_info)"
            " VALUES (?,?,?,?,?)",
            (session_id, user_id, now, now, device_info)
        )
        return {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "last_active": now,
        }


def get_session(session_id: str) -> Optional[dict]:
    """
    Truy xuất thông tin phiên làm việc.
    Tự động kiểm tra hạn TTL (7 ngày); nếu quá hạn sẽ đánh dấu vô hiệu hóa (is_active = 0) và trả về None.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND is_active = 1",
            (session_id,)
        ).fetchone()

    if not row:
        return None

    # Kiểm tra hạn thời gian sống (TTL Check)
    last_active = datetime.fromisoformat(row["last_active"])
    if _utc_now() - last_active > timedelta(days=SESSION_TTL_DAYS):
        invalidate_session(session_id)
        return None

    return dict(row)


def touch_session(session_id: str) -> None:
    """Cập nhật mốc thời gian hoạt động gần nhất (last_active) của phiên."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (_utc_now().isoformat(), session_id)
        )


def invalidate_session(session_id: str) -> None:
    """Vô hiệu hóa phiên làm việc khi người dùng đăng xuất hoặc phiên hết hạn."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
            (session_id,)
        )


def get_user_sessions(user_id: str, limit: int = 10) -> List[dict]:
    """Lấy danh sách các phiên hoạt động gần đây nhất của người dùng."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? AND is_active = 1"
            " ORDER BY last_active DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# 3. QUẢN LÝ LỊCH SỬ HỘI THOẠI (CHAT HISTORY & CONTEXT INJECTION)
# ─────────────────────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    query_type: str = "",
    book_ids: List[str] = None,
    latency_ms: int = 0,
) -> int:
    """
    Lưu một tin nhắn hội thoại vào bảng session_history.
    Tự động cập nhật thời điểm tương tác gần nhất của phiên.
    
    Returns:
        int: ID tự tăng của bản ghi mới.
    """
    book_ids_json = json.dumps(book_ids or [], ensure_ascii=False)
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO session_history"
            " (session_id, user_id, role, content, query_type, book_ids, latency_ms)"
            " VALUES (?,?,?,?,?,?,?)",
            (session_id, user_id, role, content, query_type, book_ids_json, latency_ms)
        )
        conn.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (_utc_now().isoformat(), session_id)
        )
    return cursor.lastrowid


def get_session_history(
    session_id: str,
    limit: int = 20,
) -> List[dict]:
    """
    Truy xuất lịch sử hội thoại của một phiên theo thứ tự thời gian tăng dần.
    Dùng để cung cấp ngữ cảnh hội thoại xuyên suốt cho RAG Pipeline.
    
    Returns:
        list[{role: 'user'|'model', content: str}]
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, query_type, timestamp FROM session_history"
            " WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_user_history_summary(user_id: str, days: int = 30) -> dict:
    """
    Phân tích và tổng hợp thói quen đọc sách của người dùng trong N ngày gần nhất.
    Thống kê tổng số lượt hỏi và các nhóm chủ đề được quan tâm nhiều nhất.
    """
    cutoff = (_utc_now() - timedelta(days=days)).isoformat()
    with _get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM session_history"
            " WHERE user_id = ? AND timestamp > ? AND role = 'user'",
            (user_id, cutoff)
        ).fetchone()["cnt"]

        types = conn.execute(
            "SELECT query_type, COUNT(*) as cnt FROM session_history"
            " WHERE user_id = ? AND timestamp > ? AND role = 'model' AND query_type != ''"
            " GROUP BY query_type ORDER BY cnt DESC LIMIT 5",
            (user_id, cutoff)
        ).fetchall()

    return {
        "total_queries": total,
        "top_query_types": [{"type": r["query_type"], "count": r["cnt"]} for r in types],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. QUẢN LÝ SÁCH YÊU THÍCH (SAVED BOOKS / WISHLIST)
# ─────────────────────────────────────────────────────────────────────────────

def save_book(user_id: str, book: dict) -> bool:
    """Lưu một cuốn sách vào danh sách yêu thích của người dùng."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO saved_books"
                " (user_id, book_id, book_title, book_author, price, rating)"
                " VALUES (?,?,?,?,?,?)",
                (
                    user_id,
                    book.get("id", ""),
                    book.get("title", ""),
                    book.get("author", ""),
                    int(book.get("price", 0)),
                    float(book.get("rating", 0.0)),
                )
            )
        return True
    except Exception:
        return False


def get_saved_books(user_id: str) -> List[dict]:
    """Lấy toàn bộ danh sách sách đã lưu của người dùng theo thời gian lưu mới nhất."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM saved_books WHERE user_id = ? ORDER BY saved_at DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def remove_saved_book(user_id: str, book_id: str) -> bool:
    """Xóa sách khỏi danh sách yêu thích."""
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM saved_books WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 5. THỐNG KÊ CƠ SỞ DỮ LIỆU PHỤC VỤ GIÁM SÁT (SYSTEM METRICS & STATS)
# ─────────────────────────────────────────────────────────────────────────────

def get_db_stats() -> dict:
    """
    Tổng hợp các chỉ số định lượng của cơ sở dữ liệu SQLite phục vụ endpoint /health/detailed.
    """
    with _get_conn() as conn:
        total_users = conn.execute(
            "SELECT COUNT(*) as cnt FROM users"
        ).fetchone()["cnt"]

        total_sessions = conn.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE is_active = 1"
        ).fetchone()["cnt"]

        total_messages = conn.execute(
            "SELECT COUNT(*) as cnt FROM session_history"
        ).fetchone()["cnt"]

        total_saved_books = conn.execute(
            "SELECT COUNT(*) as cnt FROM saved_books"
        ).fetchone()["cnt"]

        cutoff = (_utc_now() - timedelta(days=7)).isoformat()
        top_query = conn.execute(
            "SELECT query_type, COUNT(*) as cnt FROM session_history"
            " WHERE role = 'model' AND query_type != '' AND timestamp > ?"
            " GROUP BY query_type ORDER BY cnt DESC LIMIT 1",
            (cutoff,)
        ).fetchone()

    return {
        "total_users": total_users,
        "active_sessions": total_sessions,
        "total_messages": total_messages,
        "total_saved_books": total_saved_books,
        "top_query_type_7d": dict(top_query) if top_query else None,
        "db_path": str(DB_PATH),
    }


if __name__ == "__main__":
    init_db()
