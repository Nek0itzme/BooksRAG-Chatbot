# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #06 — Multi-key rotation + Retry config
config.py — Hằng số & siêu tham số toàn hệ thống
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Đường dẫn thư mục gốc
BASE_DIR = Path(__file__).parent.parent
load_dotenv(Path(__file__).parent / ".env")

# 1. Đường dẫn dữ liệu và ChromaDB
DATABASE_DIR      = BASE_DIR / "database"
SAMPLE_JSON       = DATABASE_DIR / "sample.json"       # Kho dữ liệu 697 cuốn sách
CHROMA_PERSIST    = str(DATABASE_DIR / "chroma_db")    # Nơi lưu ChromaDB
CHROMA_COLLECTION = "books"                            # Tên collection

# 2. Cấu hình Gemini API và danh sách Key dự phòng
GEMINI_API_KEYS: list[str] = []
for _suffix in ["", "_2", "_3", "_4", "_5"]:
    _k = os.getenv(f"GEMINI_API_KEY{_suffix}", "").strip()
    if _k:
        GEMINI_API_KEYS.append(_k)

GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
GEMINI_FLASH    = "gemini-flash-lite-latest"
GEMINI_FALLBACK = "gemini-3.5-flash-lite"

# 3. Cơ chế tự động thử lại khi gặp lỗi mạng
RETRY_MAX        = 3
RETRY_BASE_DELAY = 1.0

# 4. Mô hình nhúng vector (chạy cục bộ)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# 5. Trọng số chấm điểm kết hợp (Hybrid Scoring)
# Score_Total = ALPHA * Score_Semantic + (1 - ALPHA) * Score_Ranking
ALPHA     = 0.75   # 75% độ khớp ngữ nghĩa, 25% chất lượng sách

# Trọng số thành phần chất lượng: Rating (50%), Doanh số (30%), Chất lượng review (20%)
W_RATING  = 0.50
W_SALES   = 0.30
W_QUALITY = 0.20

# 6. Ngưỡng lọc dữ liệu
MIN_RATING     = 2.0          # Bỏ qua sách dưới 2 sao
DEFAULT_BUDGET = 10_000_000   # Mức ngân sách mặc định khi không nhập

# 7. Giới hạn số lượng sách trả về
TOP_K            = 5    # Số sách hiển thị cho người dùng
CHROMA_N_RESULTS = 20   # Số sách lấy từ ChromaDB để lọc

# 8. Gợi ý theo tác giả sau khi mua
AUTHOR_REC_COUNT = 3
AUTHOR_EXACT_MATCH_SCORE = 0.95

# 9. Cấu hình máy chủ FastAPI
HOST = "0.0.0.0"
PORT = 8000
