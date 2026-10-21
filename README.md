# Hệ thống tư vấn sách tự động tích hợp RAG

> **Đề tài Nghiên cứu Khoa học Kỹ thuật:**  
> *"Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin và hỗ trợ học tập"*  
> **Lĩnh vực:** Hệ thống phần mềm (Systems Software)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.0_Flash-8E75B2.svg)](https://ai.google.dev/)
[![RAGAS Score](https://img.shields.io/badge/RAGAS_Harmonic_Mean-0.924-success.svg)](Sample%20Tests/RAGAS_EVALUATION_REPORT.md)
[![SUS Score](https://img.shields.io/badge/SUS_Score-88.72_(Grade_A)-brightgreen.svg)](Sample%20Tests/SURVEY_EVALUATION_REPORT.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Tổng quan đề tài

Hiện tượng mô hình ngôn ngữ lớn (LLM) tự tạo lập thông tin không có thực (*hallucination / confabulation*) là thách thức lớn khi ứng dụng AI vào việc tra cứu thông tin xuất bản, tư vấn sách học đường và y tế cộng đồng.

Hệ thống được thiết kế theo kiến trúc **Hybrid RAG hai đầu kiểm soát (Rule Harness + Vector Semantic + BM25 + Hyperbolic Poincaré Ball)** nhằm bảo đảm mọi nội dung tư vấn được đối chiếu chặt chẽ với kho dữ liệu thực tế, tuân thủ quy định xuất bản Việt Nam và mang lại trải nghiệm tra cứu tin cậy, trực quan cho học sinh và bạn đọc.

---

## Các phân hệ chính

### 1. Phân hệ tư vấn sách (Book RAG)
Xử lý ngôn ngữ tự nhiên từ câu hỏi của bạn đọc qua chuỗi tìm kiếm lai và xếp hạng chặt chẽ:
* **Quy mô ngữ liệu:** Kho dữ liệu tổng hợp **23,188 đầu sách** thu thập từ Tiki (21,411 sách) và Fahasa (1,500 sách) lưu trữ tại `database/sample.json`, cùng tập ngữ liệu chuẩn hóa **697 đầu sách** đại diện 6 nhóm chủ đề phục vụ đánh giá khoa học chuyên sâu.
* **Tìm kiếm lai (Hybrid Search):** Kết hợp tìm kiếm ngữ nghĩa thông qua mô hình nhúng `all-MiniLM-L6-v2` (384 chiều) trong cơ sở dữ liệu vector ChromaDB và thuật toán tìm kiếm từ khóa BM25, sau đó hợp nhất thứ hạng bằng **Reciprocal Rank Fusion (RRF)**.
* **Lọc nón bao hàm Hyperbolic (HyPE Filter):** Áp dụng mô hình hình học Poincaré Ball (Kim et al., ECCV 2024), cắt tỉa các nhánh sách nằm ngoài nón quan hệ ngữ nghĩa của truy vấn trước khi đưa vào ngữ cảnh LLM, giảm thiểu chi phí token và hiện tượng loãng thông tin.
* **Xếp hạng đa tiêu chí:** Điểm khuyến nghị tích hợp trọng số gồm **75% độ tương đồng ngữ nghĩa** và **25% các thuộc tính thực tế** (số sao đánh giá, số lượt mua và tỷ lệ phản hồi hợp lệ).
* **Chuẩn hóa ngôn ngữ học đường:** Tích hợp từ điển `database/teencode_lexicon.json` gồm **71 cụm từ teencode / tiếng lóng** tuổi học trò kết hợp **8 trạng thái tâm lý - cảm xúc** (`mood_map`) để mở rộng truy vấn (Query Expansion).
* **Khung kiểm soát hai đầu (Rule Harness):**
  * *Tiền kiểm:* Nhận diện và ngăn chặn tấn công chèn lệnh (Prompt Injection), lọc truy vấn ngoài phạm vi trong thời gian cực ngắn (**0.4 ms** qua O(1) regex in-memory).
  * *Hậu kiểm:* Đối chiếu giá bán thực tế, tên tác giả, nhà xuất bản và rà soát nội dung cấm theo **Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13**.
* **Bộ nhớ đệm ngữ nghĩa (Semantic Cache):** Lưu trữ tạm thời trên RAM các cặp truy vấn - kết quả tương đồng cao, phản hồi tức thời trong **~1.8 ms** và cắt giảm **35% - 50% số lượt gọi ra API ngoài**.

### 2. Phân hệ đọc và tương tác tài liệu (Document RAG & Study Assistant)
Hỗ trợ học sinh và giáo viên làm việc trực tiếp với giáo trình, tài liệu chuyên đề:
* **Hỗ trợ đa định dạng:** Xử lý trực tiếp tài liệu PDF (thông qua PyMuPDF) và tài liệu Microsoft Word (.docx, bóc tách cấu trúc OpenXML bằng thư viện chuẩn `zipfile` và `xml.etree`).
* **Định vị trang chính xác:** Tự động phân tách phân đoạn kèm thẻ neo trang (`<!-- PAGE_ANCHOR: X -->`), giữ nguyên cấu trúc bảng biểu và tiêu đề để câu trả lời luôn trích dẫn kèm số trang đối chiếu cụ thể.
* **Trình xem trước kép (Dual Previewer):** Khung xem trước song song dựng trang ảo trực tiếp trên giao diện web cho cả tài liệu PDF và Word (.docx).
* **Trợ lý học tập thông minh:**
  * Tóm tắt tài liệu theo 3 cấp độ: *Ý tưởng cốt lõi*, *Luận điểm chi tiết*, và *Đánh giá kết luận*.
  * Tự động tạo bộ đề thi trắc nghiệm **10 câu hỏi (Quiz Engine)** bám sát nội dung tài liệu, có chấm điểm tương tác, giải thích chi tiết từng câu và chỉ định trang tài liệu nguồn.
* **Tái sử dụng phiên qua SQLite (WAL Mode):** Khi chọn lại tài liệu đã tải lên trước đó, hệ thống tái sử dụng ngay bản trích xuất Markdown và chỉ mục vector sẵn có, không tạo bản sao thừa và không tốn thời gian nhúng lại.

### 3. Phân hệ mở rộng: Kiểm soát an toàn dược học (OTC Gatekeeper)
Được phát triển nhằm kiểm chứng tính tổng quát của kiến trúc Hybrid RAG + Rule Harness khi áp dụng vào lĩnh vực y tế cộng đồng:
* **Cơ sở tri thức chuẩn hóa:** Tích hợp **60 loại thuốc không kê đơn (OTC)** phổ biến tại Việt Nam (`database/otc_medicines_kb.json`), chuẩn hóa theo Dược Thư Quốc Gia Việt Nam và mã định danh DrugBank.
* **Hàng rào an toàn Rx:** Chặn tuyệt đối các yêu cầu tư vấn thuốc kê đơn (kháng sinh, thuốc an thần, thuốc tim mạch, kháng viêm steroid dạng uống/tiêm) và hướng dẫn người dùng đến cơ sở y tế gần nhất.
* **Cá nhân hóa an toàn:** Đối chiếu độ tuổi bệnh nhân, giới tính và tiền sử bệnh lý (viêm loét dạ dày, suy gan, suy thận, phụ nữ mang thai / cho con bú, thiếu men G6PD).
* **Từ điển thông số tiếng Anh chuyên dụng (`Back End/otc_english_specs.py`):** Ánh xạ tên chỉ định, chống chỉ định và liều dùng sang ngôn ngữ Plain English chuẩn mực (khung CEFR A2-B1), hỗ trợ chuyển đổi giao diện song ngữ mượt mà.

### 4. Giao diện người dùng & Khả năng tương thích (UI/UX)
* **Giao diện SPA hiện đại:** Xây dựng bằng HTML5, CSS hiện đại và thư viện hoạt họa GSAP, mang lại độ mượt cao và phản hồi trực quan.
* **Hỗ trợ song ngữ toàn diện (Bi-lingual Tiếng Việt - Tiếng Anh):** Nút chuyển đổi ngôn ngữ tức thời, tự động cập nhật toàn bộ nhãn, gợi ý mẫu, tài liệu hướng dẫn và dữ liệu chuyên ngành trên cả 3 phân hệ mà không cần tải lại trang.
* **Khả năng tương thích gõ tiếng Việt:** Tối ưu hóa sự kiện bàn phím IME, xử lý triệt để lỗi mất dấu hoặc vô tình gửi tin khi đang gõ tiếng Việt.
* **Tối ưu hiển thị cho máy tính xách tay:** Thiết kế giao diện tương thích tốt với màn hình 13 - 15 inch (breakpoint 1440px và chiều cao dưới 860px), trang bị nút thu gọn thanh bên (Sidebar Toggle) và thanh cuộn độc lập cho từng cột.

### 5. Hạ tầng điều phối và cơ chế chịu lỗi
* **Xoay vòng khóa API (Key Pooling):** Cơ chế xoay vòng thông minh cụm 5 khóa API Google Gemini, tự động kích hoạt thuật toán Exponential Backoff khi phát hiện lỗi giới hạn tần suất (HTTP 429) hoặc gián đoạn mạng.
* **Dự phòng thông minh (Fallback Model):** Tự động chuyển tiếp xử lý sang mô hình phụ `gemini-2.0-flash-lite` khi dịch vụ chính gặp độ trễ cao.
* **Lưu trữ phiên hai tầng (Dual-tier Storage):** Bộ nhớ RAM tốc độ cao phục vụ các truy vấn tức thời, kết hợp cơ sở dữ liệu SQLite ở chế độ Write-Ahead Logging (WAL) để lưu trữ bền vững lịch sử trò chuyện, tài liệu đã tải lên và danh mục sách quan tâm.

---

## Cấu trúc thư mục

```text
├── Back End/                       # Máy chủ FastAPI, RAG engine, client Gemini & các mô-đun xử lý
│   ├── config.py                   # Quản lý tham số hệ thống và danh sách khóa API
│   ├── crawl_all.py                # Điều phối thu thập dữ liệu tự động
│   ├── crawl_fahasa.py             # Script thu thập dữ liệu sách từ Fahasa
│   ├── crawl_tiki.py               # Script thu thập dữ liệu sách từ Tiki
│   ├── doc_pipeline.py             # Trích xuất cấu trúc PDF và Word (.docx) sang Markdown có neo trang
│   ├── doc_rag.py                  # Quản lý chỉ mục ChromaDB và hỏi đáp tài liệu học tập theo phiên
│   ├── gemini_client.py            # Giao tiếp API Gemini với cơ chế xoay vòng 5 khóa và gom cụm lệnh
│   ├── hype_filter.py              # Bộ lọc nón bao hàm hình học Poincaré Ball (HyPE)
│   ├── indexer.py                  # Tạo vector nhúng và lập chỉ mục ChromaDB
│   ├── main.py                     # Máy chủ FastAPI, định tuyến API và cấu hình middleware
│   ├── med_gatekeeper.py           # Mô-đun kiểm tra chống chỉ định cơ bản
│   ├── models.py                   # Định nghĩa schema dữ liệu Pydantic cho API
│   ├── otc_english_specs.py        # Từ điển Plain English chuẩn hóa cho dữ liệu y tế OTC
│   ├── otc_gatekeeper.py           # Rà soát an toàn dược học OTC và hàng rào chặn thuốc kê đơn Rx
│   ├── rag_engine.py               # Pipeline xử lý RAG hybrid, chấm điểm đa tiêu chí và cache
│   ├── teen_normalizer.py          # Chuẩn hóa từ lóng teencode và mở rộng truy vấn theo cảm xúc
│   ├── requirements.txt            # Thư viện phụ thuộc cho phần Back End
│   ├── crawl.bat                   # Script chạy nhanh quá trình crawl
│   └── start_tunnel.bat            # Script khởi chạy đường hầm mạng phụ trợ
├── database/                       # Kho dữ liệu sách, tri thức y tế và từ điển ngôn ngữ
│   ├── sample.json                 # Kho dữ liệu sách hợp nhất (23,188 đầu sách)
│   ├── sample_fahasa.json          # Dữ liệu sách thu thập từ Fahasa (1,500 đầu sách)
│   ├── sample_tiki.json            # Dữ liệu sách thu thập từ Tiki (21,411 đầu sách)
│   ├── otc_medicines_kb.json       # Cơ sở tri thức 60 loại thuốc OTC và chống chỉ định
│   ├── teencode_lexicon.json       # Từ điển 71 cụm từ teencode và 8 nhóm tâm trạng
│   ├── chroma_db/                  # Thư mục lưu trữ vector index nhúng nội bộ
│   └── user_uploads/               # Thư mục lưu trữ tài liệu người dùng tải lên
├── Front End/                      # Giao diện web người dùng (Single Page Application)
│   ├── index.html                  # Giao diện chính tích hợp HTML5, CSS hiện đại & GSAP
│   └── avatar_data.js              # Tài nguyên hình đại diện ngoại tuyến dạng Base64
├── Icon Projects/                  # Tài nguyên đồ họa và biểu tượng SVG
├── Project Rules/                  # Hồ sơ quy chế cuộc thi NCKH và tài liệu hướng dẫn AI
├── Prompt Logs/                    # Nhật ký câu lệnh prompt phục vụ minh bạch nghiên cứu
├── RAG Rules/                      # Quy tắc kiểm duyệt và thuật toán tìm kiếm
│   ├── chat_harness.py             # Đánh giá độ trễ và độ chuẩn xác hội thoại
│   ├── legal_rules.py              # Bộ quy tắc hậu kiểm pháp lý theo Luật Xuất bản
│   ├── rule_harness.py             # Khung kiểm soát an toàn đầu vào và đầu ra
│   ├── search_algorithms.py        # Cài đặt thuật toán BM25, Cosine, RRF và hàm tính điểm
│   └── README.md                   # Tài liệu hướng dẫn phân hệ RAG Rules
├── Sample Tests/                   # Bộ công cụ kiểm thử thực nghiệm và đánh giá khoa học
│   ├── ground_truth_60.json        # 60 kịch bản câu hỏi Ground Truth chia theo 6 nhóm nghiệp vụ
│   ├── ragas_evaluator.py          # Chương trình đo lường định lượng theo chuẩn RAGAS
│   ├── ragas_benchmark_results.json # Dữ liệu thô kết quả đo lường RAGAS
│   ├── RAGAS_EVALUATION_REPORT.md  # Báo cáo khoa học chi tiết kết quả đánh giá RAGAS
│   ├── stress_test.py              # Kịch bản kiểm thử tải đồng thời (Stress-test)
│   ├── stress_test_results.json    # Dữ liệu kết quả kiểm thử tải
│   ├── STRESS_TEST_REPORT.md       # Báo cáo đo lường hiệu năng và độ trễ
│   ├── survey_analyzer.py          # Chương trình phân tích thống kê khảo sát (SUS, Cronbach's Alpha)
│   ├── survey_responses.csv        # Dữ liệu khảo sát người dùng thực tế (N = 37)
│   ├── SURVEY_EVALUATION_REPORT.md # Báo cáo kết quả khảo sát người dùng chuẩn quốc tế
│   ├── run_logic_checks.py         # Kịch bản kiểm tra logic toàn diện hệ thống
│   └── chat_terminal.py            # Công cụ kiểm thử tương tác nhanh trên dòng lệnh
├── Web Database/                   # Cơ sở dữ liệu SQLite quản lý phiên (chế độ WAL)
│   ├── db_manager.py               # Xử lý kết nối, truy vấn và ghi log SQLite
│   ├── session_routes.py           # API router quản lý phiên trò chuyện và tài liệu
│   ├── schema.sql                  # Cấu trúc bảng cơ sở dữ liệu quan hệ
│   └── test_db.py                  # Script kiểm tra tính toàn vẹn cơ sở dữ liệu
├── requirements.txt                # Danh sách toàn bộ thư viện Python của dự án
├── start_web.bat                   # Script khởi chạy hệ thống trên mạng nội bộ
├── start_online_tunnel.bat         # Script khởi chạy hệ thống kèm Cloudflare Tunnel công khai
└── .gitignore                      # Cấu hình loại trừ của Git
```

---

## Cài đặt và khởi chạy

### 1. Yêu cầu môi trường
* Python 3.10 trở lên (khuyến nghị Python 3.11 hoặc 3.12 để đạt hiệu năng xử lý tốt nhất).
* Ít nhất 01 khóa API Google Gemini (đăng ký miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey)).

### 2. Cài đặt các thư viện phụ thuộc

```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo tệp `.env` trong thư mục `Back End/` theo mẫu:

```env
GEMINI_API_KEY=khoa_api_chinh_cua_ban
GEMINI_API_KEY_2=khoa_api_du_phong_1
GEMINI_API_KEY_3=khoa_api_du_phong_2
GEMINI_API_KEY_4=khoa_api_du_phong_3
GEMINI_API_KEY_5=khoa_api_du_phong_4
```

### 4. Khởi chạy ứng dụng

**Chế độ mạng nội bộ (Localhost):**
Nhấp đúp chuột vào tệp `start_web.bat` hoặc thực hiện lệnh:

```bash
cd "Back End"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Mở trình duyệt và truy cập tại địa chỉ: `http://localhost:8000`.

**Chế độ trực tuyến (Cloudflare Tunnel):**
Nhấp đúp chuột vào tệp `start_online_tunnel.bat`. Cửa sổ dòng lệnh sẽ tự động thiết lập và cung cấp một đường dẫn công khai bảo mật có dạng `https://*.trycloudflare.com` để thử nghiệm từ xa trên thiết bị di động hoặc máy tính khác.

---

## Kết quả thực nghiệm khoa học

### 1. Đánh giá chất lượng RAG theo chuẩn RAGAS (60 kịch bản Ground Truth)

Thực nghiệm được thực hiện trên 60 câu hỏi chuẩn hóa thuộc 6 nhóm nghiệp vụ thực tế (Nhớ mang máng cốt truyện, Gợi ý cùng tác giả, Lọc thể loại & ngân sách, Tìm theo cảm xúc, Độ tuổi tặng quà, Câu hỏi bẫy & an toàn).

| Chỉ số RAGAS | Đợt 1 (Mức cơ sở) | Đợt 2 (Sau tối ưu hóa) | Mục tiêu đề tài | Chênh lệch ($\Delta$) | Trạng thái |
|---|:---:|:---:|:---:|:---:|:---:|
| **Context Precision** (Độ chính xác ngữ cảnh) | 0.980 | **0.985** (±0.04) | $\ge 0.80$ | $+0.5\%$ | **Đạt** |
| **Context Recall** (Độ phủ thông tin) | 0.751 | **0.885** (±0.06) | $\ge 0.85$ | **$+13.4\%$** | **Đạt** |
| **Faithfulness** (Độ trung thực, không bịa đặt) | 0.834 | **0.940** (±0.05) | $\ge 0.90$ | **$+10.6\%$** | **Đạt** |
| **Answer Relevance** (Độ phù hợp của câu trả lời) | 0.885 | **0.890** (±0.04) | $\ge 0.85$ | $+0.5\%$ | **Đạt** |

> **Điểm trung bình điều hòa toàn diện (RAGAS Harmonic Mean):**  
> $$\text{RAGAS Score} = \frac{4}{\frac{1}{0.985} + \frac{1}{0.885} + \frac{1}{0.940} + \frac{1}{0.890}} = \mathbf{0.924 / 1.000}$$  
> *(Vượt ngưỡng mục tiêu nghiên cứu 0.850 đặt ra ban đầu).*

**So sánh đối chứng với mô hình LLM thuần không có RAG:**
* **Faithfulness:** Mô hình LLM thuần chỉ đạt **0.520** (thường xuyên bịa tên sách, nhầm lẫn tác giả hoặc tự nghĩ ra giá tiền), trong khi hệ thống RAG đạt **0.940** nhờ gắn chặt ngữ cảnh với kho sách đã kiểm duyệt.
* **Recall:** Mô hình thuần chỉ đạt **0.450** (chỉ nhớ các đầu sách phổ biến trên mạng), trong khi hệ thống đạt **0.885** giúp bạn đọc tiếp cận đầy đủ các tác phẩm chuyên biệt có trong thư viện.

### 2. Khảo sát trải nghiệm người dùng thực tế ($N = 37$)

Khảo sát được triển khai độc lập với 37 người dùng (19 học sinh THPT, 6 giáo viên/cán bộ giáo dục, 12 phụ huynh/bạn đọc tự do) dựa trên thang đo quốc tế **System Usability Scale (SUS)** và thang đo Likert 5 điểm chuyên sâu cho hệ thống RAG.

| Chỉ số đo lường | Kết quả thực nghiệm | Tiêu chuẩn học thuật | Đánh giá |
|---|:---:|:---:|---|
| **Điểm SUS trung bình** | **88.72 / 100** | $\ge 68.0$ (Ngưỡng trung bình) | Vượt chuẩn trung bình +20.72 điểm |
| **Độ lệch chuẩn (Std Dev)** | **±10.68** | Phương sai thấp | Mức độ đánh giá đồng đều giữa các nhóm |
| **Điểm trung vị (Median)** | **90.00** | Phân phối tập trung mức cao | Đa số người dùng đánh giá rất tốt |
| **Xếp loại mức độ hài lòng** | **Hạng A (Excellent)** | Hạng A: $\ge 80.3$ | Đạt mức xuất sắc theo chuẩn Bangor et al. |
| **Hệ số tin cậy Cronbach's Alpha (SUS)** | **0.939** | $\ge 0.70$ (Chuẩn tin cậy) | Độ tin cậy nội tại rất cao |
| **Hệ số Cronbach's Alpha (5 tiêu chí RAG)** | **0.865** | $\ge 0.70$ (Chuẩn tin cậy) | Mức độ nhất quán đánh giá cao |

**Đánh giá định lượng 5 khía cạnh cốt lõi của RAG (Thang điểm 1 - 5):**
1. *Tìm đúng sách khi chỉ nhớ mang máng cốt truyện:* **4.59 / 5.0** (100% người dùng đánh giá điểm 4 & 5).
2. *Tính hữu ích khi gợi ý tác phẩm cùng tác giả sau mua:* **4.49 / 5.0** (100% đồng ý).
3. *Độ tin cậy về giá bán và hạn chế suy diễn sai lệch:* **4.78 / 5.0** (Tiêu chí đạt điểm cao nhất).
4. *Tính minh bạch của điểm số tương đồng (Match %):* **4.68 / 5.0**.
5. *Mức độ tin cậy và vượt trội so với chatbot thông thường:* **4.78 / 5.0**.

### 3. Đo lường hiệu năng và khả năng chịu tải (Stress-test)

| Tầng xử lý | Độ trễ đo được | Cơ chế tối ưu |
|---|:---:|---|
| **Kiểm tra quy tắc an toàn (Rule Harness)** | **0.4 - 1.2 ms** | Khớp biểu thức chính quy O(1) in-memory, chặn injection trước khi gọi LLM |
| **Truy xuất bộ nhớ đệm (Semantic Cache Hit)** | **1.8 ms** | Đạt thông lượng $> 1,200\text{ req/s}$, giảm 100% chi phí gọi API đám mây |
| **Tìm kiếm lai nội bộ (ChromaDB + BM25 + RRF)** | **42.5 - 180 ms** | Lập chỉ mục vector tối ưu trên không gian 384 chiều |
| **Tổng hợp câu trả lời từ LLM (Gemini API)** | **1.2 - 2.2 s** | Duy trì ổn định thông qua cụm 5 API key xoay vòng |

---

## Ý nghĩa thực tiễn và đạo đức nghiên cứu

1. **Ý nghĩa học đường:** Dự án mang lại công cụ hỗ trợ đọc sách và học tập cá nhân hóa, giúp học sinh tra cứu tài liệu học tập, tự ôn luyện qua bài tập trắc nghiệm tự động và hình thành văn hóa đọc chủ động.
2. **Tuân thủ pháp luật và đạo đức AI:** Hệ thống được phát triển với tinh thần sử dụng AI có trách nhiệm trong giáo dục, tích hợp bộ lọc tuân thủ nghiêm ngặt **Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13** và các quy định an toàn thông tin hiện hành.

---

## Giấy phép sử dụng

Dự án được phân phối dưới giấy phép mã nguồn mở [MIT License](LICENSE).
