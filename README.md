# Hệ Thống Tư Vấn Sách Tự Động Tích Hợp RAG (Book RAG System)

> **Đề tài Nghiên cứu Khoa học Kỹ thuật (NCKH KHKT):**  
> *"Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin"*

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-8E75B2.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌟 Điểm Nổi Bật Của Dự Án

1. **Triệt tiêu Ảo giác thông tin (Anti-Hallucination):** Ràng buộc không gian sinh từ của LLM (Gemini 2.5 Flash) vào kho dữ liệu sách có thật 100%, bảo đảm thông tin tác giả, giá niêm yết và nhà xuất bản chính xác tuyệt đối.
2. **Thuật toán Tìm kiếm lai (Hybrid Search):** Kết hợp Dense Semantic Vector (ChromaDB + SentenceTransformers `all-MiniLM-L6-v2`) và Sparse Lexical (BM25) qua thuật toán hợp nhất thứ hạng Reciprocal Rank Fusion (RRF).
3. **Bộ lọc bao hàm Hyperbolic Poincaré Ball (HyPE):** Ứng dụng hình học phi Euclid (ECCV 2024) xây dựng nón bao hàm (Entailment Cones) để lọc bỏ sách lạc đề trước khi đưa vào LLM.
4. **Xếp hạng thương mại đa tiêu chí (Explainable AI):** Chấm điểm minh bạch theo công thức $Score = 75\% \text{ Semantic} + 25\% \text{ Commercial Ranking}$ (kết hợp Đánh giá sao, Doanh số bán thực tế và Chất lượng review).
5. **Chuẩn hóa Ngôn ngữ phi hình thức (Teencode & Tiếng lòng):** Tự động giải mã từ viết tắt, tiếng lóng và ánh xạ cảm xúc bạn đọc (thất tình, stress, mất động lực...) sang thể loại sách phù hợp.
6. **Dây cương an toàn pháp lý (Rule Harness):** Tự động chặn các truy vấn vi phạm Điều 10 Luật Xuất bản Việt Nam 2012 và phòng vệ tấn công bẻ khóa (Prompt Injection / Jailbreak).
7. **Giao diện Web trực quan:** Hỗ trợ Light/Dark mode, tìm kiếm bằng hình ảnh (Gemini Vision OCR), giỏ sách yêu thích và xuất phiếu tư vấn PDF khổ A4 có xác thực điện tử.

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
├── Back End/              # Máy chủ FastAPI, RAG Engine, Gemini Client, HyPE Filter
│   ├── config.py          # Cấu hình siêu tham số, hằng số toàn hệ thống
│   ├── gemini_client.py   # Tương tác Gemini API (Key Pool Rotation, Prompt Single-Call)
│   ├── hype_filter.py     # Bộ lọc bao hàm hình học phi Euclid Poincaré Ball
│   ├── indexer.py         # Quy trình nhúng vector và tạo chỉ mục ChromaDB
│   ├── main.py            # REST API FastAPI, Rate Limiting (SlowAPI), Async ThreadPool
│   ├── models.py          # Schema Pydantic định nghĩa request/response và boundary guards
│   ├── rag_engine.py      # Lõi thực thi chuỗi RAG 6 bước
│   ├── teen_normalizer.py # Chuẩn hóa teencode & bản đồ tâm trạng tiếng lòng
│   └── start_web.bat      # Script khởi chạy máy chủ 1-click + Cloudflare Tunnel
├── database/              # Kho dữ liệu sách (JSON) và từ điển Teencode
│   ├── sample.json        # Dữ liệu sách crawl thực tế
│   └── teencode_lexicon.json # Bộ từ điển teencode & quy tắc cảm xúc
├── Front End/             # Giao diện Web Vanilla HTML5/CSS3/JavaScript
│   ├── index.html         # Giao diện chatbot, giỏ sách, xuất PDF A4
│   └── avatar_data.js     # Dữ liệu hình ảnh đại diện
├── Icon Projects/         # Bộ icon định dạng SVG giao diện
├── RAG Rules/             # Dây cương quy tắc pháp lý & thuật toán tìm kiếm
│   ├── legal_rules.py     # Quy tắc an toàn theo Luật Xuất bản 2012
│   ├── rule_harness.py    # Input/Output Rule Harness chống Jailbreak
│   └── search_algorithms.py # Thuật toán BM25, Cosine, RRF, Commercial Scoring
├── Sample Tests/          # Bộ công cụ kiểm thử & đo lường khoa học
│   ├── ragas_evaluator.py # Đánh giá định lượng RAGAS (Dataset 60 Ground Truth)
│   ├── stress_test.py     # Kiểm thử chịu tải đồng thời (Concurrency Benchmark)
│   ├── survey_analyzer.py # Phân tích thống kê khảo sát SUS & Likert (Cronbach's Alpha)
│   └── chat_terminal.py   # Giao diện tương tác 9 kịch bản mẫu qua dòng lệnh
├── Web Database/          # Quản trị CSDL phiên SQLite 3NF (WAL Mode)
│   ├── db_manager.py      # Thread-Local Connection Pool, CRUD operations
│   ├── session_routes.py  # Router quản lý phiên và giỏ sách
│   └── schema.sql         # Cấu trúc CSDL quan hệ chuẩn 3NF
├── requirements.txt       # Danh sách thư viện Python phụ thuộc
└── .gitignore             # Danh mục loại trừ khi đẩy lên Git
```

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Yêu cầu hệ thống
* Python 3.10+ (Khuyên dùng Python 3.12+)
* Khóa Google Gemini API Key (miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey))

### 2. Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` bên trong thư mục `Back End/` (dựa trên mẫu `.env.example`):
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Khởi chạy ứng dụng
* **Cách 1 (Nhanh nhất trên Windows):** Nhấp đúp vào file `Back End/start_web.bat`.
* **Cách 2 (Dòng lệnh):**
  ```bash
  cd "Back End"
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
* Mở trình duyệt và truy cập: `http://localhost:8000`

---

## 📊 Kết Quả Đo Lường Thực Nghiệm

* **RAGAS Benchmark (60 Ground Truth):**
  * *Context Precision:* **0.985**
  * *Faithfulness (Độ trung thực):* **1.000** (0% ảo giác)
  * *Answer Relevance:* **0.942**
* **Khảo sát Trải nghiệm Người dùng ($N=30$):**
  * *Điểm chuẩn SUS (System Usability Scale):* **> 85/100** (Hạng A - Best Imaginable)
  * *Độ tin cậy thang đo Cronbach's Alpha:* $\alpha \ge 0.75$ (Đạt chuẩn khoa học cao)

---

## 📜 Giấy Phép & Đạo Đức Nghiên Cứu

Mã nguồn được phát triển phục vụ mục đích nghiên cứu khoa học, tuân thủ nghiêm ngặt Quy chế sử dụng AI có trách nhiệm và Điều 10 Luật Xuất bản Việt Nam 2012.
