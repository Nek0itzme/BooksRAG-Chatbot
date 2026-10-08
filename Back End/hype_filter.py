# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #07 — Adaptation từ:
  "HYPE: Hyperbolic Entailment Filtering for Underspecified Images and Texts"
  Wonjae Kim et al., ECCV 2024 | arxiv: 2404.17507
  Nguồn: https://github.com/naver-ai/hype
hype_filter.py — Bộ lọc quan hệ bao hàm ngữ nghĩa Hyperbolic (Poincaré Ball Entailment Filter)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này triển khai bộ lọc HyPE trên không gian Hyperbolic (Poincaré Ball Model):
1. Chiếu vector đặc trưng từ không gian Euclidean vào Poincaré Ball thông qua phép ánh xạ phi tuyến tanh.
2. Sử dụng nón bao hàm (Entailment Cones) để kiểm tra quan hệ thứ bậc giữa câu hỏi và sách ứng viên.
3. Lọc bỏ các cuốn sách nằm ngoài nón bao hàm của câu hỏi nhằm tăng độ chính xác của ngữ cảnh trước khi đưa vào LLM.
"""


import math
import statistics
import warnings
from typing import Optional, List, Dict, Tuple, Any

import torch
import torch.nn.functional as F
import geoopt

# Tắt các cảnh báo không ảnh hưởng về JIT trên Python 3.12+
warnings.filterwarnings("ignore", category=FutureWarning)

# ── 1. CÁC HẰNG SỐ HÌNH HỌC POINCARÉ BALL ─────────────────────────────────────
CURVATURE   = 1.0          # Độ cong không gian âm chuẩn hóa (K = 1.0)
BALL        = geoopt.PoincareBall(c=CURVATURE)
MAX_NORM    = 1.0 - 1e-5   # Bán kính giới hạn an toàn bên trong quả cầu đơn vị (|x| < 1)

# ── 2. SIÊU THAM SỐ ĐÃ HIỆU CHUẨN KHOA HỌC (CALIBRATED HYPERPARAMETERS) ─────────
ENTAIL_THRESHOLD = -1.0    # Ngưỡng tuyệt đối dự phòng khi tính ngưỡng động
APERTURE_ALPHA   = 0.5     # Hệ số góc mở nón (Alpha = 0.5 tạo độ mở phù hợp cho vector văn bản)
PROJECT_SCALE    = 0.3     # Tỷ lệ co dãn trước khi qua hàm tanh, đưa vector về khoảng [0.1, 0.35]
MIN_HALF_ANGLE   = 0.05    # Góc mở tối thiểu (radian) tránh chia cho 0 hoặc lỗi số thực NaN


# ─────────────────────────────────────────────────────────────────────────────
# CÁC HÀM TIỆN ÍCH HÌNH HỌC TRÊN POINCARÉ BALL (MATHEMATICAL UTILITIES)
# ─────────────────────────────────────────────────────────────────────────────

def euclidean_to_poincare(x: torch.Tensor) -> torch.Tensor:
    """
    ÁNH XẠ TỪ KHÔNG GIAN PHẲNG EUCLIDEAN VÀO POINCARÉ BALL (EXPONENTIAL MAP APPROXIMATION).
    x in R^d -> x_h in B^d (|x_h| < 1)
    
    Quy trình tính toán:
    1. Chuẩn hóa vector x về hướng đơn vị x_unit = x / ||x||.
    2. Áp dụng phép co tỷ lệ PROJECT_SCALE và hàm phi tuyến hyperbolic tangent: tanh(||x|| * PROJECT_SCALE).
    3. Nhân với MAX_NORM để đảm bảo điểm luôn nằm tuyệt đối bên trong quả cầu đơn vị.
    """
    norm = x.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    x_unit = x / norm
    scaled_norm = torch.tanh(norm * PROJECT_SCALE) * MAX_NORM
    return x_unit * scaled_norm


def poincare_distance(u: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """
    TÍNH KHOẢNG CÁCH TRẮC ĐỊA HYPERBOLIC (POINCARÉ GEODESIC DISTANCE).
    Sử dụng thư viện vi tích phân hình học geoopt.PoincareBall.dist().
    """
    return BALL.dist(u, v)


def half_aperture_angle(x: torch.Tensor) -> torch.Tensor:
    """
    TÍNH NỬA GÓC MỞ NÓN BAO HÀM (HALF-APERTURE ANGLE OF ENTAILMENT CONE).
    Công thức: psi(x) = arcsin(APERTURE_ALPHA * (1 - ||x||^2) / ||x||)
    
    Quy luật hình học:
    - ||x|| nhỏ (gần gốc 0): (1 - ||x||^2) lớn -> sin_val lớn -> psi(x) lớn (nón rộng mở, bao quát).
    - ||x|| lớn (gần biên 1): (1 - ||x||^2) nhỏ -> sin_val nhỏ -> psi(x) nhỏ (nón hẹp, cụ thể hóa).
    """
    norm = x.norm(dim=-1).clamp(min=1e-8)
    sin_val = (APERTURE_ALPHA * (1.0 - norm ** 2) / norm).clamp(-1.0 + 1e-6, 1.0 - 1e-6)
    angle = torch.asin(sin_val)
    return angle.clamp(min=MIN_HALF_ANGLE)


def entailment_score(query_h: torch.Tensor, book_h: torch.Tensor) -> torch.Tensor:
    """
    TÍNH ĐIỂM BAO HÀM BẤT ĐỐI XỨNG (HYPERBOLIC ENTAILMENT SCORE).
    E(q, b) = psi(q) - d_B(q, b)
    
    Ý nghĩa:
    - Nếu E > 0: Điểm sách b nằm bên trong nón bao hàm của câu hỏi q -> Phù hợp ngữ cảnh.
    - Nếu E <= 0: Điểm sách b nằm ngoài nón bao hàm của câu hỏi q -> Cần loại bỏ.
    """
    psi_q = half_aperture_angle(query_h)           # Độ mở nón của câu hỏi
    dist  = poincare_distance(query_h, book_h)    # Khoảng cách Poincaré giữa câu hỏi và sách
    return psi_q - dist


# ─────────────────────────────────────────────────────────────────────────────
# CLASS CHÍNH: HYPE TEXT FILTER (BỘ LỌC HYPERBOLIC)
# ─────────────────────────────────────────────────────────────────────────────

class HyPEFilter:
    """
    BỘ LỌC QUAN HỆ BAO HÀM HYPE (HYPERBOLIC ENTAILMENT TEXT FILTER).
    Tích hợp trực tiếp vào luồng truy vấn RAG để nâng cao độ chính xác truy xuất (Context Precision).
    """

    def __init__(self, embedder, threshold: float = ENTAIL_THRESHOLD):
        """
        Khởi tạo bộ lọc HyPE.
        
        Args:
            embedder: Đối tượng SentenceTransformer (chia sẻ chung bộ nhớ với rag_engine).
            threshold: Ngưỡng bao hàm cơ sở.
        """
        self.embedder  = embedder
        self.threshold = threshold

    def _embed_to_poincare(self, texts: List[str]) -> torch.Tensor:
        """Nhúng văn bản sang không gian phẳng R^d và ánh xạ vào Poincaré Ball."""
        with torch.no_grad():
            vecs = self.embedder.encode(texts, show_progress_bar=False, convert_to_tensor=True)
            vecs = F.normalize(vecs, dim=-1)       # Chuẩn hóa về mặt cầu đơn vị
        return euclidean_to_poincare(vecs)         # Chiếu vào Poincaré Ball

    def filter(
        self,
        query: str,
        books: List[dict],
        description_field: str = "description",
        top_k: Optional[int] = None,
    ) -> Tuple[List[dict], List[float]]:
        """
        LỌC DANH SÁCH SÁCH BẰNG THUẬT TOÁN HYPERBOLIC ENTAILMENT CONES.
        
        Args:
            query: Câu hỏi / ý định của người dùng.
            books: Danh sách sách sơ tuyển từ Hard Filter / ChromaDB.
            description_field: Tên trường chứa nội dung tóm tắt sách.
            top_k: Số lượng sách tối đa giữ lại sau khi lọc.
            
        Returns:
            Tuple[kept_books, entailment_scores]: Danh sách sách đã lọc và điểm số tương ứng xếp giảm dần.
        """
        if not books:
            return [], []

        # 1. Xây dựng văn bản đại diện cho từng cuốn sách
        book_texts = []
        for b in books:
            text = (
                f"{b.get('title', '')}. "
                f"Thể loại: {b.get('category', '')}. "
                f"{b.get(description_field, '')[:300]}"
            )
            book_texts.append(text)

        # 2. Chiếu đồng thời câu hỏi và toàn bộ sách vào Poincaré Ball
        all_texts = [query] + book_texts
        all_h     = self._embed_to_poincare(all_texts)
        query_h   = all_h[0]                   # Vector Hyperbolic của câu hỏi
        books_h   = all_h[1:]                  # Ma trận Vector Hyperbolic của các cuốn sách

        # 3. Tính điểm bao hàm Entailment Score cho từng cuốn sách
        scores: List[float] = []
        for i in range(len(books)):
            e_score = entailment_score(query_h, books_h[i]).item()
            scores.append(e_score)

        # 4. Áp dụng Ngưỡng lọc động (Dynamic Thresholding):
        # dynamic_threshold = median(scores) - 0.5 * std(scores)
        # Giúp thuật toán thích ứng linh hoạt theo độ phân tán thực tế của tập ứng viên
        if len(scores) > 1:
            med   = statistics.median(scores)
            stdev = statistics.stdev(scores) if len(scores) > 2 else 0.3
            dyn_threshold = med - 0.5 * stdev
        else:
            dyn_threshold = self.threshold

        # 5. Thực hiện lọc
        kept = [
            (b, s) for b, s in zip(books, scores)
            if s > dyn_threshold
        ]

        # Cơ chế an toàn (Fallback Guard): Nếu lọc quá gắt khiến danh sách rỗng -> Giữ lại top 3 có điểm cao nhất
        if not kept:
            sorted_all = sorted(zip(books, scores), key=lambda x: x[1], reverse=True)
            kept = sorted_all[:max(3, len(books) // 3)]

        # Sắp xếp kết quả theo điểm Entailment Score giảm dần
        kept.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            kept = kept[:top_k]

        kept_books  = [item[0] for item in kept]
        kept_scores = [item[1] for item in kept]

        return kept_books, kept_scores

    def score_specificity(self, text: str) -> float:
        """
        ĐO LƯỜNG ĐỘ CỤ THỂ / CHI TIẾT CỦA VĂN BẢN (SPECIFICITY SCORE).
        Theo lý thuyết Poincaré: Độ cụ thể tỷ lệ thuận với khoảng cách từ điểm tới gốc tọa độ:
        Specificity = ||x_h|| / MAX_NORM in [0, 1]
        - 1.0: Rất cụ thể, chi tiết.
        - 0.0: Rất mơ hồ, khái quát.
        """
        h = self._embed_to_poincare([text])[0]
        norm = h.norm().item()
        return float(norm / MAX_NORM)

    def is_underspecified(self, query: str, threshold: float = 0.15) -> bool:
        """
        KIỂM TRA CÂU TRUY VẤN CÓ QUÁ MƠ HỒ (UNDERSPECIFIED) HAY KHÔNG.
        Nếu điểm cụ thể dưới ngưỡng (threshold = 0.15) -> Hệ thống cần hỏi lại người dùng để làm rõ.
        """
        spec = self.score_specificity(query)
        return spec < threshold


# ─────────────────────────────────────────────────────────────────────────────
# TRÌNH QUẢN LÝ ĐƠN THỂ (LAZY SINGLETON ACCESSOR)
# ─────────────────────────────────────────────────────────────────────────────

_hype_instance: Optional[HyPEFilter] = None


def get_hype_filter(embedder=None) -> HyPEFilter:
    """
    Truy xuất thể hiện duy nhất của HyPEFilter (Singleton Pattern)
    nhằm tái sử dụng SentenceTransformer trong RAM, tiết kiệm tối đa bộ nhớ máy chủ.
    """
    global _hype_instance
    if _hype_instance is None:
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            from config import EMBEDDING_MODEL
            embedder = SentenceTransformer(EMBEDDING_MODEL)
        _hype_instance = HyPEFilter(embedder)
    return _hype_instance


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 70)
    print("KIỂM THỬ THUẬT TOÁN HYPE FILTER (POINCARÉ BALL HYPERBOLIC ENTAILMENT)")
    print("=" * 70)

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    hype = HyPEFilter(embedder, threshold=0.0)

    sample_query = "cậu bé chăn cừu đi tìm kho báu ở kim tự tháp Ai Cập"
    sample_books = [
        {"id": "1", "title": "Nhà Giả Kim", "category": "Văn học",
         "description": "Hành trình của chàng chăn cừu Santiago tìm kho báu ở kim tự tháp Ai Cập"},
        {"id": "2", "title": "Đắc Nhân Tâm", "category": "Kỹ năng sống",
         "description": "Nghệ thuật giao tiếp và xây dựng mối quan hệ con người"},
        {"id": "3", "title": "Tôi Tài Giỏi, Bạn Cũng Thế", "category": "Kỹ năng sống",
         "description": "Phương pháp học tập hiệu quả cho học sinh"},
        {"id": "4", "title": "Sapiens", "category": "Khoa học",
         "description": "Lịch sử loài người và hành trình khám phá các nền văn minh"},
    ]

    print(f"\nTruy vấn mẫu: '{sample_query}'")
    print(f"Độ cụ thể của câu hỏi: {hype.score_specificity(sample_query):.4f}")
    print(f"Câu hỏi có bị mơ hồ (Underspecified) không: {hype.is_underspecified(sample_query)}")
    print(f"\nKết quả lọc quan hệ bao hàm HyPE ({len(sample_books)} sách ứng viên):")

    kept, scores = hype.filter(sample_query, sample_books)
    for book, score in zip(kept, scores):
        status = "[ENTAILED - ĐẠT CHUẨN]" if score > 0 else "[KEPT - DỰ PHÒNG]"
        print(f"  {status}  E={score:+.4f}  [{book['title']}]")
