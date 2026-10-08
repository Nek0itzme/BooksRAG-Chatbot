# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
models.py — Định nghĩa cấu trúc dữ liệu Pydantic cho API (FastAPI Schemas)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này định nghĩa các mô hình dữ liệu (Pydantic schemas) cho Request và Response,
giúp kiểm tra tính hợp lệ của dữ liệu đầu vào và chuẩn hóa định dạng kết quả trả về.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# 1. YÊU CẦU ĐẦU VÀO TỪ CLIENT (REQUEST MODELS)
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """
    Lược đồ yêu cầu gửi câu hỏi tư vấn sách từ người dùng.
    Hỗ trợ đa phương thức: Văn bản tự nhiên, Ràng buộc ngân sách, Lịch sử ngữ cảnh và Ảnh bìa sách (Vision).
    """
    message: str = Field(
        ...,
        description="Câu hỏi hoặc mô tả nhu cầu tìm sách của người dùng",
        min_length=1,
        max_length=2000,
    )
    budget: Optional[int] = Field(
        None,
        description="Ngân sách tối đa mà người dùng mong muốn (VNĐ)",
        ge=0,
        le=100_000_000,   # Giới hạn tối đa 100 triệu VNĐ để ngăn tràn số
    )
    session_id: Optional[str] = Field(
        None, 
        description="Mã định danh phiên làm việc (UUID) để duy trì lịch sử hội thoại liên tục"
    )
    session_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách lịch sử tương tác trước đó trong phiên [{role: user|model, content: str}]"
    )
    purchased_book_id: Optional[str] = Field(
        None,
        description="Mã ID sách người dùng vừa chọn mua (nhằm kích hoạt gợi ý tác giả cùng phiên)"
    )
    image_data: Optional[str] = Field(
        None,
        description="Chuỗi Base64 Data URL của ảnh bìa sách (phục vụ tìm kiếm sách bằng thị giác máy tính / Vision OCR)",
        max_length=5_000_000,   # Giới hạn ~3.7MB sau giải mã, tối ưu cho ảnh bìa độ phân giải cao
    )


class BuyRequest(BaseModel):
    """
    Lược đồ yêu cầu khi người dùng chọn mua một cuốn sách trong giao diện.
    """
    book_id: str = Field(..., description="Mã định danh duy nhất của cuốn sách (vd: BK0001)")
    session_id: str = Field(..., description="Mã phiên làm việc hiện tại của người dùng")


# ─────────────────────────────────────────────────────────────────────────────
# 2. DỮ LIỆU ĐỐI TƯỢNG SÁCH & CHẤM ĐIỂM (BOOK DATA ENTITIES)
# ─────────────────────────────────────────────────────────────────────────────

class BookResult(BaseModel):
    """
    Thực thể thông tin chi tiết của một cuốn sách sau khi đã qua quy trình truy xuất và xếp hạng.
    Bao gồm thông tin mô tả và toàn bộ các điểm số thành phần minh bạch hóa thuật toán.
    """
    id: str
    title: str
    author: str
    category: str
    publisher: str
    price: int
    original_price: int
    rating: float
    sold_count: int
    in_stock: bool
    tags: List[str]
    description: str
    target_audience: str
    
    # ── Các trường điểm số định lượng của thuật toán Hybrid Scoring ──────────
    score_semantic: float = Field(0.0, description="Điểm tương đồng ngữ nghĩa (Dense Cosine + Sparse Lexical)")
    score_ranking: float = Field(0.0, description="Điểm xếp hạng thương mại (50% Sao + 30% Doanh số + 20% Review)")
    score_total: float = Field(0.0, description="Điểm tổng hợp cuối cùng: ALPHA * Semantic + (1-ALPHA) * Ranking")
    score_hype: float = Field(0.0, description="Điểm bao hàm Hyperbolic Poincaré Ball Entailment Cone (HyPE Score)")
    reason: str = Field("", description="Lý do ngắn gọn vì sao cuốn sách được hệ thống đề xuất")


# ─────────────────────────────────────────────────────────────────────────────
# 3. KẾT QUẢ TRẢ VỀ CHO CLIENT (RESPONSE MODELS)
# ─────────────────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """
    Lược đồ phản hồi hoàn chỉnh của RAG Chatbot gửi về cho giao diện Web.
    """
    answer: str = Field(..., description="Câu trả lời tư vấn tự nhiên bằng tiếng Việt có cấu trúc")
    books: List[BookResult] = Field(default_factory=list, description="Danh sách sách phù hợp nhất (Top-K)")
    author_recs: List[BookResult] = Field(
        default_factory=list,
        description="Danh sách gợi ý thêm các tác phẩm cùng tác giả (In-session Recommendation)"
    )
    session_id: str = Field("", description="Mã phiên làm việc hiện hành")
    query_type: str = Field("", description="Loại ý định câu hỏi: vague_plot | by_author | by_mood | by_budget | anti_halluc")
    query_context: str = Field("", description="Tóm tắt chủ đề tìm kiếm để hiển thị trên thanh bên kết quả")
    found: bool = Field(True, description="True nếu tìm thấy sách trong kho, False nếu kho chưa có hoặc bị chặn")
    vision_info: Optional[Dict[str, Any]] = Field(None, description="Kết quả phân tích nhận diện ảnh bìa qua Gemini Vision")


class HealthResponse(BaseModel):
    """
    Lược đồ phản hồi kiểm tra sức khỏe hệ thống (Health Check Endpoint).
    """
    status: str = Field(..., description="Trạng thái hệ thống: 'ok' hoặc 'degraded'")
    total_books: int = Field(..., description="Tổng số lượng sách có trong kho dữ liệu sample.json")
    chroma_ready: bool = Field(..., description="Trạng thái sẵn sàng của cơ sở dữ liệu vector ChromaDB")
