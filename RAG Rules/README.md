# KIẾN TRÚC RAG RULES VÀ HARNESS SYSTEM
## Đề tài: Hệ Thống Tư Vấn Sách Tự Động Sử Dụng RAG Nhằm Giảm Sai Lệch Thông Tin Và Gợi Ý Theo Nhu Cầu Người Dùng
Lĩnh vực: Hệ thống phần mềm (Software Systems) | Năm học: 2026-2027

---

## 1. TỔNG QUAN HỆ THỐNG HARNESS

Hệ thống áp dụng mô hình Governed RAG Harness gồm 3 tầng kiểm soát nhằm đảm bảo AI vận hành an toàn, minh bạch và giảm thiểu thông tin sai lệch:

```
                       [Người Dùng Nhắn Tin]
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. INPUT RULE HARNESS (legal_rules.py & rule_harness.py)        │
│  • Lọc các truy vấn bẻ khóa (Prompt Injection / Jailbreak)      │
│  • Kiểm soát nội dung theo Điều 10 Luật Xuất bản 2012           │
│  • Nhận diện câu hỏi ngoài phạm vi (Out-of-Domain)              │
└────────────────────────────────┬────────────────────────────────┘
                                 │ (Nếu hợp lệ)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. CHAT HARNESS & HYBRID SEARCH (search_algorithms.py)          │
│  • Quản lý phiên hội thoại và giỏ hàng tạm thời                 │
│  • Lexical Search (BM25) tìm theo tên sách và tác giả           │
│  • Dense Semantic Search (ChromaDB Cosine) tìm theo cốt truyện  │
│  • Hợp nhất thứ hạng bằng Reciprocal Rank Fusion (RRF)          │
│  • Tính điểm thương mại (Rating, Sales, Review Quality)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. OUTPUT RULE HARNESS (rule_harness.py)                        │
│  • Kiểm chứng: chỉ trả lời về sách có trong kết quả RAG         │
│  • Đối chiếu giá bán và tác giả với dữ liệu trong kho           │
│  • Đảm bảo tính minh bạch theo Luật Bảo vệ quyền lợi NTD 2023   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
                     [Câu Trả Lời An Toàn & Chuẩn Xác]
```

---

## 2. CĂN CỨ PHÁP LÝ VÀ CHUẨN MỰC NỘI DUNG (`legal_rules.py`)

1. **Luật Xuất bản Việt Nam 2012 (Điều 10):**
   - Lọc bỏ các từ khóa và nội dung vi phạm: kích động bạo lực, khiêu dâm, xuyên tạc lịch sử, vi phạm bản quyền xuất bản.
2. **Luật Bảo vệ quyền lợi người tiêu dùng 2023:**
   - Minh bạch giá niêm yết (VNĐ) và tình trạng kho hàng (`in_stock`).
   - Hạn chế đưa ra thông tin không có cơ sở hoặc mô tả sai lệch nội dung tác phẩm.

---

## 3. CÁC THUẬT TOÁN TÌM KIẾM (`search_algorithms.py`)

Hệ thống kết hợp hai phương pháp tìm kiếm:

### 3.1 Thuật toán BM25 (Lexical Matching)
Áp dụng công thức BM25 tiêu chuẩn:
$$\text{Score}_{\text{BM25}}(D, Q) = \sum_{i=1}^{N} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
Hỗ trợ tìm chính xác khi người đọc nhớ đúng tên sách hoặc tác giả.

### 3.2 Thuật toán Reciprocal Rank Fusion (RRF)
Hợp nhất kết quả từ BM25 và Vector Embedding ChromaDB:
$$\text{RRF\_Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)} \quad (k = 60)$$

### 3.3 Công thức tính điểm tổng hợp
$$Score_{\text{Total}} = \alpha \cdot Score_{\text{RRF}} + (1 - \alpha) \cdot (w_r \hat{R} + w_s \hat{S} + w_q Q)$$

---

## 4. ĐIỀU PHỐI VÀ KIỂM THỬ TỰ ĐỘNG (`chat_harness.py`)

1. **DialogueHarness:** Quản lý trạng thái phiên, ghi nhận sách đã chọn và tự động kích hoạt gợi ý 2 đến 3 tác phẩm cùng tác giả khi người dùng đưa sách vào giỏ hàng.
2. **AutomatedTestHarness:** Bộ công cụ kiểm thử tự động với 60 câu hỏi chuẩn (Ground Truth), chạy kiểm tra và xuất các chỉ số:
   - Độ trễ phản hồi trung bình và P95.
   - Tỷ lệ tuân thủ quy tắc an toàn nội dung.
   - Tỷ lệ câu trả lời có căn cứ dữ liệu (Faithfulness).

---
*Tài liệu kỹ thuật nội bộ, RAG Rules System*
