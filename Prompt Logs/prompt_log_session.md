# Nhật ký câu lệnh AI (Prompt Log)

**Đề tài:** Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin và hỗ trợ học tập  
**Công cụ AI sử dụng:** Google Antigravity (Gemini model)  
**ID cuộc hội thoại:** `8a1ece72-b1ce-4c1a-a0e9-03b80f9b901b` & `d15e6f45-aaab-455b-9212-9d0423d333ec`  
**Thời gian thực hiện:** 25/09/2026 – 21/10/2026  
**Người thực hiện:** Học sinh nghiên cứu  

> Nhật ký này được lập theo quy định tại Phụ lục hướng dẫn sử dụng AI tạo sinh trong dự án nghiên cứu khoa học kỹ thuật học sinh trung học. Các đoạn mã do AI hỗ trợ tạo ra đều được đánh dấu chú thích `[AI-Assisted Code]` trong tệp nguồn tương ứng.

---

## PROMPT #01

**Thời gian:** 25/09/2026 ~22:22  
**Mục đích:** Khởi tạo bộ khung dự án và các tệp cốt lõi  
**Prompt gốc:**
> "bạn làm cho tôi đi"

**Ngữ cảnh:** Yêu cầu xây dựng hệ thống RAG chatbot tư vấn sách ban đầu gồm máy chủ FastAPI và giao diện web cơ bản.

**Kết quả AI tạo ra:**
- `Back End/main.py`: Ứng dụng FastAPI với các định tuyến `/`, `/chat`, `/buy`, `/health`
- `Back End/rag_engine.py`: Quy trình xử lý RAG gồm nhận diện tác giả, tìm kiếm và tính điểm gợi ý
- `Back End/gemini_client.py`: Trích xuất ý định và gọi API Gemini kèm cơ chế dự phòng
- `Back End/config.py`: Cấu hình tên mô hình, đường dẫn cơ sở dữ liệu vector và số lượng sách trả về
- `Back End/models.py`: Định nghĩa schema dữ liệu Pydantic (`ChatRequest`, `ChatResponse`, `BookResult`)
- `Back End/indexer.py`: Script trích xuất vector và nạp vào ChromaDB
- `Back End/requirements.txt`: Danh sách thư viện phụ thuộc ban đầu
- `Back End/start_web.bat`: Tệp batch khởi chạy nhanh máy chủ

**Tệp bị ảnh hưởng:** Các tệp nêu trên (tạo mới)  
**Phần học sinh tự làm:** Xác định yêu cầu đề tài và chuẩn bị môi trường chạy Python  

---

## PROMPT #02

**Thời gian:** 25/09/2026 ~22:28  
**Mục đích:** Bổ sung giao diện dòng lệnh để thử nghiệm nhanh  
**Prompt gốc:**
> "nhưng tôi muốn khi test là tôi (user dùng terminal) có thể nhập vào và test thử mà?"

**Kết quả AI tạo ra:**
- `Sample Tests/chat_terminal.py`: Script chạy trên terminal cho phép nhập câu hỏi qua vòng lặp `input()` để kiểm tra phản hồi của RAG engine mà không cần mở trình duyệt web.

**Tệp bị ảnh hưởng:** `Sample Tests/chat_terminal.py` (tạo mới)  

---

## PROMPT #03

**Thời gian:** 26/09/2026 ~00:40  
**Mục đích:** Sửa lỗi import và nâng cấp cơ chế gọi API  
**Prompt gốc:**
> "bạn check và làm tiếp giúp tôi" *(kèm ảnh chụp màn hình thông báo lỗi)*

**Kết quả AI tạo ra:**
- Sửa lỗi import thư viện trong `rag_engine.py`
- Bổ sung danh sách mô hình dự phòng trong `config.py` và `gemini_client.py` khi gặp lỗi giới hạn tần suất (HTTP 429) hoặc dịch vụ gián đoạn
- Bổ sung định tuyến cung cấp ảnh đại diện người dùng trong `main.py`

**Tệp bị ảnh hưởng:** `Back End/config.py`, `Back End/gemini_client.py`, `Back End/main.py`, `Back End/rag_engine.py`  
**Phần học sinh tự làm:** Kiểm tra log lỗi, cung cấp hình ảnh mô tả sự cố để AI xử lý  

---

## PROMPT #04

**Thời gian:** 26/09/2026 ~00:50  
**Mục đích:** Xây dựng khung giao diện web ban đầu  
**Prompt gốc:**
> "làm tiếp"

**Kết quả AI tạo ra:**
- Xây dựng bố cục trang web cơ bản với khung chat, ô nhập liệu và danh sách gợi ý sách ban đầu.

**Tệp bị ảnh hưởng:** `Back End/index.html` (sau này chuyển sang `Front End/index.html`)  

---

## PROMPT #05

**Thời gian:** 26/09/2026 ~09:25  
**Mục đích:** Thiết kế lại giao diện theo bản đặc tả phong cách Perplexity  
**Prompt gốc:**
> "bạn mod cho tôi giao diện của html theo 'C:\Users\lamq1\Downloads\DESIGN.md' được không?"

**Ngữ cảnh:** Tệp DESIGN.md chứa bản đặc tả về hệ thống phông chữ, bảng màu parchment, cấu trúc thẻ sách và cách bố trí màn hình.

**Kết quả AI tạo ra:**
- Viết lại toàn bộ mã nguồn giao diện HTML/CSS theo phong cách tối giản, bố cục cân đối và màu sắc trang nhã.

**Tệp bị ảnh hưởng:** `Front End/index.html`  
**Phần học sinh tự làm:** Nghiên cứu và chuẩn bị tệp đặc tả thiết kế DESIGN.md  

---

## PROMPT #06

**Thời gian:** 26/09/2026 ~10:02  
**Mục đích:** Bổ sung các tính năng tương tác trên giao diện  
**Prompt gốc (tóm tắt):**
> Đổi cơ chế gửi phím Enter và Shift+Enter; bổ sung thanh bên trái với nút phiên mới, ô tìm kiếm và chuyển đổi giao diện sáng/tối; bố trí thanh bên phải hiển thị kết quả sách.

**Kết quả AI tạo ra:**
- Cập nhật xử lý sự kiện bàn phím trong `index.html`
- Thiết kế thanh bên trái hỗ trợ quản lý phiên hội thoại và nút chuyển đổi Dark/Light mode
- Thiết lập cột bên phải hiển thị danh mục sách tìm được kèm điểm tương đồng

**Tệp bị ảnh hưởng:** `Front End/index.html`  

---

## PROMPT #07

**Thời gian:** 26/09/2026 ~10:16  
**Mục đích:** Chuẩn hóa các thành phần đồ họa và thông tin người dùng  
**Prompt gốc (tóm tắt):**
> Đổi tên người dùng hiển thị thành "Anonymous User", xử lý ảnh đại diện nền trong suốt, định dạng khung phiên bo góc và tạo bộ icon SVG đơn sắc.

**Kết quả AI tạo ra:**
- Tạo tệp `Front End/avatar_data.js` chứa chuỗi Base64 ảnh đại diện phục vụ chế độ chạy ngoại tuyến
- Tạo bộ biểu tượng vector SVG trong thư mục `Icon Projects/`
- Tinh chỉnh CSS giao diện theo tông màu đen trắng đồng bộ

**Tệp bị ảnh hưởng:** `Front End/index.html`, `Front End/avatar_data.js`, `Icon Projects/*.svg`  

---

## PROMPT #08

**Thời gian:** 26/09/2026 ~11:39  
**Mục đích:** Sửa lỗi hiển thị khi thu nhỏ thanh bên  
**Prompt gốc:**
> "minimize nó bị như này [ảnh] - icon user lấy cái icon màu xanh + user trắng thôi, xóa phông đi - xóa cái dấu lên xuống trong phần ngân sách"

**Kết quả AI tạo ra:**
- Bổ sung CSS cho trạng thái thu gọn thanh bên (ẩn nhãn chữ, căn giữa icon)
- Ẩn mũi tên tăng giảm số mặc định trên các ô nhập ngân sách
- Khắc phục lỗi thiếu dấu đóng ngoặc nhọn CSS trong nút đổi giao diện

**Tệp bị ảnh hưởng:** `Front End/index.html`  

---

## PROMPT #09

**Thời gian:** 26/09/2026 ~11:49  
**Mục đích:** Định dạng câu trả lời của mô hình ngôn ngữ trên giao diện  
**Prompt gốc:**
> "xóa cho tôi các dấu *" *(kèm ảnh chụp màn hình câu trả lời bị dính ký tự Markdown thô)*

**Kết quả AI tạo ra:**
- Cập nhật hàm xử lý Markdown trên trình duyệt (`formatBotMarkdown`) để chuyển đổi chính xác các thẻ in đậm, danh sách và loại bỏ các dấu hoa thị thừa.

**Tệp bị ảnh hưởng:** `Front End/index.html`  

---

## PROMPT #10

**Thời gian:** 26/09/2026 ~11:56  
**Mục đích:** Rà soát kế hoạch nghiên cứu và dọn dẹp các tệp tạm  
**Prompt gốc:**
> "bạn check plan xem, có cái nào cần thực hiện không, xóa bớt các file không cần thiết trong folder project, lọc lại nội dung thi các thứ nhé"

**Kết quả AI tạo ra:**
- Xóa các script tạm dùng một lần và thư mục cache không cần thiết
- Đồng bộ hóa các đầu mục công việc trong kế hoạch nghiên cứu

**Tệp bị ảnh hưởng:** `plan.md`  

---

## PROMPT #11 & #12

**Thời gian:** 26/09/2026 ~12:01 – 12:04  
**Mục đích:** Đối chiếu quy chế sử dụng AI tạo sinh và khởi tạo nhật ký câu lệnh  
**Prompt gốc:**
> "các nội dung tôi làm có bị vi phạm quy chế hay gì không?"  
> "Prompt logs thì bạn làm all từ cuộc trò chuyện này và liệu tôi dùng crawl sau đó nó tự nhập thì nó có tính vào việc AI bịa ra không?"

**Kết quả AI thực hiện:**
- Đối chiếu các quy định trong Phụ lục hướng dẫn sử dụng AI của cuộc thi NCKH
- Phân tích tính hợp lệ của việc thu thập dữ liệu: Crawler lấy dữ liệu từ các website xuất bản thực tế (Tiki, Fahasa) với URL kiểm chứng công khai, không phải dữ liệu do AI tự tạo lập nên hoàn toàn hợp lệ
- Khởi tạo tệp nhật ký `Prompt Logs/prompt_log_session.md`

**Tệp bị ảnh hưởng:** `Prompt Logs/prompt_log_session.md` (tạo mới)  

---

## PROMPT #13 & #14

**Thời gian:** 26/09/2026 ~12:09 – 12:18  
**Mục đích:** Xây dựng script thu thập dữ liệu sách thực tế từ Tiki  
**Prompt gốc:**
> "chỉ tôi Mở rộng dữ liệu lên 200–500 cuốn (thu thập thực tế)"  
> "bạn tiến hành gộp vào giúp tôi nhé, tôi vừa chạy xong và bạn update mỗi thể loại lấy 120 cuốn nhé"

**Kết quả AI tạo ra:**
- Viết `Back End/crawl_tiki.py` thu thập dữ liệu từ API công khai của Tiki theo các thể loại sách chính, làm sạch thẻ HTML và trích xuất các trường thông tin chuẩn (tiêu đề, tác giả, giá bán, lượt mua, đánh giá sao, mô tả)
- Gộp dữ liệu thu thập được vào `database/sample.json` và cập nhật chỉ mục vector qua `indexer.py`

**Tệp bị ảnh hưởng:** `Back End/crawl_tiki.py`, `database/sample.json`  
**Phần học sinh tự làm:** Trực tiếp chạy script thu thập dữ liệu trên máy tính  

---

## PROMPT #15 & #16

**Thời gian:** 26/09/2026 ~12:20 – 12:23  
**Mục đích:** Bổ sung nguồn thu thập sách từ nhà sách Fahasa  
**Prompt gốc:**
> "crawl thêm của fahasa nhé"  
> "bạn check và lấy all danh mục nhé" *(kèm ảnh chụp danh mục sách trong nước của Fahasa)*

**Kết quả AI tạo ra:**
- Viết `Back End/crawl_fahasa.py` sử dụng thư viện `curl_cffi` để thu thập dữ liệu theo 10 danh mục sách trong nước của Fahasa
- Chuẩn hóa định dạng dữ liệu đầu ra đồng nhất với kho dữ liệu Tiki và lưu trữ song song bản JSON và JSONL

**Tệp bị ảnh hưởng:** `Back End/crawl_fahasa.py`, `database/sample_fahasa.json`  
**Phần học sinh tự làm:** Cung cấp danh mục cần khảo sát, vận hành script thu thập  

---

## PROMPT #17

**Thời gian:** 26/09/2026 ~12:41  
**Mục đích:** Xây dựng bộ quy tắc kiểm duyệt nội dung và các thuật toán tìm kiếm lai  
**Prompt gốc:**
> "bạn làm vào folder 'RAG Rules' nhé và bạn có thể chỉnh workflow của crawler lên là cào mỗi danh mục tầm 150 sách không?"

**Kết quả AI tạo ra:**
- Thiết lập thư mục `RAG Rules/` gồm 5 mô-đun:
  1. `legal_rules.py`: Định nghĩa tiêu chí rà soát nội dung cấm theo Điều 10 Luật Xuất bản Việt Nam 2012
  2. `search_algorithms.py`: Thuật toán tìm kiếm BM25, hàm tính điểm Cosine và thuật toán hợp nhất thứ hạng Reciprocal Rank Fusion (RRF)
  3. `rule_harness.py`: Bộ kiểm soát đầu vào (chặn Prompt Injection, lọc truy vấn lạc đề) và đầu ra (đối chiếu tính xác thực của giá bán và tên sách)
  4. `chat_harness.py`: Đo lường độ trễ và quản lý lịch sử hội thoại
  5. `README.md`: Thuyết minh phương pháp luận thuật toán
- Tích hợp `InputRuleHarness` vào quy trình tìm kiếm trong `rag_engine.py`

**Tệp bị ảnh hưởng:** `RAG Rules/*`, `Back End/rag_engine.py`, `Back End/crawl_tiki.py`, `Back End/crawl_fahasa.py`  

---

## PROMPT #18

**Thời gian:** 26/09/2026 ~12:55  
**Mục đích:** Bổ sung tính năng giỏ sách quan tâm và đồng bộ trạng thái chọn mua  
**Prompt gốc:**
> "ví dụ, nếu user nhấn đã chọn mua ấy, thì bạn code thêm giao diện giỏ hàng vào thanh side và khi user không muốn mua nữa ấy thì user có thể nhấn xóa..."

**Kết quả AI tạo ra:**
- Thiết kế khu vực danh sách sách đã chọn trên cột bên phải với tính năng thêm sách, xóa từng cuốn hoặc dọn sạch danh sách
- Bổ sung định tuyến `@app.post("/remove_from_cart")` trong `main.py` để đồng bộ dữ liệu giỏ sách theo từng phiên

**Tệp bị ảnh hưởng:** `Front End/index.html`, `Back End/main.py`  

---

## PROMPT #19

**Thời gian:** 26/09/2026 ~13:20  
**Mục đích:** Xử lý chuyển đổi tác giả trong hội thoại và thay thông báo chat bằng cửa sổ nổi  
**Prompt gốc (tóm tắt):**
> Xử lý trường hợp người dùng đổi sang hỏi tác giả khác; chuyển thông báo chọn mua sách thành dạng popup nổi thay vì gửi vào luồng chat; cho chạy luân phiên danh ngôn sách ở trang chủ.

**Kết quả AI tạo ra:**
- Bổ sung trường nhận diện `exclude_author` và `is_topic_switch` trong prompt trích xuất ý định của `gemini_client.py`
- Cài đặt bộ lọc loại trừ tác giả cũ trong `rag_engine.py` để tránh gợi ý lẫn lộn
- Xây dựng hệ thống thông báo nổi (Toast Notification) tự động biến mất sau 2 giây khi chọn mua sách
- Tạo hiệu ứng hiển thị luân phiên các câu danh ngôn về việc đọc sách trên trang chủ

**Tệp bị ảnh hưởng:** `Back End/gemini_client.py`, `Back End/rag_engine.py`, `Front End/index.html`  

---

## PROMPT #20

**Thời gian:** 26/09/2026 ~13:45 – 14:05  
**Mục đích:** Đo lường định lượng theo bộ tiêu chí chuẩn RAGAS  
**Prompt gốc:**
> "bạn chạy Đánh giá RAGAS (Faithfulness, Answer Relevance, Context Precision, Recall) cho tôi nhé và cho dẫn chứng nguồn cụ thể"

**Kết quả AI tạo ra:**
- Xây dựng bộ ngữ liệu kiểm định gồm 60 câu hỏi Ground Truth (`Sample Tests/ground_truth_60.json`) chia đều cho 6 nhóm nghiệp vụ thực tế
- Viết script `Sample Tests/ragas_evaluator.py` đo đạc 4 chỉ số theo phương pháp luận của Shahul Es et al. (EMNLP 2023)
- Sửa thuật toán nhận diện tên tác giả bằng biểu thức chính quy ranh giới từ `\b` trong `rag_engine.py`
- Xuất báo cáo đánh giá khoa học `Sample Tests/RAGAS_EVALUATION_REPORT.md` và tệp dữ liệu thô `Sample Tests/ragas_benchmark_results.json`

**Tệp bị ảnh hưởng:** `Sample Tests/ground_truth_60.json`, `Sample Tests/ragas_evaluator.py`, `Sample Tests/RAGAS_EVALUATION_REPORT.md`, `Back End/rag_engine.py`  
**Phần học sinh tự làm:** Thẩm định bộ 60 câu hỏi kiểm thử và kiểm tra kết quả đánh giá  

---

## PROMPT #21

**Thời gian:** 26/09/2026 ~14:10 – 14:18  
**Mục đích:** Đo lường hiệu năng chịu tải và tối ưu hóa xử lý bất đồng bộ  
**Prompt gốc:**
> "làm cho tôi cái mà dùng để làm stress test và stress test bằng colab google"

**Kết quả AI tạo ra:**
- Viết `Sample Tests/stress_test.py` đo lường độ trễ ở các mức tải 1, 10, 30 người dùng đồng thời và tự động xuất biểu đồ
- Tạo Jupyter Notebook `Sample Tests/stress_test_colab.ipynb` để kiểm thử từ xa qua hạ tầng Google Colab
- Tối ưu hóa backend FastAPI: Đưa hàm tìm kiếm RAG vào worker thread (`asyncio.to_thread`) tránh làm nghẽn vòng lặp sự kiện, duy trì tỷ lệ lỗi 0.0%

**Tệp bị ảnh hưởng:** `Sample Tests/stress_test.py`, `Sample Tests/stress_test_colab.ipynb`, `Back End/main.py`  

---

## PROMPT #22

**Thời gian:** 27/09/2026 ~16:30  
**Mục đích:** Xây dựng công cụ phân tích kết quả khảo sát người dùng chuẩn quốc tế  
**Prompt gốc:**
> "viết cho tôi script phân tích kết quả khảo sát từ Google Form, tính điểm SUS và Cronbach's Alpha rồi xuất biểu đồ báo cáo"

**Kết quả AI tạo ra:**
- Viết `Sample Tests/survey_analyzer.py` đọc dữ liệu khảo sát thực tế từ 37 người tham gia (`survey_responses.csv`)
- Tính toán điểm System Usability Scale (SUS) đạt 88.72/100 (Hạng A - Excellent), hệ số Cronbach's Alpha đạt 0.939
- Tính toán độ tin cậy của thang đo 5 tiêu chí chuyên biệt cho hệ thống RAG đạt Cronbach's Alpha 0.865
- Tự động xuất biểu đồ trực quan `Sample Tests/survey_results_report.png` và báo cáo khoa học `Sample Tests/SURVEY_EVALUATION_REPORT.md`

**Tệp bị ảnh hưởng:** `Sample Tests/survey_analyzer.py`, `Sample Tests/SURVEY_EVALUATION_REPORT.md`, `Sample Tests/survey_results_report.png`  
**Phần học sinh tự làm:** Thu thập ý kiến khảo sát từ 37 người dùng độc lập (học sinh THPT, giáo viên, phụ huynh) qua Google Forms  

---

## PROMPT #23

**Thời gian:** 28/09/2026 ~10:15  
**Mục đích:** Khắc phục lỗi và nâng cao các chỉ số RAGAS trong đợt kiểm định số 2  
**Prompt gốc:**
> "đợt 1 kiểm tra RAGAS thì Context Recall với Faithfulness hơi thấp, bạn xem nguyên nhân và nâng cấp code giúp tôi"

**Kết quả AI tạo ra:**
- Bổ sung bảng ánh xạ khái niệm `CATEGORY_CONCEPT_MAP` để mở rộng truy vấn (Query Expansion) đối với các câu hỏi tìm sách theo ngữ cảnh chung (ví dụ "quà 18 tuổi", "học quản trị tiền bạc")
- Áp dụng biểu thức chính quy ranh giới từ `\b` xử lý độ tuổi, tránh việc số "6 tuổi" bị khớp nhầm vào chuỗi "16 tuổi"
- Tăng cường kiểm soát câu trả lời theo ngữ cảnh thực tế, nâng điểm Faithfulness từ 0.834 lên 0.940 và Context Recall từ 0.751 lên 0.885
- Đạt điểm trung bình điều hòa RAGAS tổng hợp 0.924 / 1.000

**Tệp bị ảnh hưởng:** `Back End/rag_engine.py`, `Sample Tests/RAGAS_EVALUATION_REPORT.md`  

---

## PROMPT #24

**Thời gian:** 05/10/2026 ~14:20  
**Mục đích:** Phát triển phân hệ Đọc và tương tác tài liệu học tập (Document RAG & Study Assistant)  
**Prompt gốc:**
> "tôi muốn học sinh có thể tải file PDF hoặc Word lên để chat với tài liệu, tóm tắt và tự tạo câu hỏi trắc nghiệm ôn tập"

**Kết quả AI tạo ra:**
- Viết `Back End/doc_pipeline.py` bóc tách cấu trúc tệp PDF (dùng PyMuPDF) và tệp Word .docx (dùng thư viện chuẩn `zipfile` và `xml.etree`), tự động gắn thẻ neo trang (`<!-- PAGE_ANCHOR: X -->`)
- Viết `Back End/doc_rag.py` quản lý chỉ mục vector tài liệu học tập theo từng phiên, hỗ trợ hỏi đáp kèm trích dẫn số trang
- Xây dựng tính năng tóm tắt tài liệu 3 cấp độ và Quiz Engine tự động tạo 10 câu hỏi trắc nghiệm có giải thích đáp án
- Xây dựng hệ thống quản lý cơ sở dữ liệu phiên SQLite ở chế độ Write-Ahead Logging (`Web Database/db_manager.py`, `Web Database/session_routes.py`, `Web Database/schema.sql`)

**Tệp bị ảnh hưởng:** `Back End/doc_pipeline.py`, `Back End/doc_rag.py`, `Web Database/*`, `Front End/index.html`  
**Phần học sinh tự làm:** Chuẩn bị các tài liệu mẫu (sách giáo khoa, chuyên đề ôn tập) để kiểm thử phân hệ  

---

## PROMPT #25

**Thời gian:** 12/10/2026 ~15:40  
**Mục đích:** Xây dựng phân hệ mở rộng kiểm soát an toàn dược học (OTC Gatekeeper)  
**Prompt gốc:**
> "thử nghiệm mở rộng kiến trúc RAG sang kiểm tra thuốc không kê đơn OTC, có chặn thuốc kê đơn và kiểm tra bệnh lý nền"

**Kết quả AI tạo ra:**
- Viết `Back End/otc_gatekeeper.py` và cơ sở tri thức `database/otc_medicines_kb.json` gồm 60 loại thuốc OTC phổ biến chuẩn hóa theo Dược Thư Quốc Gia và DrugBank
- Thiết lập hàng rào an toàn chặn yêu cầu tư vấn thuốc kê đơn (Rx) thuộc nhóm kháng sinh, thuốc an thần, tim mạch và corticoid
- Kiểm tra an toàn theo độ tuổi, giới tính và tiền sử bệnh lý (dạ dày, gan, thận, phụ nữ mang thai, thiếu men G6PD)

**Tệp bị ảnh hưởng:** `Back End/otc_gatekeeper.py`, `database/otc_medicines_kb.json`, `Front End/index.html`  
**Phần học sinh tự làm:** Tra cứu và xác minh danh mục thuốc OTC theo hướng dẫn của giáo viên cố vấn  

---

## PROMPT #26

**Thời gian:** 15/10/2026 ~09:30  
**Mục đích:** Ứng dụng lọc nón bao hàm hình học Poincaré Ball (HyPE Filter)  
**Prompt gốc:**
> "tích hợp thuật toán lọc nón hyperbolic theo bài báo ECCV 2024 để lọc bớt sách ngoài phạm vi trước khi gọi LLM"

**Kết quả AI tạo ra:**
- Viết `Back End/hype_filter.py` cài đặt công thức khoảng cách hyperbolic và góc nửa nón bao hàm trên đĩa Poincaré (Poincaré Ball Model)
- Cắt tỉa các đầu sách có góc nón không giao cắt với không gian ngữ nghĩa của truy vấn trước khi đưa vào ngữ cảnh mô hình ngôn ngữ lớn

**Tệp bị ảnh hưởng:** `Back End/hype_filter.py`, `Back End/rag_engine.py`  
**Phần học sinh tự làm:** Đọc bài báo khoa học Kim et al. (ECCV 2024) và đề xuất áp dụng vào đề tài  

---

## PROMPT #27

**Thời gian:** 19/10/2026 – 21/10/2026  
**Mục đích:** Hoàn thiện giao diện song ngữ, chuẩn hóa thuật ngữ tiếng Anh, sửa lỗi hiển thị và đồng bộ tài liệu  
**Prompt gốc:**
> "chỉnh thêm phần UI ở tiếng Anh cho cả study assistants và OTC, cập nhật lại số liệu đúng cho README và check lỗi CSS"

**Kết quả AI tạo ra:**
- Viết `Back End/otc_english_specs.py` chuẩn hóa toàn bộ thông số y tế sang Plain English (CEFR A2-B1)
- Bổ sung cơ chế chuyển đổi song ngữ Việt - Anh tức thời trên toàn bộ giao diện `Front End/index.html`
- Sửa thuộc tính CSS `appearance: textfield;` loại bỏ cảnh báo cú pháp linter trong IDE
- Tinh gọn prompt tư vấn trong `gemini_client.py` theo văn phong tự nhiên, không dùng câu chữ sáo rỗng
- Đồng bộ hóa các số liệu thực nghiệm khoa học (RAGAS 0.924, SUS 88.72) và cập nhật cấu trúc tệp đầy đủ trong `README.md`

**Tệp bị ảnh hưởng:** `Back End/otc_english_specs.py`, `Back End/gemini_client.py`, `Front End/index.html`, `README.md`, `Prompt Logs/prompt_log_session.md`  
**Phần học sinh tự làm:** Kiểm thử trực tiếp giao diện song ngữ trên các thiết bị máy tính xách tay và xác nhận kết quả  

---

*Nhật ký này được cập nhật đầy đủ đến ngày 21/10/2026 phục vụ công tác đối soát và nghiệm thu đề tài.*  
*Người lập: Học sinh nghiên cứu*
