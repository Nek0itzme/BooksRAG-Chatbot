# -*- coding: utf-8 -*-
"""
hype_filter.py — HYPE-inspired Hyperbolic Entailment Filtering (Text-only)
[AI-Assisted Code] Prompt #07 — Adaptation từ:
  "HYPE: Hyperbolic Entailment Filtering for Underspecified Images and Texts"
  Wonjae Kim et al., ECCV 2024 | arxiv: 2404.17507
  Nguồn: https://github.com/naver-ai/hype

Ý tưởng gốc (HyPE):
  - Nhúng văn bản vào không gian Hyperbolic (Poincaré Ball)
  - Dùng Entailment Cones để kiểm tra quan hệ bao hàm: A ⊆ B
  - Nếu query "entails" book description → sách phù hợp
  - Nếu không → lọc bỏ (underspecified/irrelevant)

Điều chỉnh cho bài toán tư vấn sách (text-only):
  - Nhúng (query, book_description) bằng SentenceTransformer → R^d
  - Map vào Poincaré Ball bằng Möbius transformation
  - Tính Entailment Score: E(q, b) = half-aperture angle(q) - distance(q, b)
  - Nếu E(q, b) > threshold → sách "entailed" bởi query → giữ lại
  - Đây là lọc BẤT ĐỐI XỨNG: khác cosine (đối xứng)
"""

import math
import warnings
from typing import Optional

import torch
import torch.nn.functional as F
import geoopt

# Tắt FutureWarning của torch.jit.script trên Python 3.14
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Hằng số Poincaré Ball ─────────────────────────────────────────────────────
CURVATURE   = 1.0    # độ cong của Poincaré Ball (K=1 chuẩn hóa)
BALL        = geoopt.PoincareBall(c=CURVATURE)
MAX_NORM    = 1.0 - 1e-5   # giới hạn an toàn trong ball (tránh biên |x|=1)

# ── Siêu tham số HyPE (văn bản) — ĐÃ CALIBRATE lại ──────────────────────────
# Vấn đề gốc: all-MiniLM trả về vector normalized (norm≈1) → tanh(1)≈0.76
# → tất cả điểm gần rìa Poincaré ball → cone cực hẹp (ψ≈0.055rad) → E luôn âm
# FIX: PROJECT_SCALE=0.3 → norm sau tanh ≈ 0.29, APERTURE_ALPHA=0.5 → ψ≈0.8rad
ENTAIL_THRESHOLD = -1.0   # Ngưỡng tuyệt đối (fallback khi dynamic threshold ko đủ)
APERTURE_ALPHA   = 0.5    # FIX: tăng 0.1 → 0.5 để cone đủ rộng cho text embedding
PROJECT_SCALE    = 0.3    # FIX: scale xuống trước tanh, giữ norm trong [0.1, 0.35]
MIN_HALF_ANGLE   = 0.05   # góc tối thiểu để tránh nan



# ─────────────────────────────────────────────────────────────────────────────
# Poincaré Ball Utilities
# ─────────────────────────────────────────────────────────────────────────────

def euclidean_to_poincare(x: torch.Tensor) -> torch.Tensor:
    """
    Map vector Euclidean → Poincaré Ball với scale điều chỉnh.
    x ∈ R^d → x_h ∈ B^d (|x_h| < 1)

    Vấn đề gốc: sentence-transformers trả về vector đã normalized (norm≈1).
    tanh(1.0) ≈ 0.76 → tất cả điểm nằm gần rìm ball → cone cực hẹp.
    FIX: nhân norm với PROJECT_SCALE trước tanh → giữ norm trong [0.1, 0.4].
         Điều này tạo ra cone rộng hơn và khoảng cách có ý nghĩa hơn.
    """
    norm = x.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    x_unit = x / norm
    # Scale xuống trước khi áp dụng tanh: norm_in ≈ 0.3 → tanh(0.3) ≈ 0.29
    scaled_norm = torch.tanh(norm * PROJECT_SCALE) * MAX_NORM
    return x_unit * scaled_norm


def poincare_distance(u: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """
    Khoảng cách Poincaré giữa 2 điểm u, v ∈ B^d.
    d(u,v) = (2/sqrt(K)) * arctanh(sqrt(K) * |(-u) ⊕ v|)
    Dùng geoopt.PoincareBall.dist() để tính chính xác.
    """
    return BALL.dist(u, v)


def half_aperture_angle(x: torch.Tensor) -> torch.Tensor:
    """
    Half-aperture angle của entailment cone tại điểm x ∈ B^d.
    Từ paper HyPE (Eq. 5), điều chỉnh cho text:
      ψ(x) = arcsin(APERTURE_ALPHA * (1 - |x|²) / |x|)
    Điểm gần gốc → cone rộng (underspecified / vague query)
    Điểm xa gốc  → cone hẹp (specific / concrete description)

    FIX: APERTURE_ALPHA tăng 0.1 → 0.5 để tạo cone có kích cỡ có ý nghĩa.
    """
    norm = x.norm(dim=-1).clamp(min=1e-8)
    # FIX: sự kết hợp PROJECT_SCALE + APERTURE_ALPHA mới cho ψ trong [0.05, 1.0] rad
    sin_val = (APERTURE_ALPHA * (1.0 - norm ** 2) / norm).clamp(-1.0 + 1e-6, 1.0 - 1e-6)
    angle = torch.asin(sin_val)
    return angle.clamp(min=MIN_HALF_ANGLE)


def entailment_score(query_h: torch.Tensor, book_h: torch.Tensor) -> torch.Tensor:
    """
    E(q, b) = ψ(q) - d_B(q, b)

    Nếu E > 0: book b nằm trong entailment cone của query q → entailed
    Nếu E ≤ 0: book b nằm ngoài cone → not entailed (lọc bỏ)

    Tính chất bất đối xứng: E(q,b) ≠ E(b,q)
    """
    psi_q = half_aperture_angle(query_h)           # cone width của query
    dist   = poincare_distance(query_h, book_h)    # khoảng cách Poincaré
    return psi_q - dist


# ─────────────────────────────────────────────────────────────────────────────
# Main HYPE Filter API
# ─────────────────────────────────────────────────────────────────────────────

class HyPEFilter:
    """
    HYPE Text Filter — lọc sách dựa trên Hyperbolic Entailment.

    Sử dụng:
        hype = HyPEFilter(embedder)
        kept_books, scores = hype.filter(query, candidate_books)
    """

    def __init__(self, embedder, threshold: float = ENTAIL_THRESHOLD):
        """
        embedder: SentenceTransformer instance (đã load sẵn từ rag_engine)
        threshold: E(q,b) > threshold mới giữ lại (mặc định = 0.0)
        """
        self.embedder  = embedder
        self.threshold = threshold

    def _embed_to_poincare(self, texts: list[str]) -> torch.Tensor:
        """Nhúng văn bản → R^d → Poincaré Ball."""
        with torch.no_grad():
            vecs = self.embedder.encode(texts, show_progress_bar=False,
                                        convert_to_tensor=True)
            vecs = F.normalize(vecs, dim=-1)       # chuẩn hóa trên mặt cầu đơn vị
        return euclidean_to_poincare(vecs)         # map vào Poincaré Ball

    def filter(
        self,
        query: str,
        books: list[dict],
        description_field: str = "description",
        top_k: Optional[int] = None,
    ) -> tuple[list[dict], list[float]]:
        """
        Lọc danh sách sách bằng HYPE Entailment.

        Args:
            query: câu hỏi người dùng
            books: danh sách sách từ ChromaDB/hard_filter
            description_field: trường văn bản của sách (default: 'description')
            top_k: chỉ giữ top-k sau khi lọc (None = giữ tất cả entailed)

        Returns:
            (kept_books, entailment_scores) — đã sort theo score giảm dần
        """
        if not books:
            return [], []

        # Xây văn bản đại diện mỗi sách: title + category + description
        book_texts = []
        for b in books:
            text = (
                f"{b.get('title', '')}. "
                f"Thể loại: {b.get('category', '')}. "
                f"{b.get(description_field, '')[:300]}"
            )
            book_texts.append(text)

        # Map query + books → Poincaré Ball
        all_texts   = [query] + book_texts
        all_h       = self._embed_to_poincare(all_texts)
        query_h     = all_h[0]                   # (d,)
        books_h     = all_h[1:]                  # (N, d)

        # Tính entailment score cho từng sách
        scores = []
        for i in range(len(books)):
            e_score = entailment_score(query_h, books_h[i]).item()
            scores.append(e_score)

        # FIX: dùng ngưỡng động: median - 0.5*std thay vì threshold tuyệt đối.
        # Lý do: điểm E phụ thuộc scale của projection, cần so sánh tương đối.
        import statistics
        if len(scores) > 1:
            med   = statistics.median(scores)
            stdev = statistics.stdev(scores) if len(scores) > 2 else 0.3
            dyn_threshold = med - 0.5 * stdev
        else:
            dyn_threshold = self.threshold

        # Lọc: giữ sách có E(q,b) > dynamic_threshold
        kept = [
            (b, s) for b, s in zip(books, scores)
            if s > dyn_threshold
        ]

        # Nếu không có sách nào vượt threshold → hạ threshold và giữ top-3
        if not kept:
            sorted_all = sorted(zip(books, scores), key=lambda x: x[1], reverse=True)
            kept = sorted_all[:max(3, len(books) // 3)]

        # Sort theo entailment score giảm dần
        kept.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            kept = kept[:top_k]

        kept_books  = [item[0] for item in kept]
        kept_scores = [item[1] for item in kept]

        return kept_books, kept_scores

    def score_specificity(self, text: str) -> float:
        """
        Tính mức độ "specific" của một văn bản.
        Từ paper HyPE: điểm càng xa gốc Poincaré → càng cụ thể.
        
        Returns:
            specificity ∈ [0, 1] — 1 = rất cụ thể, 0 = rất mơ hồ
        """
        h = self._embed_to_poincare([text])[0]
        norm = h.norm().item()
        return float(norm / MAX_NORM)   # chuẩn hóa về [0,1]

    def is_underspecified(self, query: str, threshold: float = 0.15) -> bool:
        """
        Kiểm tra query có quá mơ hồ (underspecified) không.
        Nếu query quá vague → cần hỏi thêm thông tin.
        """
        spec = self.score_specificity(query)
        return spec < threshold


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor (dùng chung embedder với rag_engine)
# ─────────────────────────────────────────────────────────────────────────────

_hype_instance: Optional[HyPEFilter] = None


def get_hype_filter(embedder=None) -> HyPEFilter:
    """
    Lazy singleton — dùng chung embedder với rag_engine để tiết kiệm RAM.
    """
    global _hype_instance
    if _hype_instance is None:
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            from config import EMBEDDING_MODEL
            embedder = SentenceTransformer(EMBEDDING_MODEL)
        _hype_instance = HyPEFilter(embedder)
    return _hype_instance


# ─────────────────────────────────────────────────────────────────────────────
# CLI test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("HYPE Filter Test — Hyperbolic Entailment (Text-only)")
    print("=" * 60)

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    hype = HyPEFilter(embedder, threshold=0.0)

    query = "cậu bé chăn cừu đi tìm kho báu ở kim tự tháp Ai Cập"
    mock_books = [
        {"id": "1", "title": "Nhà Giả Kim", "category": "Văn học",
         "description": "Hành trình của chàng chăn cừu Santiago tìm kho báu ở kim tự tháp Ai Cập"},
        {"id": "2", "title": "Đắc Nhân Tâm", "category": "Kỹ năng sống",
         "description": "Nghệ thuật giao tiếp và xây dựng mối quan hệ con người"},
        {"id": "3", "title": "Tôi Tài Giỏi, Bạn Cũng Thế", "category": "Kỹ năng sống",
         "description": "Phương pháp học tập hiệu quả cho học sinh"},
        {"id": "4", "title": "Sapiens", "category": "Khoa học",
         "description": "Lịch sử loài người và hành trình khám phá các nền văn minh"},
    ]

    print(f"\nQuery: '{query}'")
    print(f"Specificity score: {hype.score_specificity(query):.4f}")
    print(f"Is underspecified: {hype.is_underspecified(query)}")
    print(f"\nEntailment Filtering ({len(mock_books)} sách):")

    kept, scores = hype.filter(query, mock_books)
    for book, score in zip(kept, scores):
        status = "✅ ENTAILED" if score > 0 else "⚠️ KEPT (fallback)"
        print(f"  {status}  E={score:+.4f}  [{book['title']}]")

    print("\n[Hàm entailment_score chi tiết]")
    all_h = hype._embed_to_poincare([query] + [b["description"] for b in mock_books])
    q_h = all_h[0]
    print(f"  Query Poincaré norm: {q_h.norm().item():.4f}")
    print(f"  Query half-aperture: {half_aperture_angle(q_h).item():.4f} rad")
    for i, b in enumerate(mock_books):
        b_h = all_h[i + 1]
        d = poincare_distance(q_h, b_h).item()
        psi = half_aperture_angle(q_h).item()
        e = psi - d
        print(f"  [{b['title']:30s}] dist={d:.4f}  ψ={psi:.4f}  E={e:+.4f}")
