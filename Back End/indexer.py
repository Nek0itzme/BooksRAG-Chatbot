# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
indexer.py — Tiến trình nhúng vector và tạo chỉ mục ChromaDB (Vector Indexing Pipeline)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này chịu trách nhiệm:
1. Đọc dữ liệu sách đã thu thập từ file JSON (sample.json).
2. Xây dựng văn bản tổng hợp đa trường (Tựa đề, Tác giả, Thể loại, Mô tả, Tags).
3. Sinh vector nhúng 384 chiều bằng mô hình SentenceTransformer ('all-MiniLM-L6-v2').
4. Lưu trữ và lập chỉ mục HNSW (Hierarchical Navigable Small World) trong ChromaDB với metric Cosine.
"""

import sys
import json
import time
from typing import List, Dict, Any

# Cấu hình UTF-8 cho console Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from config import (
    SAMPLE_JSON,
    CHROMA_PERSIST,
    CHROMA_COLLECTION,
    EMBEDDING_MODEL,
)

# ── Import thư viện Vector Database & Học sâu ─────────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"[ERROR] Thiếu thư viện: {e}")
    print("Vui lòng cài đặt: pip install chromadb sentence-transformers")
    sys.exit(1)


def build_embed_text(book: Dict[str, Any]) -> str:
    """
    XÂY DỰNG CHUỖI VĂN BẢN TỔNG HỢP ĐA TRƯỜNG ĐỂ NHÚNG VECTOR (MULTI-FIELD SYNTHESIS).
    Ghép các thành phần ngữ nghĩa quan trọng nhất: Tựa đề + Tựa gốc + Tác giả + Thể loại + Đối tượng + Mô tả + Tags.
    
    Returns:
        str: Chuỗi văn bản giàu ngữ nghĩa phân cách bởi dấu gạch đứng ' | '.
    """
    tags_str = " ".join(book.get("tags", []))
    parts = [
        book.get("title", ""),
        book.get("original_title", ""),
        book.get("author", ""),
        book.get("category", ""),
        book.get("target_audience", ""),
        book.get("description", ""),
        tags_str,
    ]
    return " | ".join(p.strip() for p in parts if p and p.strip())


def build_metadata(book: Dict[str, Any]) -> Dict[str, Any]:
    """
    CHUẨN HÓA METADATA LƯU TRỮ KÈM VECTOR TRONG CHROMADB.
    Lưu ý kỹ thuật: ChromaDB chỉ hỗ trợ các kiểu nguyên thủy (str, int, float, bool).
    Các trường dạng List (như tags) được chuẩn hóa thành chuỗi phân cách bởi dấu '|'.
    
    Returns:
        dict: Tập thuộc tính metadata dùng cho lọc cứng (Hard Filter) và hiển thị kết quả.
    """
    return {
        "id":              book["id"],
        "isbn":            book.get("isbn", ""),
        "title":           book["title"],
        "original_title":  book.get("original_title", ""),
        "author":          book["author"],
        "category":        book["category"],
        "publisher":       book.get("publisher", ""),
        "publish_year":    book.get("publish_year", 0),
        "price":           int(book.get("price", 0)),
        "original_price":  int(book.get("original_price", book.get("price", 0))),
        "rating":          float(book.get("rating", 0.0)),
        "sold_count":      int(book.get("sold_count", 0)),
        "total_reviews":   int(book.get("total_reviews", 0)),
        "valid_reviews":   int(book.get("valid_reviews", 0)),
        "in_stock":        bool(book.get("in_stock", True)),
        "target_audience": book.get("target_audience", ""),
        "tags":            "|".join(book.get("tags", [])),   # Chuyển đổi list -> string
        "description":     book.get("description", ""),
        "search_keyword":  book.get("search_keyword", ""),
    }


def run_indexer() -> None:
    """
    QUY TRÌNH THỰC THI INDEXER TỰ ĐỘNG:
    1. Đọc kho sách chuẩn từ sample.json.
    2. Tải mô hình học sâu SentenceTransformer.
    3. Thiết lập Collection HNSW Cosine trong ChromaDB.
    4. Sinh embeddings hàng loạt và nạp vào cơ sở dữ liệu theo từng Batch an toàn bộ nhớ.
    """
    print("=" * 70)
    print("📚 TIẾN TRÌNH LẬP CHỈ MỤC VECTOR DATABASE (CHROMADB INDEXER)")
    print("=" * 70)

    # Bước 1: Đọc và giải mã dữ liệu JSON
    print(f"\n[1/4] Đọc dữ liệu sách từ file: {SAMPLE_JSON}")
    with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    books = raw_data.get("data", raw_data) if isinstance(raw_data, dict) else raw_data
    print(f"      -> Tổng số sách phát hiện: {len(books)} cuốn")

    # Bước 2: Nạp mô hình nhúng ngữ nghĩa
    print(f"\n[2/4] Tải mô hình nhúng cục bộ: {EMBEDDING_MODEL}")
    t0 = time.time()
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    print(f"      -> Tải mô hình hoàn tất trong {time.time() - t0:.2f} giây")

    # Bước 3: Khởi tạo kết nối lưu trữ ChromaDB
    print(f"\n[3/4] Kết nối cơ sở dữ liệu vector bền vững tại: {CHROMA_PERSIST}")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST)

    # Xóa Collection cũ nếu đã tồn tại để đảm bảo tính toàn vẹn khi tái lập chỉ mục
    existing_cols = [c.name for c in client.list_collections()]
    if CHROMA_COLLECTION in existing_cols:
        client.delete_collection(CHROMA_COLLECTION)
        print(f"      -> Đã làm mới Collection '{CHROMA_COLLECTION}' để re-index")

    # Tạo Collection mới với không gian khoảng cách Cosine
    client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},   # Sử dụng khoảng cách Cosine (Cosine Distance Space)
    )
    collection = client.get_collection(CHROMA_COLLECTION)

    # Bước 4: Xây dựng văn bản, sinh vector và nạp vào ChromaDB theo Batch
    BATCH_SIZE = 500   # Kích thước lô tối ưu tránh nghẽn bộ nhớ RAM
    print(f"\n[4/4] Bắt đầu mã hóa vector & lưu trữ {len(books)} cuốn sách (Batch size = {BATCH_SIZE})...")
    t0 = time.time()

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for book in books:
        ids.append(book["id"])
        documents.append(build_embed_text(book))
        metadatas.append(build_metadata(book))

    # Mã hóa vector hàng loạt với SentenceTransformer
    print(f"   Đang sinh vector 384 chiều cho {len(documents)} văn bản...")
    embeddings = embedder.encode(documents, show_progress_bar=True, batch_size=64).tolist()

    # Thêm dữ liệu vào ChromaDB theo từng batch
    total_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"   Đang nạp vào ChromaDB ({total_batches} batch)...")
    for i in range(0, len(ids), BATCH_SIZE):
        batch_end = min(i + BATCH_SIZE, len(ids))
        collection.add(
            ids=ids[i:batch_end],
            embeddings=embeddings[i:batch_end],
            documents=documents[i:batch_end],
            metadatas=metadatas[i:batch_end],
        )
        batch_num = (i // BATCH_SIZE) + 1
        print(f"   ✅ Đã nạp xong Batch {batch_num}/{total_batches} ({batch_end}/{len(ids)} cuốn sách)", flush=True)

    elapsed = time.time() - t0
    print(f"\n✅ HOÀN TẤT THÀNH CÔNG! Đã lập chỉ mục {len(books)} cuốn sách trong {elapsed:.2f}s")
    print(f"   Collection: '{CHROMA_COLLECTION}' | Tổng số vector sẵn sàng: {collection.count()}")


if __name__ == "__main__":
    run_indexer()
