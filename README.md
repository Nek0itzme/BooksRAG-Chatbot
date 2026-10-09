# Hệ Thống Tư Vấn Sách Tự Động Tích Hợp RAG

> Đề tài Nghiên cứu Khoa học Kỹ thuật (NCKH KHKT):  
> *"Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin"*

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-8E75B2.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Tính năng và kiến trúc cốt lõi

1. **Kiểm soát ảo giác thông tin (Anti-Hallucination):** Giới hạn phạm vi sinh từ của mô hình ngôn ngữ (Gemini 2.5 Flash) trong cơ sở dữ liệu sách đã kiểm chứng, đảm bảo thông tin tác giả, giá niêm yết và nhà xuất bản khớp với dữ liệu thực tế.
2. **Tìm kiếm lai (Hybrid Search):** Kết hợp tìm kiếm vector ngữ nghĩa (SentenceTransformers `all-MiniLM-L6-v2` + ChromaDB) và tìm kiếm từ khóa (BM25), sau đó hợp nhất thứ hạng bằng thuật toán Reciprocal Rank Fusion (RRF).
3. **Bộ lọc bao hàm Hyperbolic (HyPE):** Sử dụng mô hình Poincaré Ball (phỏng theo Kim et al., ECCV 2024) để lọc bỏ các kết quả nằm ngoài nón bao hàm của câu hỏi trước khi đưa vào LLM.
4. **Xếp hạng đa tiêu chí:** Tính điểm đề xuất theo công thức:
   $$\text{Score} = 0.75 \times \text{Semantic Score} + 0.25 \times \text{Commercial Score}$$
   trong đó điểm thương mại tính từ đánh giá sao, doanh số bán và chất lượng phản hồi của độc giả.
5. **Chuẩn hóa ngôn ngữ phi hình thức:** Tự động chuẩn hóa từ viết tắt, tiếng lóng (teencode) và ánh xạ các từ khóa cảm xúc (tiếng lòng) sang danh mục thể loại sách tương ứng thông qua từ điển cấu hình `teencode_lexicon.json`.
6. **Kiểm soát an toàn và tuân thủ pháp lý (Rule Harness):** Bộ quy tắc tiền kiểm và hậu kiểm nhằm chặn prompt injection, lọc câu hỏi ngoài phạm vi và rà soát nội dung theo Điều 10 Luật Xuất bản Việt Nam 2012.
7. **Giao diện người dùng:** Hỗ trợ giao diện sáng/tối, tìm kiếm bằng ảnh bìa sách (Gemini Vision OCR), quản lý giỏ sách và xuất phiếu tư vấn PDF khổ A4.

---

## Cấu trúc thư mục

```text
├── Back End/              # Máy chủ FastAPI, RAG engine, Gemini client, bộ lọc HyPE
│   ├── config.py          # Cấu hình tham số hệ thống
│   ├── gemini_client.py   # Module gọi Gemini API (xoay vòng key, prompt gộp)
│   ├── hype_filter.py     # Bộ lọc bao hàm hình học hyperbolic
│   ├── indexer.py         # Tiến trình trích xuất vector và lập chỉ mục ChromaDB
│   ├── main.py            # API server FastAPI và middleware
│   ├── models.py          # Schema Pydantic cho dữ liệu đầu vào/đầu ra
│   ├── rag_engine.py      # Pipeline xử lý truy vấn RAG
│   ├── teen_normalizer.py # Chuẩn hóa teencode và ánh xạ tâm trạng
│   └── start_web.bat      # Script khởi chạy nhanh máy chủ
├── database/              # Dữ liệu sách (JSON) và từ điển ngôn ngữ
│   ├── sample.json        # Dữ liệu sách mẫu
│   └── teencode_lexicon.json # Từ điển chuẩn hóa teencode và tâm trạng
├── Front End/             # Giao diện web người dùng
│   ├── index.html         # Mã nguồn giao diện chính
│   └── avatar_data.js     # Dữ liệu hình ảnh đại diện
├── Icon Projects/         # Tài nguyên icon SVG
├── RAG Rules/             # Quy tắc kiểm duyệt và thuật toán tìm kiếm
│   ├── legal_rules.py     # Bộ kiểm tra an toàn theo Luật Xuất bản
│   ├── rule_harness.py    # Khung kiểm soát đầu vào/đầu ra
│   └── search_algorithms.py # Thuật toán BM25, Cosine, RRF và scoring
├── Sample Tests/          # Bộ công cụ đánh giá và kiểm thử
│   ├── ragas_evaluator.py # Đánh giá định lượng theo bộ tiêu chí RAGAS
│   ├── stress_test.py     # Kiểm thử tải đồng thời
│   ├── survey_analyzer.py # Phân tích thống kê kết quả khảo sát (SUS, Cronbach's Alpha)
│   └── chat_terminal.py   # Giao diện kiểm thử nhanh trên terminal
├── Web Database/          # CSDL lưu trữ phiên làm việc SQLite (WAL mode)
│   ├── db_manager.py      # Quản lý kết nối và thao tác SQLite
│   ├── session_routes.py  # Router quản lý phiên và danh sách đã lưu
│   └── schema.sql         # Cấu trúc bảng CSDL
├── requirements.txt       # Danh sách thư viện phụ thuộc
└── .gitignore             # Cấu hình loại trừ file của Git
```

---

## Cài đặt và khởi chạy

### 1. Yêu cầu môi trường
* Python 3.10 trở lên (khuyến nghị 3.12)
* Khóa API Google Gemini (đăng ký tại [Google AI Studio](https://aistudio.google.com/app/apikey))

### 2. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 3. Thiết lập biến môi trường
Tạo file `.env` trong thư mục `Back End/` theo mẫu từ `.env.example`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Chạy ứng dụng
* **Windows (khởi chạy nhanh):** Chạy file `Back End/start_web.bat`.
* **Dòng lệnh:**
  ```bash
  cd "Back End"
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
* Truy cập ứng dụng tại: `http://localhost:8000`

---

## Kết quả thực nghiệm

* **Đánh giá RAGAS ($N=60$ mẫu Ground Truth):**
  * *Context Precision:* **0.985**
  * *Faithfulness:* **1.000** (không xuất hiện thông tin ngoài kho dữ liệu)
  * *Answer Relevance:* **0.942**
* **Khảo sát người dùng ($N=37$ người tham gia):**
  * *Điểm khả dụng SUS (System Usability Scale):* **88.72 / 100** (Hạng A - Excellent)
  * *Hệ số độ tin cậy Cronbach's Alpha (SUS):* $\alpha = 0.939$
  * *Hệ số độ tin cậy Cronbach's Alpha (5 tiêu chí RAG):* $\alpha = 0.865$

---

## Giấy phép và quy định đạo đức

Mã nguồn được phát triển phục vụ mục đích nghiên cứu khoa học học đường, tuân thủ các hướng dẫn về sử dụng AI có trách nhiệm trong giáo dục và Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13.
