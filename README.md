# Hệ thống tư vấn sách tự động tích hợp RAG

> Đề tài Nghiên cứu Khoa học Kỹ thuật:
> *"Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin và hỗ trợ học tập"*  
> Lĩnh vực: Hệ thống phần mềm (Systems Software)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.0_Flash-8E75B2.svg)](https://ai.google.dev/)
[![RAGAS Score](https://img.shields.io/badge/RAGAS_Harmonic_Mean-0.924-success.svg)](Sample%20Tests/RAGAS_EVALUATION_REPORT.md)
[![SUS Score](https://img.shields.io/badge/SUS_Score-88.72_(Grade_A)-brightgreen.svg)](Sample%20Tests/SURVEY_EVALUATION_REPORT.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 1. Tổng quan đề tài

Khi dùng mô hình ngôn ngữ lớn (LLM) để tìm kiếm sách hoặc hỗ trợ học tập, người dùng thường gặp hiện tượng mô hình tự bịa thông tin (hallucination). Mô hình có thể gợi ý những cuốn sách không có thật, gán sai tác giả hoặc đưa ra mức giá không đúng.

Dự án này giải quyết vấn đề trên bằng kiến trúc Hybrid RAG kết hợp lọc hình học Hyperbolic Poincaré Ball và khung kiểm soát hai đầu (Rule Harness). Mọi gợi ý đều được đối chiếu trực tiếp với kho dữ liệu sách thực tế và kiểm duyệt theo quy định xuất bản Việt Nam.

Hệ thống gồm 2 phân hệ độc lập:
1. Phân hệ 1: Tư vấn sách (Book RAG)
2. Phân hệ 2: Đọc và tương tác tài liệu học tập (Document RAG & Study Assistant)

---

## 2. Kiến trúc hai phân hệ

### Phân hệ 1: Tư vấn sách (Book RAG)

* Kho ngữ liệu thực tế: 23,188 đầu sách thu thập từ Tiki (21,411 cuốn) và Fahasa (1,500 cuốn) lưu tại `database/sample.json`. Một tập chuẩn hóa gồm 697 đầu sách thuộc 6 nhóm chủ đề được dùng cho các bài đánh giá thực nghiệm khoa học.
* Tìm kiếm lai (Hybrid Search): Kết hợp tìm kiếm ngữ nghĩa qua mô hình nhúng `all-MiniLM-L6-v2` (vector 384 chiều) trong ChromaDB và tìm kiếm từ khóa BM25, sau đó hợp nhất thứ tự bằng Reciprocal Rank Fusion (RRF).
* Lọc nón bao hàm Hyperbolic (HyPE Filter): Áp dụng hình học Poincaré Ball (`geoopt.PoincareBall`) để tính toán quan hệ bao hàm giữa câu hỏi và sách. Thuật toán cắt bỏ các sách nằm ngoài nón ngữ nghĩa trước khi đưa vào ngữ cảnh cho LLM, giúp giảm độ loãng thông tin và tiết kiệm token. Quá trình tính toán được vector hóa hoàn toàn qua PyTorch batch operations.
* Xếp hạng đa tiêu chí: Điểm gợi ý kết hợp 75% độ tương đồng ngữ nghĩa và 25% thuộc tính sách thực tế (50% điểm sao rating, 30% lượt mua đã bán, 20% chất lượng bình luận).
* Nhận diện tiếng lóng học trò: Từ điển `database/teencode_lexicon.json` gồm 71 từ lóng, viết tắt tuổi học trò cùng 8 nhóm trạng thái cảm xúc (`mood_map`) giúp hệ thống hiểu đúng câu hỏi tự nhiên của học sinh.
* Khung kiểm soát hai đầu (Rule Harness):
  * Tiền kiểm: Phát hiện và chặn các câu lệnh tấn công prompt injection, câu hỏi lạc đề qua tập biểu thức chính quy xử lý trong bộ nhớ (độ trễ dưới 1 ms).
  * Hậu kiểm: Đối chiếu lại tên sách, tác giả, giá tiền và rà soát nội dung theo Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13.
* Bộ nhớ đệm ngữ nghĩa: Lưu tạm trên RAM các cặp truy vấn có độ tương đồng cao, phản hồi kết quả trong khoảng 1.8 ms và giảm 35% đến 50% số lượt gọi ra API ngoài.

### Phân hệ 2: Đọc và tương tác tài liệu (Document RAG & Study Assistant)

* Xử lý đa định dạng: Đọc trực tiếp tài liệu PDF (qua PyMuPDF) và tài liệu Microsoft Word (.docx, bóc tách cấu trúc OpenXML bằng `zipfile` và `xml.etree`).
* Neo trang tài liệu: Tự động gắn thẻ neo trang (`<!-- PAGE_ANCHOR: X -->`) trong bản trích xuất Markdown. Khi trả lời câu hỏi, hệ thống luôn chỉ rõ số trang nguồn để học sinh dễ đối chiếu.
* Trình xem trước tài liệu: Cho phép xem song song nội dung PDF hoặc Word dựng lại trên giao diện web cùng lúc với cửa sổ hội thoại.
* Công cụ học tập:
  * Tóm tắt tài liệu theo 3 mức độ: tóm tắt ý chính, luận điểm chi tiết, và nhận xét tổng kết.
  * Tự động sinh đề trắc nghiệm 10 câu (Quiz Engine) bám sát nội dung bài học, có chấm điểm tương tác, giải thích đáp án và dẫn chứng trang nguồn.
* Quản lý phiên qua SQLite (WAL Mode): Người dùng có thể chọn lại tài liệu đã tải lên từ thư viện cá nhân mà không cần tải lại file hay tính toán lại vector nhúng.

---

## 3. Hạ tầng kỹ thuật và độ ổn định

* Cụm khóa API xoay vòng: Hệ thống nạp tối đa 5 khóa Google Gemini từ biến môi trường, tự động đổi khóa khi gặp lỗi quá hạn mức (HTTP 429) kèm thời gian chờ theo cấp số nhân (exponential backoff).
* Mô hình dự phòng: Khi mô hình chính `gemini-flash-lite-latest` gặp sự cố, hệ thống chuyển sang mô hình dự phòng `gemini-2.0-flash-lite` hoặc kích hoạt phản hồi mẫu dựa trên dữ liệu sách thực tế.
* Lưu trữ phiên 2 tầng: Sử dụng RAM để phản hồi nhanh các thao tác trong phiên và đồng bộ vào SQLite (Write-Ahead Logging) để lưu trữ lịch sử chat, giỏ sách và danh sách tài liệu.
* Bảo mật và kiểm soát truy cập: Giới hạn tần suất gọi API (20 lượt chat/phút/IP qua SlowAPI), cấu hình CORS không dùng cookie ngoài ý muốn, và khóa cách ly thư viện tài liệu giữa các session ID khác nhau.

---

## 4. Cấu trúc thư mục

```text
├── Back End/                       # Máy chủ FastAPI, RAG engine, client Gemini và các module xử lý
│   ├── config.py                   # Tham số hệ thống, trọng số xếp hạng và cấu hình model
│   ├── crawl_all.py                # Script điều phối thu thập dữ liệu
│   ├── crawl_fahasa.py             # Script crawl dữ liệu từ Fahasa
│   ├── crawl_tiki.py               # Script crawl dữ liệu từ Tiki
│   ├── doc_pipeline.py             # Trích xuất PDF và DOCX sang Markdown có thẻ neo trang
│   ├── doc_rag.py                  # Quản lý ChromaDB theo phiên và hỏi đáp tài liệu học tập
│   ├── gemini_client.py            # Kết nối Google Gemini API với cơ chế xoay vòng 5 key
│   ├── hype_filter.py              # Bộ lọc hình học Poincaré Ball (vector hóa bằng PyTorch)
│   ├── indexer.py                  # Tạo vector nhúng và nạp dữ liệu vào ChromaDB
│   ├── main.py                     # Máy chủ FastAPI, định tuyến API và middleware
│   ├── models.py                   # Schema dữ liệu Pydantic
│   ├── rag_engine.py               # Pipeline Hybrid RAG, chấm điểm đa tiêu chí và semantic cache
│   ├── teen_normalizer.py          # Chuẩn hóa teencode và ánh xạ cảm xúc học trò
│   ├── requirements.txt            # Danh sách thư viện phụ thuộc cho Back End
│   ├── crawl.bat                   # File thực thi crawl nhanh
│   └── start_tunnel.bat            # File khởi chạy Cloudflare Tunnel
├── database/                       # Kho dữ liệu sách và từ điển
│   ├── sample.json                 # Kho sách hợp nhất 23,188 cuốn
│   ├── sample_fahasa.json          # 1,500 sách từ Fahasa
│   ├── sample_tiki.json            # 21,411 sách từ Tiki
│   ├── teencode_lexicon.json       # 71 cụm từ lóng và 8 nhóm tâm trạng
│   ├── chroma_db/                  # Cơ sở dữ liệu vector ChromaDB
│   └── user_uploads/               # Thư mục chứa tài liệu học sinh tải lên theo phiên
├── Front End/                      # Giao diện web người dùng (Single Page Application)
│   ├── index.html                  # Giao diện chính gồm 2 phân hệ (HTML5, CSS, GSAP)
│   └── avatar_data.js              # Dữ liệu ảnh đại diện Base64
├── Icon Projects/                  # Biểu tượng và đồ họa giao diện
├── Project Rules/                  # Quy chế nghiên cứu và tài liệu chỉ dẫn
├── Prompt Logs/                    # Nhật ký prompt thử nghiệm
├── RAG Rules/                      # Quy tắc an toàn và thuật toán tìm kiếm
│   ├── chat_harness.py             # Đánh giá độ trễ và hội thoại
│   ├── legal_rules.py              # Bộ lọc pháp lý theo Luật Xuất bản
│   ├── rule_harness.py             # Lớp bảo vệ Input và Output
│   └── search_algorithms.py        # Cài đặt BM25, Cosine Similarity và RRF
├── Sample Tests/                   # Bộ công cụ kiểm thử và đánh giá khoa học
│   ├── run_logic_checks.py         # Bộ kiểm thử 29 assertion kiểm tra toàn diện codebase
│   ├── raw_google_form_survey_responses.csv # Dữ liệu thô 38 phiếu khảo sát thực tế từ Google Form
│   ├── ground_truth_60.json        # 60 kịch bản kiểm thử chia theo 6 nhóm nghiệp vụ
│   ├── ragas_evaluator.py          # Script đánh giá định lượng theo chuẩn RAGAS
│   ├── ragas_benchmark_results.json# Kết quả đánh giá RAGAS thô
│   ├── RAGAS_EVALUATION_REPORT.md  # Báo cáo kết quả RAGAS chi tiết
│   ├── stress_test.py              # Script kiểm thử tải đồng thời
│   ├── stress_test_results.json    # Kết quả kiểm thử tải
│   ├── STRESS_TEST_REPORT.md       # Báo cáo hiệu năng và độ trễ
│   ├── survey_analyzer.py          # Script phân tích khảo sát người dùng (SUS, Cronbach's Alpha)
│   ├── survey_responses.csv        # Ma trận điểm số khảo sát người dùng (37 mẫu chuẩn hóa)
│   ├── SURVEY_EVALUATION_REPORT.md # Báo cáo kết quả trải nghiệm người dùng
│   └── chat_terminal.py            # Công cụ chat thử nghiệm trên terminal
├── Web Database/                   # Cơ sở dữ liệu SQLite quản lý phiên
│   ├── db_manager.py               # Kết nối, ghi log và truy vấn SQLite (WAL mode)
│   ├── session_routes.py           # Định tuyến API quản lý tài khoản và lịch sử
│   ├── schema.sql                  # Cấu trúc bảng SQLite
│   └── test_db.py                  # Script kiểm tra cơ sở dữ liệu
├── requirements.txt                # Thư viện Python toàn hệ thống
├── start_web.bat                   # Script khởi chạy web nội bộ
└── start_online_tunnel.bat         # Script khởi chạy web kèm Cloudflare Tunnel
```

---

## 5. Hướng dẫn cài đặt và chạy thử

### Yêu cầu hệ thống
* Python 3.10 trở lên (khuyến nghị Python 3.11).
* Ít nhất 1 khóa Google Gemini API miễn phí từ [Google AI Studio](https://aistudio.google.com/app/apikey).

### Các bước thực hiện

1. Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

2. Tạo file cấu hình `Back End/.env` với nội dung:
```env
GEMINI_API_KEY=khoa_api_chinh_cua_ban
GEMINI_API_KEY_2=khoa_api_du_phong_1
GEMINI_API_KEY_3=khoa_api_du_phong_2
GEMINI_API_KEY_4=khoa_api_du_phong_3
GEMINI_API_KEY_5=khoa_api_du_phong_4
```

3. Khởi chạy máy chủ:
* Chạy trên máy nội bộ: nhấp đúp vào file `start_web.bat` hoặc gõ:
```bash
cd "Back End"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Truy cập giao diện tại: `http://localhost:8000`

* Chạy qua đường hầm Internet (Cloudflare Tunnel): nhấp đúp vào `start_online_tunnel.bat` để lấy đường link công khai dạng `https://*.trycloudflare.com`.

4. Chạy kiểm tra toàn bộ hệ thống:
```bash
python "Sample Tests/run_logic_checks.py"
```

---

## 6. Kết quả thực nghiệm

### Đánh giá chất lượng RAG theo chuẩn RAGAS

Thử nghiệm trên 60 kịch bản chuẩn thuộc 6 nhóm yêu cầu phổ biến của học sinh và độc giả:

| Tiêu chí | Điểm ban đầu | Sau tối ưu | Ngưỡng mục tiêu | Mức tăng | Đánh giá |
|---|:---:|:---:|:---:|:---:|:---:|
| Context Precision (Độ chính xác ngữ cảnh) | 0.980 | 0.985 | >= 0.80 | +0.5% | Đạt |
| Context Recall (Độ phủ thông tin) | 0.751 | 0.885 | >= 0.85 | +13.4% | Đạt |
| Faithfulness (Độ trung thực, không bịa đặt) | 0.834 | 0.940 | >= 0.90 | +10.6% | Đạt |
| Answer Relevance (Độ phù hợp của phản hồi) | 0.885 | 0.890 | >= 0.85 | +0.5% | Đạt |

Điểm trung bình điều hòa RAGAS đạt:
$$\text{RAGAS Score} = \frac{4}{\frac{1}{0.985} + \frac{1}{0.885} + \frac{1}{0.940} + \frac{1}{0.890}} = 0.924 / 1.000$$

Khi so sánh với mô hình LLM độc lập không có RAG:
* Faithfulness tăng từ 0.520 lên 0.940.
* Recall tăng từ 0.450 lên 0.885.

### Khảo sát trải nghiệm người dùng thực tế (N = 38)

Dữ liệu khảo sát thu thập trực tiếp từ Google Form (`Sample Tests/raw_google_form_survey_responses.csv`, 38 phiếu phản hồi) bao gồm 3 nhóm đối tượng: 20 học sinh THPT (52.6%), 12 phụ huynh học sinh và bạn đọc tự do (31.6%), cùng 6 giáo viên và cán bộ giáo dục (15.8%).

Thang đo System Usability Scale (SUS) và bộ câu hỏi đánh giá tính năng RAG:

| Chỉ số | Kết quả thực nghiệm | Tiêu chuẩn học thuật | Nhận xét |
|---|:---:|:---:|---|
| Điểm SUS trung bình | 88.72 / 100 | >= 68.0 | Vượt chuẩn trung bình 20.72 điểm |
| Độ lệch chuẩn | +-10.68 | Phân tán hẹp | Đánh giá giữa các nhóm khá đồng nhất |
| Điểm trung vị | 90.00 | Mức cao | Đa số người dùng hài lòng ở mức cao |
| Xếp loại mức độ hài lòng | Hạng A (Xuất sắc) | >= 80.3 | Đạt chuẩn Grade A (Bangor et al., 2008) |
| Cronbach's Alpha (SUS) | 0.939 | >= 0.70 | Thang đo đạt độ tin cậy nội tại cao |
| Cronbach's Alpha (bộ 5 câu RAG) | 0.865 | >= 0.70 | Mức độ nhất quán đánh giá cao |

Phân tích điểm số theo nhóm đối tượng:
* Giáo viên và cán bộ giáo dục (6 người): Điểm SUS trung bình đạt 92.50 / 100. Nhóm giáo viên đánh giá cao nhất tính chính xác của giá bìa niêm yết, nhà xuất bản và khả năng hỗ trợ soạn đề thi từ tài liệu học tập.
* Phụ huynh và bạn đọc tự do (12 người): Điểm SUS trung bình đạt 89.17 / 100. Nhóm phụ huynh ghi nhận hệ thống gợi ý sách bám sát độ tuổi và ngân sách thực tế.
* Học sinh THPT (20 người): Điểm SUS trung bình đạt 87.24 / 100. Học sinh thích tính năng tìm truyện theo cốt truyện mang máng, khả năng nhận diện tiếng lóng học trò và thi trắc nghiệm tương tác.

Điểm đánh giá 5 khía cạnh cốt lõi của RAG (thang điểm 5):
* Tìm đúng sách khi chỉ nhớ mang máng cốt truyện: 4.59 / 5.0 (100% người dùng đánh giá điểm 4 và 5).
* Tính hữu ích khi gợi ý tác phẩm cùng tác giả: 4.49 / 5.0 (100% đồng ý).
* Độ chính xác về giá bán và hạn chế suy diễn sai: 4.78 / 5.0 (tiêu chí đạt điểm cao nhất).
* Tính minh bạch của điểm số tương đồng Match %: 4.68 / 5.0.
* Độ tin cậy tổng thể so với chatbot thông thường: 4.78 / 5.0.

Phân bố phản hồi nổi bật từ tệp khảo sát thực tế:
* Về độ tin cậy của mô hình RAG: 28.9% người tham gia (11/38) ấn tượng nhất với tính chuẩn xác vượt trội so với các chatbot thông thường; 26.3% (10/38) tin tưởng hoàn toàn vào dữ liệu giá bìa và thông tin tác giả, xác nhận không thấy hiện tượng bịa sách; 21.1% (8/38) đánh giá cao việc minh bạch điểm số Match %; 13.2% (5/38) ghi nhận khả năng truy tìm sách theo cốt truyện và 10.5% (4/38) thích gợi ý cùng tác giả.
* Về trải nghiệm tương tác: 21.1% (8/38) đánh giá tính năng hội thoại, giỏ sách và hiển thị điểm tương đồng tích hợp rất gắn kết; 18.4% (7/38) nhận thấy giao diện dễ làm quen nhanh chóng và 18.4% (7/38) mong muốn sử dụng hệ thống thường xuyên trong việc đọc sách học đường.

### Đo lường hiệu năng xử lý (Stress-test)

| Tầng xử lý | Thời gian đo được | Cơ chế tối ưu |
|---|:---:|---|
| Kiểm tra quy tắc an toàn (Rule Harness) | 0.4 đến 1.2 ms | Regex O(1) in-memory, chặn lệnh xấu trước khi gửi đi |
| Truy xuất bộ nhớ đệm (Semantic Cache Hit) | 1.8 ms | Phản hồi ngay trên RAM, không mất chi phí API |
| Tìm kiếm lai (ChromaDB + BM25 + RRF) | 42.5 đến 180 ms | Lập chỉ mục vector 384 chiều kết hợp xếp hạng nhanh |
| Phản hồi từ Google Gemini | 1.2 đến 2.2 s | Cụm 5 API key xoay vòng và tự động retry |

---

## 7. Đạo đức nghiên cứu và tuân thủ pháp lý

Dự án tuân thủ Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13. Mọi phản hồi từ hệ thống đều được kiểm tra trước khi trả về cho người dùng để loại bỏ các nội dung vi phạm pháp luật, bảo vệ an toàn thông tin cho học sinh trong môi trường học đường.

---

## 8. Giấy phép

Dự án sử dụng giấy phép mã nguồn mở [MIT License](LICENSE).
