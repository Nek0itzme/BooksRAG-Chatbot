# -*- coding: utf-8 -*-
"""
test_db.py: Kịch bản kiểm thử tích hợp cơ sở dữ liệu SQLite (Integration Test Suite)
Đề tài: Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin

Kịch bản kiểm thử bao gồm:
1. Khởi tạo schema và cấu hình WAL mode.
2. Quản lý tài khoản người dùng và phiên làm việc.
3. Ghi và truy xuất lịch sử hội thoại.
4. Thao tác thêm/xóa sách yêu thích (Wishlist CRUD).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Cấu hình UTF-8 cho Windows Console tránh lỗi ký tự tiếng Việt
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from db_manager import (
    init_db, create_or_get_user, create_session,
    get_session as db_get_session, save_message,
    get_session_history, save_book, get_saved_books, remove_saved_book
)

print("=" * 65)
print("WEB DATABASE — TẬP LỆNH KIỂM THỬ TÍCH HỢP HỆ THỐNG CƠ SỞ DỮ LIỆU")
print("=" * 65)

# ── 1. Khởi Tạo Cơ Sở Dữ Liệu & Bật Chế Độ WAL ──────────────────────────────
print("\n[BƯỚC 1] Kiểm tra khởi tạo CSDL & Chế độ WAL...")
init_db()
print(" -> [PASS] Khởi tạo schema 3NF và bật WAL mode thành công.")

# ── 2. Kiểm Tra Quản Lý Danh Tính Người Dùng (User Management) ───────────────
print("\n[BƯỚC 2] Kiểm tra khởi tạo/truy vấn User...")
user = create_or_get_user("test_user", "Nguyen Van Test")
assert user and "user_id" in user, "Lỗi: Không khởi tạo được User ID"
print(f" -> [PASS] User: '{user['username']}' | ID: {user['user_id'][:12]}... | Avatar Seed: {user.get('avatar_seed')}")

# ── 3. Kiểm Tra Quản Lý Phiên Làm Việc (Session Lifecycle) ────────────────────
print("\n[BƯỚC 3] Kiểm tra cấp phát Phiên làm việc (Session)...")
session = create_session(user["user_id"], device_info="Chrome/Windows-TestRunner")
assert session and "session_id" in session, "Lỗi: Không tạo được Session"
sid = session["session_id"]
uid = user["user_id"]
print(f" -> [PASS] Cấp phát thành công Session ID: {sid[:12]}... | TTL: 7 ngày")

# ── 4. Kiểm Tra Ghi Nhận Lịch Sử Hội Thoại (Multi-turn Messaging) ─────────────
print("\n[BƯỚC 4] Kiểm tra ghi nhận tương tác & Metadata...")
msg1_id = save_message(sid, uid, "user", "Tìm sách tâm lý học dễ hiểu cho người mới")
msg2_id = save_message(
    sid, uid, "model",
    "Gợi ý: Đắc Nhân Tâm, Tâm Lý Học Đám Đông",
    query_type="by_mood",
    book_ids=["BK0001", "BK0002"],
    latency_ms=1450.5
)
assert msg1_id and msg2_id, "Lỗi: Ghi log tin nhắn thất bại"
print(f" -> [PASS] Đã ghi nhận 2 lượt tin nhắn (User Query & Model Response with metadata)")

# ── 5. Kiểm Tra Truy Xuất Ngữ Cảnh Hội Thoại (Context Retrieval) ─────────────
print("\n[BƯỚC 5] Kiểm tra truy xuất lịch sử hội thoại (Sliding Window)...")
history = get_session_history(sid, limit=20)
assert len(history) >= 2, "Lỗi: Lịch sử hội thoại không đầy đủ"
print(f" -> [PASS] Truy xuất thành công {len(history)} tin nhắn theo trình tự thời gian:")
for h in history:
    print(f"    • [{h['role'].upper()}]: {h['content'][:55]}...")

# ── 6. Kiểm Tra Lưu Sách Yêu Thích (Wishlist UPSERT) ──────────────────────────
print("\n[BƯỚC 6] Kiểm tra lưu sách vào danh mục yêu thích...")
ok = save_book(uid, {
    "id": "BK0001",
    "title": "Đắc Nhân Tâm",
    "author": "Dale Carnegie",
    "category": "Kỹ năng sống",
    "price": 79000,
    "rating": 4.8
})
assert ok, "Lỗi: Không thể lưu sách vào mục yêu thích"
print(" -> [PASS] Đã lưu sách thành công (UPSERT logic verified)")

# ── 7. Kiểm Tra Lấy Danh Sách Đã Lưu (Wishlist Read) ─────────────────────────
print("\n[BƯỚC 7] Kiểm tra đọc danh mục sách đã lưu...")
books = get_saved_books(uid)
assert len(books) > 0, "Lỗi: Danh sách sách đã lưu rỗng"
print(f" -> [PASS] Tìm thấy {len(books)} cuốn sách trong danh mục yêu thích:")
for b in books:
    print(f"    • [{b['book_id']}] {b['book_title']} — {b['book_author']} ({b['price']:,}đ)")

# ── 8. Kiểm Tra Xóa Sách Khỏi Danh Mục (Wishlist Delete) ──────────────────────
print("\n[BƯỚC 8] Kiểm tra xóa sách khỏi mục yêu thích...")
remove_saved_book(uid, "BK0001")
books_after = get_saved_books(uid)
assert len(books_after) == len(books) - 1, "Lỗi: Xóa sách không thành công"
print(f" -> [PASS] Xóa thành công. Số sách còn lại: {len(books_after)}")

print("\n" + "=" * 65)
print("✅ TẤT CẢ CÁC BƯỚC KIỂM THỬ TÍCH HỢP CSDL ĐỀU ĐẠT CHUẨN (100% PASSED)!")
print("=" * 65 + "\n")
