# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
search_algorithms.py — Các thuật toán tìm kiếm và xếp hạng lai (Hybrid Search Algorithms)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Thuật toán triển khai:
1. Lexical / Keyword Search (BM25) — tìm chính xác tên sách, tác giả, từ khóa.
2. Dense Semantic Search (Vector Embedding Cosine Similarity) — tìm theo ý định/cốt truyện mơ hồ.
3. Reciprocal Rank Fusion (RRF) — Hợp nhất thứ hạng từ nhiều nguồn tìm kiếm.
4. Điểm xếp hạng thương mại đa tiêu chí (Rating + Doanh số + Chất lượng đánh giá).
"""

import math
import re
from typing import List, Dict, Any, Tuple


class BM25Searcher:
    """
    Tìm kiếm từ khóa theo thuật toán BM25 (Okapi BM25).
    Hỗ trợ tìm chính xác tên sách, tên tác giả và các từ khóa đặc thù.
    """
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tách từ đơn giản, chuyển về chữ thường và lọc bỏ ký tự đặc biệt."""
        return re.findall(r"\w+", (text or "").lower())

    def _build_index(self) -> None:
        """Xây dựng chỉ mục ngược (Inverted Index) và tính trước TF, IDF cho kho sách."""
        total_len = 0
        df: Dict[str, int] = {}
        N = len(self.corpus)

        for doc in self.corpus:
            # Gộp các trường thông tin chính để tìm kiếm
            text = (
                f"{doc.get('title', '')} "
                f"{doc.get('author', '')} "
                f"{doc.get('publisher', '')} "
                f"{doc.get('category', '')} "
                f"{doc.get('description', '')}"
            )
            tokens = self._tokenize(text)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)

            # Tính tần số từ (TF) trong từng sách
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_freqs.append(tf)

            # Đếm số lượng sách có chứa từ khóa (DF)
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

        self.avg_doc_len = total_len / max(1, N)

        # Tính chỉ số IDF cho từng từ khóa
        for term, freq in df.items():
            self.idf[term] = math.log(1.0 + (N - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 20) -> List[Tuple[Dict[str, Any], float]]:
        """Truy vấn sách theo từ khóa BM25 và trả về danh sách có điểm số cao nhất."""
        q_tokens = self._tokenize(query)
        scores: List[Tuple[Dict[str, Any], float]] = []

        for idx, doc in enumerate(self.corpus):
            score = 0.0
            doc_tf = self.doc_freqs[idx]
            d_len = self.doc_len[idx]

            for t in q_tokens:
                if t in doc_tf:
                    freq = doc_tf[t]
                    idf_val = self.idf.get(t, 0.0)
                    
                    # Công thức tính điểm Okapi BM25
                    num = freq * (self.k1 + 1.0)
                    denom = freq + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                    score += idf_val * (num / denom)

            if score > 0:
                scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]], 
    k: int = 60
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Hợp nhất thứ hạng tương hỗ (RRF) từ nhiều danh sách kết quả (Vector Search + BM25).
    Sử dụng vị trí thứ hạng thay vì điểm số gốc để tránh lệch thang đo giữa các thuật toán.
    """
    rrf_scores: Dict[str, float] = {}
    doc_lookup: Dict[str, Dict[str, Any]] = {}

    for r_list in ranked_lists:
        for rank, doc in enumerate(r_list, start=1):
            doc_id = str(doc.get("id") or doc.get("tiki_id") or doc.get("title", ""))
            doc_lookup[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [(doc_lookup[doc_id], score) for doc_id, score in sorted_docs]


def compute_commercial_score(
    book: Dict[str, Any], 
    w_r: float = 0.50, 
    w_s: float = 0.30, 
    w_q: float = 0.20,
    max_sold: int = 5000
) -> float:
    """
    Tính điểm xếp hạng chất lượng bổ trợ dựa trên đánh giá sao, doanh số và độ tin cậy review.
    - Điểm sao: Chuẩn hóa từ thang 1-5 về [0, 1].
    - Doanh số: Dùng hàm logarit để giảm chênh lệch quá lớn giữa sách cũ và mới.
    - Độ tin cậy review: Dựa trên tỷ lệ đánh giá hợp lệ.
    """
    # 1. Chuẩn hóa rating về khoảng [0, 1]
    raw_rating = float(book.get("rating", 4.5))
    r_hat = max(0.0, min(1.0, (raw_rating - 1.0) / 4.0))

    # 2. Chuẩn hóa số lượng đã bán theo logarit
    sold = max(0.0, float(book.get("sold_count", 0)))  # clamp trước log — sold âm → log(-x) crash ValueError
    s_hat = math.log(1.0 + sold) / math.log(1.0 + max(1, max_sold))
    s_hat = min(1.0, max(0.0, s_hat))

    # 3. Hệ số tin cậy đánh giá
    valid_rev = float(book.get("valid_reviews", 1))
    total_rev = max(1.0, float(book.get("total_reviews", 1)))
    q_ratio = min(1.0, valid_rev / total_rev)
    q_confidence = min(1.0, valid_rev / 10.0)
    q_score = q_ratio * q_confidence

    return w_r * r_hat + w_s * s_hat + w_q * q_score
