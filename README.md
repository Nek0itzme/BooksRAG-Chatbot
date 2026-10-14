# Hệ thống tư vấn sách tự động tích hợp RAG

> Đề tài Nghiên cứu Khoa học Kỹ thuật:
> *"Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin"*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.0_Flash-8E75B2.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Các phân hệ chính

### Tư vấn sách (Book RAG)

Phân hệ tư vấn sách xử lý truy vấn của độc giả qua chuỗi kiểm soát và xếp hạng thông tin:

* Tìm kiếm lai kết hợp tìm kiếm ngữ nghĩa bằng mô hình `all-MiniLM-L6-v2` lưu trong ChromaDB và tìm kiếm từ khóa BM25, sau đó hợp nhất thứ hạng bằng thuật toán Reciprocal Rank Fusion (RRF).
* Lọc nón bao hàm Hyperbolic HyPE trên mô hình hình học Poincaré Ball (Kim et al., ECCV 2024), loại bỏ các đầu sách không thuộc phạm vi ngữ nghĩa của câu hỏi trước khi đưa vào mô hình ngôn ngữ lớn.
* Xếp hạng đa tiêu chí tính toán điểm gợi ý dựa trên 75% độ tương đồng ngữ nghĩa và 25% các chỉ số thực tế gồm số sao đánh giá, lượt mua cùng tỷ lệ phản hồi hợp lệ.
* Chuẩn hóa từ ngữ lóng và teencode của học sinh thông qua từ điển `teencode_lexicon.json`, tự động ánh xạ biểu cảm sang thể loại sách phù hợp.
* Khung kiểm soát hai đầu (Rule Harness) gồm tiền kiểm chặn tấn công chèn lệnh (prompt injection), lọc truy vấn ngoài phạm vi và hậu kiểm đối chiếu giá bán, tên tác giả theo Điều 10 Luật Xuất bản Việt Nam 2012.

### Đọc và tương tác tài liệu (Document RAG)

Phân hệ hỗ trợ bạn đọc tải lên và làm việc trực tiếp với tài liệu học tập:

* Hỗ trợ định dạng PDF (sử dụng PyMuPDF) và Microsoft Word (.docx, bóc tách cấu trúc OpenXML bằng thư viện chuẩn `zipfile` và `xml.etree` của Python).
* Tự động chia trang và gắn thẻ neo (`<!-- PAGE_ANCHOR: X -->`), giữ nguyên cấu trúc bảng biểu và tiêu đề để trích dẫn chính xác số trang đối chiếu trong câu trả lời.
* Khung xem trước trực quan tích hợp cả tài liệu PDF và Word (.docx) trực tiếp trên giao diện web, tự động dựng trang ảo giúp tra cứu tương tự như xem PDF.
* Tóm tắt tài liệu theo ba cấp độ (ý tưởng chính, luận điểm chi tiết, kết luận) và tự động tạo đề thi trắc nghiệm 10 câu hỏi kèm đáp án giải thích chi tiết cùng số trang tham chiếu.
* Tái sử dụng tài liệu từ cơ sở dữ liệu SQLite: Khi người dùng chọn lại tài liệu đã tải lên, hệ thống sử dụng trực tiếp bản Markdown và chỉ mục vector sẵn có của phiên đó, không tạo bản sao hay bóc tách lại dữ liệu.

### Kiểm soát an toàn dược học (OTC Gatekeeper)

Phân hệ mở rộng này kiểm chứng tính tổng quát của kiến trúc Hybrid RAG và Rule Harness trên lĩnh vực y tế cộng đồng:

* Chặn các câu hỏi yêu cầu tư vấn thuốc kê đơn (Rx) thuộc nhóm kháng sinh, thuốc an thần, tim mạch và kháng viêm steroid theo danh mục quy định của Bộ Y Tế.
* Tra cứu thông tin từ cơ sở dữ liệu thuốc không kê đơn chuẩn hóa theo Dược Thư Quốc Gia Việt Nam và mã định danh DrugBank, đối chiếu độ tuổi, giới tính và tiền sử bệnh lý (dạ dày, gan, thận, thai kỳ, thiếu men G6PD).
* Tự động làm mới và đưa danh mục thuốc gợi ý phù hợp lên đầu cột hiển thị mỗi khi người dùng gửi câu hỏi mới trong khung chat.
* Ô nhập độ tuổi bệnh nhân để trống theo mặc định để người dùng chủ động điền thông tin chính xác.

### Giao diện người dùng và khả năng tương thích

* Giao diện SPA xây dựng bằng HTML5, CSS hiện đại và thư viện chuyển động GSAP.
* Khung nhập liệu hỗ trợ gõ và hiển thị đầy đủ dấu tiếng Việt trên cả ba khu vực trò chuyện (Tư vấn sách, Tương tác tài liệu, Dược học OTC), xử lý tốt sự kiện gõ IME khi gửi tin.
* Tối ưu hiển thị cho máy tính xách tay một màn hình (màn hình 13 đến 15 inch): Thiết lập bố cục tự co giãn qua media queries (`@media (max-width: 1440px)` và chiều cao dưới 860px), cột danh mục có thanh cuộn riêng biệt và trang bị nút thu gọn thanh bên (sidebar toggle) giúp các bộ lọc và khung chat luôn nằm trọn trong tầm nhìn.

### Xoay vòng khóa API và quản lý phiên

* Cơ chế xoay vòng tối đa 5 khóa API Google Gemini, tự động kích hoạt thuật toán exponential backoff khi gặp lỗi giới hạn tần suất (HTTP 429) hoặc sự cố kết nối.
* Tự động chuyển hướng dự phòng sang mô hình `gemini-2.0-flash-lite` khi dịch vụ chính gián đoạn.
* Quản lý phiên hai tầng: bộ nhớ RAM tạm thời giúp phản hồi nhanh các truy vấn tức thời, kết hợp cơ sở dữ liệu SQLite ở chế độ Write-Ahead Logging (WAL) để lưu trữ bền vững lịch sử trò chuyện, giỏ sách và tài liệu tải lên.

## Cấu trúc thư mục

```text
├── Back End/              # Máy chủ FastAPI, RAG engine, Gemini client, các phân hệ xử lý
│   ├── config.py          # Cấu hình tham số và danh sách khóa API
│   ├── doc_pipeline.py    # Trích xuất PDF và Word sang Markdown có thẻ neo trang
│   ├── doc_rag.py         # Lập chỉ mục ChromaDB và hỏi đáp tài liệu theo phiên
│   ├── gemini_client.py   # Gọi Gemini API với xoay vòng khóa và gọi gộp
│   ├── hype_filter.py     # Bộ lọc nón bao hàm hình học hyperbolic
│   ├── indexer.py         # Trích xuất vector và lập chỉ mục ChromaDB
│   ├── main.py            # API server FastAPI, định tuyến và middleware
│   ├── med_gatekeeper.py  # Kiểm tra chống chỉ định cơ bản
│   ├── models.py          # Schema Pydantic cho dữ liệu API
│   ├── otc_gatekeeper.py  # Rà soát an toàn dược phẩm OTC và cảnh báo Rx
│   ├── rag_engine.py      # Pipeline xử lý truy vấn RAG và tính điểm hybrid
│   ├── teen_normalizer.py # Chuẩn hóa teencode và ánh xạ cảm xúc
│   ├── crawl_fahasa.py    # Thu thập dữ liệu sách Fahasa
│   ├── crawl_tiki.py      # Thu thập dữ liệu sách Tiki
│   └── start_tunnel.bat   # Script khởi chạy phụ trợ
├── database/              # Dữ liệu sách, tri thức thuốc và từ điển ngôn ngữ
│   ├── sample.json        # Kho dữ liệu sách tổng hợp
│   ├── sample_fahasa.json # Dữ liệu sách thu thập từ Fahasa
│   ├── sample_tiki.json   # Dữ liệu sách thu thập từ Tiki
│   ├── otc_medicines_kb.json # Cơ sở tri thức thuốc OTC và chống chỉ định
│   └── teencode_lexicon.json # Từ điển chuẩn hóa teencode và tâm trạng
├── Front End/             # Giao diện web người dùng
│   ├── index.html         # Giao diện chính (SPA)
│   └── avatar_data.js     # Dữ liệu ảnh đại diện ngoại tuyến (Base64)
├── Icon Projects/         # Tài nguyên icon SVG
├── Project Rules/         # Quy chế cuộc thi NCKH và phụ lục hướng dẫn AI
├── Prompt Logs/           # Nhật ký câu lệnh prompt theo quy định NCKH
├── RAG Rules/             # Quy tắc kiểm duyệt và thuật toán tìm kiếm
│   ├── chat_harness.py    # Đánh giá độ trễ và độ chính xác hội thoại
│   ├── legal_rules.py     # Bộ kiểm tra an toàn theo Luật Xuất bản
│   ├── rule_harness.py    # Khung kiểm soát đầu vào và đầu ra
│   └── search_algorithms.py # Thuật toán BM25, Cosine, RRF và tính điểm
├── Sample Tests/          # Bộ công cụ kiểm thử và đánh giá khoa học
│   ├── run_logic_checks.py # Kiểm tra logic hệ thống và phát hiện lỗi tiềm ẩn
│   ├── ragas_evaluator.py # Đánh giá định lượng theo bộ tiêu chí RAGAS
│   ├── stress_test.py     # Kiểm thử tải đồng thời
│   ├── survey_analyzer.py # Phân tích thống kê kết quả khảo sát (SUS, Cronbach's Alpha)
│   └── chat_terminal.py   # Kiểm thử nhanh trên terminal
├── Web Database/          # Cơ sở dữ liệu SQLite phiên làm việc (WAL mode)
│   ├── db_manager.py      # Quản lý kết nối và thao tác SQLite
│   ├── session_routes.py  # Router quản lý phiên và tài liệu đã lưu
│   └── schema.sql         # Cấu trúc bảng cơ sở dữ liệu
├── start_online_tunnel.bat # Khởi chạy toàn bộ hệ thống kèm Cloudflare Tunnel
├── start_web.bat          # Khởi chạy hệ thống trên mạng cục bộ
├── requirements.txt       # Danh sách thư viện phụ thuộc
└── .gitignore             # Danh sách loại trừ của Git
```

## Cài đặt và khởi chạy

### Yêu cầu môi trường

* Python 3.10 trở lên (khuyên dùng Python 3.11 hoặc 3.12).
* Khóa API Google Gemini (đăng ký tại [Google AI Studio](https://aistudio.google.com/app/apikey)).

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### Thiết lập biến môi trường

Tạo file `.env` trong thư mục `Back End/` theo mẫu:

```env
GEMINI_API_KEY=khoa_api_chinh_cua_ban
GEMINI_API_KEY_2=khoa_api_du_phong_1
GEMINI_API_KEY_3=khoa_api_du_phong_2
GEMINI_API_KEY_4=khoa_api_du_phong_3
GEMINI_API_KEY_5=khoa_api_du_phong_4
```

### Khởi chạy ứng dụng

**Chạy cục bộ:** Mở `start_web.bat` hoặc chạy lệnh:

```bash
cd "Back End"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập giao diện tại `http://localhost:8000`.

**Chạy trực tuyến (Cloudflare Tunnel):** Mở `start_online_tunnel.bat`. Cửa sổ dòng lệnh sẽ hiển thị địa chỉ công khai dạng `https://*.trycloudflare.com` để thử nghiệm từ xa.

## Kết quả thực nghiệm

**Đánh giá RAGAS trên 60 mẫu Ground Truth:**

| Chỉ số | Kết quả |
|---|---|
| Context Precision | 0.985 |
| Faithfulness | 1.000 |
| Answer Relevance | 0.942 |

**Khảo sát người dùng (37 người tham gia):**

| Chỉ số | Kết quả |
|---|---|
| Điểm SUS (System Usability Scale) | 88.72 / 100 (Hạng A) |
| Cronbach's Alpha thang đo SUS | 0.939 |
| Cronbach's Alpha thang đo 5 tiêu chí RAG | 0.865 |

## Giấy phép và đạo đức nghiên cứu

Mã nguồn được phát triển phục vụ đề tài nghiên cứu khoa học học đường, tuân thủ hướng dẫn sử dụng trí tuệ nhân tạo có trách nhiệm trong giáo dục và Điều 10 Luật Xuất bản Việt Nam số 19/2012/QH13.
