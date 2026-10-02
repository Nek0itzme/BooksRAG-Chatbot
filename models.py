# -*- coding: utf-8 -*-
"""
models.py — Pydantic schemas cho FastAPI
Request / Response / Book data models
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Request ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="Câu hỏi / yêu cầu của người dùng")
    budget: Optional[int] = Field(None, description="Ngân sách tối đa (VND)", ge=0)
    session_id: Optional[str] = Field(None, description="ID phiên chat")
    session_history: list[dict] = Field(
        default_factory=list,
        description="Lịch sử chat [{role: user|model, content: str}]"
    )
    purchased_book_id: Optional[str] = Field(
        None,
        description="ID sách vừa mua (để gợi ý thêm tác giả)"
    )
    image_data: Optional[str] = Field(
        None,
        description="Ảnh bìa hoặc nội dung sách dạng Base64 data URL (hỗ trợ tìm kiếm sách bằng hình ảnh)"
    )


class BuyRequest(BaseModel):
    book_id: str = Field(..., description="ID sách người dùng chọn mua")
    session_id: str = Field(..., description="ID phiên chat hiện tại")


# ── Response ──────────────────────────────────────────────────────────────────

class BookResult(BaseModel):
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
    tags: list[str]
    description: str
    target_audience: str
    # Scoring (trả về để debug / frontend hiển thị)
    score_semantic: float = 0.0
    score_ranking: float = 0.0
    score_total: float = 0.0
    score_hype: float = 0.0   # HyPE Hyperbolic Entailment Score (Poincaré Ball)
    reason: str = ""   # lý do gợi ý (Gemini tổng hợp)



class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời tự nhiên bằng tiếng Việt")
    books: list[BookResult] = Field(default_factory=list)
    author_recs: list[BookResult] = Field(
        default_factory=list,
        description="Gợi ý thêm từ cùng tác giả (in-session)"
    )
    session_id: str = ""
    query_type: str = ""   # vague_plot | specific | by_author | by_mood | by_budget
    query_context: str = "" # Tiêu đề/chủ đề tìm kiếm mới cho thanh bên phải
    found: bool = True     # False = không có sách phù hợp trong kho
    vision_info: Optional[dict] = Field(None, description="Kết quả nhận diện ảnh bìa sách qua Gemini Vision")


class HealthResponse(BaseModel):
    status: str
    total_books: int
    chroma_ready: bool
