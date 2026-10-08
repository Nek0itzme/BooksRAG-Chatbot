-- schema.sql: Lược đồ cơ sở dữ liệu SQLite cho phiên làm việc và người dùng
-- Đề tài: Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin
--
-- Cấu trúc các bảng:
-- 1. users: Quản lý thông tin tài khoản người dùng.
-- 2. sessions: Quản lý các phiên tương tác.
-- 3. session_history: Lưu trữ lịch sử tin nhắn hỏi đáp.
-- 4. saved_books: Lưu danh sách sách yêu thích / giỏ hàng.
-- 5. Indexes: Tối ưu tốc độ truy vấn theo khóa ngoại và mốc thời gian.


-- 1. BẢNG NGƯỜI DÙNG (USERS)
CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,              -- Mã định danh duy nhất của người dùng (UUID v4)
    username     TEXT UNIQUE NOT NULL,          -- Tên đăng nhập tài khoản
    display_name TEXT DEFAULT '',               -- Tên hiển thị người dùng
    avatar_seed  TEXT DEFAULT '',               -- Seed ký tự sinh avatar đại diện
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP, -- Thời điểm khởi tạo tài khoản
    last_seen    DATETIME DEFAULT CURRENT_TIMESTAMP  -- Thời điểm truy cập gần nhất
);

-- 2. BẢNG PHIÊN LÀM VIỆC (SESSIONS)
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,              -- Mã định danh duy nhất của phiên (UUID v4)
    user_id      TEXT NOT NULL,                 -- Khóa ngoại liên kết tới bảng users
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP, -- Thời điểm mở phiên
    last_active  DATETIME DEFAULT CURRENT_TIMESTAMP, -- Mốc thời gian tương tác gần nhất
    is_active    INTEGER DEFAULT 1,             -- Trạng thái phiên: 1 (đang hoạt động), 0 (đã đăng xuất/hết hạn)
    device_info  TEXT DEFAULT '',               -- Thông tin thiết bị / trình duyệt
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. BẢNG LỊCH SỬ HỘI THOẠI (SESSION_HISTORY)
CREATE TABLE IF NOT EXISTS session_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,                 -- Khóa ngoại liên kết tới bảng sessions
    user_id     TEXT NOT NULL,                 -- Khóa ngoại liên kết tới bảng users
    role        TEXT NOT NULL CHECK(role IN ('user', 'model')), -- Vai trò: 'user' hoặc 'model'
    content     TEXT NOT NULL,                 -- Nội dung câu hỏi hoặc câu trả lời
    query_type  TEXT DEFAULT '',               -- Phân loại ý định: vague_plot, by_author, by_budget...
    book_ids    TEXT DEFAULT '',               -- Danh sách mã sách được gợi ý (chuỗi mảng JSON)
    latency_ms  INTEGER DEFAULT 0,              -- Thời gian xử lý RAG (mili-giây) phục vụ thống kê hiệu năng
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP, -- Thời điểm gửi tin
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- 4. BẢNG SÁCH YÊU THÍCH / ĐÃ LƯU (SAVED_BOOKS)
CREATE TABLE IF NOT EXISTS saved_books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,                 -- Khóa ngoại liên kết tới bảng users
    book_id     TEXT NOT NULL,                 -- Mã định danh sách trong kho (vd: BK0001)
    book_title  TEXT NOT NULL,                 -- Tựa đề sách
    book_author TEXT DEFAULT '',               -- Tên tác giả
    price       INTEGER DEFAULT 0,             -- Giá niêm yết (VNĐ)
    rating      REAL DEFAULT 0,                -- Đánh giá sao
    saved_at    DATETIME DEFAULT CURRENT_TIMESTAMP, -- Thời điểm lưu sách
    UNIQUE(user_id, book_id),                  -- Đảm bảo mỗi người dùng không lưu trùng 1 cuốn sách nhiều lần
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ── 5. CÁC CHỈ MỤC TỐI ƯU TRUY VẤN (INDEXES FOR HIGH-THROUGHPUT RETRIEVAL) ─────
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_history_session ON session_history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_user ON session_history(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_books(user_id);
