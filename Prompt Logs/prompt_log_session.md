# Nhật Ký Câu Lệnh AI (Prompt Log) — Phiên 01

**Đề tài:** Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG Chống Sai Lệch Thông Tin & Gợi Ý Cá Nhân Hóa  
**Công cụ AI sử dụng:** Google Antigravity (Gemini model)  
**ID Cuộc hội thoại:** `8a1ece72-b1ce-4c1a-a0e9-03b80f9b901b`  
**Thời gian phiên:** 25/09/2026 – 26/09/2026  
**Học sinh:** Anonymous User  

> Ghi chú: Nhật ký này được lập theo yêu cầu của Phụ lục 1 — Hướng Dẫn Sử Dụng AI Tạo Sinh Trong Dự Án Nghiên Cứu. Mọi đoạn code do AI tạo ra đều được gắn comment `[AI-Assisted Code]` trong file nguồn tương ứng.

---

## PROMPT #01

**Thời gian:** 25/09/2026 ~22:22  
**Mục đích:** Khởi tạo toàn bộ hệ thống  
**Prompt gốc:**
> "bạn làm cho tôi đi"

**Ngữ cảnh:** Yêu cầu build hệ thống RAG chatbot tư vấn sách từ đầu bao gồm backend FastAPI và giao diện web.

**Kết quả AI tạo ra:**
- `Back End/main.py` — FastAPI app với các routes: `/`, `/chat`, `/buy`, `/health`
- `Back End/rag_engine.py` — RAG pipeline: `detect_author()`, `run_rag()`, hybrid scoring
- `Back End/gemini_client.py` — `parse_intent()`, `generate_answer()`, multi-model fallback
- `Back End/config.py` — Cấu hình `GEMINI_FLASH`, `CHROMA_PATH`, `TOP_K`
- `Back End/models.py` — Pydantic models: `ChatRequest`, `ChatResponse`, `BuyRequest`, `BookResult`
- `Back End/indexer.py` — Script embed sách vào ChromaDB
- `Back End/requirements.txt` — Danh sách thư viện
- `Back End/start_web.bat` — Launcher 1 click

**Files bị ảnh hưởng:** Tất cả file trên (tạo mới)  
**Người tự làm:** Không (code ban đầu hoàn toàn do AI tạo)  
**Ghi chú:** Được phép theo quy chế — "Sử dụng AI để viết mã nguồn ban đầu cho dự án"

---

## PROMPT #02

**Thời gian:** 25/09/2026 ~22:28  
**Mục đích:** Thêm tính năng test terminal tương tác  
**Prompt gốc:**
> "nhưng tôi muốn khi test là tôi (user dùng terminal) có thể nhập vào và test thử mà?"

**Kết quả AI tạo ra:**
- `Sample Tests/chat_terminal.py` — Script terminal để test RAG engine trực tiếp qua input() loop

**Files bị ảnh hưởng:** `Sample Tests/chat_terminal.py` (tạo mới)  
**Ghi chú:** File này chỉ dùng để test nội bộ, không thuộc backend chính thức

---

## PROMPT #03

**Thời gian:** 25/09/2026 ~00:40 (26/09)  
**Mục đích:** Kiểm tra lỗi và tiếp tục hoàn thiện hệ thống  
**Prompt gốc:**
> "bạn check và làm tiếp giúp tôi" _(kèm ảnh screenshot lỗi)_

**Kết quả AI tạo ra:**
- Sửa lỗi import trong `rag_engine.py`
- Cập nhật `config.py`: `GEMINI_FLASH = "gemini-3.1-flash-lite"` (fallback từ model 503)
- Cập nhật `gemini_client.py`: thêm multi-model fallback loop (3.1-flash-lite → 3.8-flash → offline)
- Thêm route `/avatar.png` và `/avatar_data.js` vào `main.py`

**Files bị ảnh hưởng:** `config.py`, `gemini_client.py`, `main.py`, `rag_engine.py`  
**Người tự làm:** Debug (học sinh kiểm tra lỗi, AI sửa code)

---

## PROMPT #04

**Thời gian:** 25/09/2026 ~00:50  
**Mục đích:** Tiếp tục sau khi xem kết quả  
**Prompt gốc:**
> "làm tiếp"

**Kết quả AI tạo ra:**
- Tiếp tục hoàn thiện `index.html` — giao diện web cơ bản

**Files bị ảnh hưởng:** `Back End/index.html`

---

## PROMPT #05

**Thời gian:** 26/09/2026 ~09:25  
**Mục đích:** Redesign giao diện theo file thiết kế  
**Prompt gốc:**
> "bạn mod cho tôi giao diện của html theo 'C:\Users\lamq1\Downloads\DESIGN.md' được không?"

**Ngữ cảnh:** File DESIGN.md chứa spec thiết kế Perplexity AI style — typography, màu sắc, layout.

**Kết quả AI tạo ra:**
- Viết lại toàn bộ `Back End/index.html` (~1900+ dòng) theo phong cách Parchment/Perplexity

**Files bị ảnh hưởng:** `Back End/index.html` (viết lại toàn bộ)  
**Ghi chú:** Học sinh cung cấp file thiết kế (DESIGN.md), AI implement theo spec

---

## PROMPT #06

**Thời gian:** 26/09/2026 ~10:02  
**Mục đích:** Cập nhật nhiều tính năng UI cùng lúc  
**Prompt gốc (tóm tắt):**
> - Đổi cơ chế gửi: Enter = gửi, Shift+Enter = xuống hàng  
> - Thay đổi format câu trả lời chatbot  
> - Làm sidebar trái: nút + New Session, thu gọn taskbar, search sessions, danh mục session, user avatar ở góc dưới  
> - Thêm Dark/Light mode  
> - Hai thanh bên glassmorphism  
> - Thanh bên phải hiển thị kết quả sách  

**Kết quả AI tạo ra:**
- Cập nhật `index.html`: keyboard handler (Enter/Shift+Enter), sidebar layout, dark/light toggle, glassmorphism CSS

**Files bị ảnh hưởng:** `Back End/index.html`

---

## PROMPT #07

**Thời gian:** 26/09/2026 ~10:16  
**Mục đích:** Tinh chỉnh UI chi tiết  
**Prompt gốc (tóm tắt):**
> - Đổi tên "nek0itzme" → "Anonymous User"  
> - Avatar lấy từ file `C:\Users\lamq1\Downloads\avatar.png`  
> - Khung session trong ô bo tròn  
> - Xóa badge "NCKH 2026-2027 Pro"  
> - Xóa gợi ý "Enter để gửi • Shift+Enter xuống hàng"  
> - Xóa API Docs  
> - Đổi màu chủ đề từ xanh lá → trắng-đen monochrome glassmorphism  
> - Icons lấy từ Morphicons (SVG stroke style)

**Kết quả AI tạo ra:**
- Cập nhật `index.html`: màu sắc, layout, session UI
- Xử lý `avatar.png` → transparent PNG 256×256
- Tạo `avatar_data.js` — embed base64 avatar
- Tạo `Back End/process_avatar.py` _(script tạm — đã xóa)_
- Tạo `Back End/create_icons.py` _(script tạm — đã xóa)_
- Tạo 10 SVG icons trong `Icon Projects/`: search, chat, collapse, plus, chevron-down, trash, sparkles, book, send, moon, sun, image

**Files bị ảnh hưởng:** `index.html`, `avatar.png`, `avatar_data.js`, `Icon Projects/*.svg`

---

## PROMPT #08

**Thời gian:** 26/09/2026 ~11:39  
**Mục đích:** Fix UI khi sidebar thu nhỏ  
**Prompt gốc:**
> "minimize nó bị như này [ảnh] - icon user lấy cái icon màu xanh + user trắng thôi, xóa phông đi - xóa cái dấu lên xuống trong phần ngân sách"

**Kết quả AI tạo ra:**
- Sửa CSS collapsed sidebar: ẩn text, căn giữa icons
- Sửa `input[type="number"]::-webkit-inner-spin-button { display: none }`
- Cập nhật avatar display: `background: transparent; border: none`
- Fix missing `}` trong `.theme-toggle-btn` gây vỡ layout

**Files bị ảnh hưởng:** `Back End/index.html`

---

## PROMPT #09

**Thời gian:** 26/09/2026 ~11:49  
**Mục đích:** Xóa ký tự `*` trong câu trả lời chatbot  
**Prompt gốc:**
> "xóa cho tôi các dấu *" _(kèm ảnh screenshot)_

**Kết quả AI tạo ra:**
- Cập nhật hàm `formatBotMarkdown()` trong `index.html`: thêm `html.replace(/\*/g, '')` để xóa sạch dấu `*` còn sót

**Files bị ảnh hưởng:** `Back End/index.html` (JS function `formatBotMarkdown`)

---

## PROMPT #10

**Thời gian:** 26/09/2026 ~11:56  
**Mục đích:** Kiểm tra kế hoạch và dọn dẹp project  
**Prompt gốc:**
> "bạn check plan xem, có cái nào cần thực hiện không, xóa bớt các file không cần thiết trong folder project, lọc lại nội dung thi các thứ nhé"

**Kết quả AI thực hiện:**
- Xóa: `Back End/process_avatar.py`, `Back End/create_icons.py`, `__pycache__/` ở root
- Cập nhật và tái cấu trúc `plan.md`: thêm bảng tiến độ ✅/⏳, đồng bộ thông số kỹ thuật thực tế

**Files bị ảnh hưởng:** `plan.md` (cập nhật), xóa 2 script tạm + 1 thư mục cache

---

## PROMPT #11

**Thời gian:** 26/09/2026 ~12:01  
**Mục đích:** Kiểm tra tuân thủ quy chế  
**Prompt gốc:**
> "các nội dung tôi làm có bị vi phạm quy chế hay gì không?"

**Kết quả AI thực hiện:**
- Đọc Phụ lục 1, Phụ lục 2
- Phân tích từng hạng mục theo quy chế
- Chỉ ra các điểm cần lưu ý: Prompt Log chưa có, plan.md không được nộp làm kế hoạch chính thức, cần xác nhận tính thật của dữ liệu

**Files bị ảnh hưởng:** Không có (tư vấn thuần túy)

---

## PROMPT #12

**Thời gian:** 26/09/2026 ~12:04  
**Mục đích:** Tạo Prompt Log và giải thích về crawler  
**Prompt gốc:**
> "Prompt logs thì bạn làm all từ cuộc trò chuyện này và liệu tôi dùng crawl sau đó nó tự nhập thì nó có tính vào việc AI bịa ra không?"

**Kết quả AI thực hiện:**
- Tạo thư mục `Prompt Logs/`
- Tạo file `prompt_log_session_01.md` (file này)
- Giải thích về crawler (xem bên dưới)

**Files bị ảnh hưởng:** `Prompt Logs/prompt_log_session_01.md` (tạo mới)

---

## Câu hỏi về Crawler — Giải thích

> **"Dùng crawler tự động thu thập dữ liệu rồi nhập vào DB — có tính là AI bịa ra không?"**

**Trả lời: KHÔNG vi phạm**, với điều kiện:

| Điều kiện | Chi tiết |
|-----------|---------|
| ✅ Crawler lấy dữ liệu từ **website thật** (Tiki, Fahasa...) | Đây là dữ liệu thực tế, không phải AI sáng tác |
| ✅ Code crawler do **bạn tự viết** hoặc AI viết (với comment `[AI-Assisted Code]`) | Công cụ thu thập ≠ nguồn dữ liệu |
| ✅ Dữ liệu **có thể kiểm chứng** (link URL nguồn gốc) | Giám khảo có thể tra lại |
| ❌ Vi phạm nếu: dùng AI để **bịa ra** thông tin sách không có thật | Ví dụ: "hãy tạo cho tôi 500 cuốn sách giả" |

**Kết luận:** Crawler là **công cụ kỹ thuật** thu thập dữ liệu thật — hoàn toàn hợp lệ và thậm chí được khuyến khích vì là dữ liệu có nguồn gốc rõ ràng từ Tiki/Fahasa.

---

## PROMPT #13

**Thời gian:** 26/09/2026 ~12:09  
**Mục đích:** Hướng dẫn mở rộng dữ liệu lên 200–500 cuốn sách thực tế  
**Prompt gốc:**
> "chỉ tôi Mở rộng dữ liệu lên 200–500 cuốn (thu thập thực tế)"

**Kết quả AI tạo ra:**
- Tạo `Back End/crawl_tiki.py` — script thu thập dữ liệu thật từ API Tiki.vn theo 5 danh mục, làm sạch HTML, chuẩn hóa 12 trường dữ liệu.

**Files bị ảnh hưởng:** `Back End/crawl_tiki.py` (tạo mới)

---

## PROMPT #14

**Thời gian:** 26/09/2026 ~12:18  
**Mục đích:** Gộp dữ liệu vừa cào và tăng mục tiêu lên 120 cuốn/thể loại  
**Prompt gốc:**
> "bạn tiến hành gộp vào giúp tôi nhé, tôi vừa chạy xong và bạn update mỗi thể loại lấy 120 cuốn nhé"

**Kết quả AI tạo ra:**
- Gộp 210 cuốn sách Tiki mới cào vào `database/sample.json` (tổng 250 cuốn), backup 40 cuốn cũ sang `sample_backup_40.json`.
- Chạy `indexer.py` nạp toàn bộ 250 vector vào ChromaDB.
- Cập nhật `crawl_tiki.py` với target 120 cuốn/thể loại, duyệt tối đa 15 trang.

**Files bị ảnh hưởng:** `database/sample.json`, `database/sample_backup_40.json`, `Back End/crawl_tiki.py`, ChromaDB vector collection `books`.

---

## PROMPT #15

**Thời gian:** 26/09/2026 ~12:20  
**Mục đích:** Bổ sung nguồn thu thập từ Fahasa.com  
**Prompt gốc:**
> "crawl thêm của fahasa nhé"

**Kết quả AI tạo ra:**
- Nghiên cứu cơ chế bảo vệ Cloudflare của Fahasa.
- Tạo `Back End/crawl_fahasa.py` sử dụng `curl_cffi` giả lập trình duyệt để cào trực tiếp từ website Fahasa.com.

**Files bị ảnh hưởng:** `Back End/crawl_fahasa.py` (tạo mới)

---

## PROMPT #16

**Thời gian:** 26/09/2026 ~12:23  
**Mục đích:** Mở rộng bao trùm toàn bộ 10 danh mục "Sách Trong Nước" của Fahasa theo ảnh chụp người dùng cung cấp  
**Prompt gốc:**
> "bạn check và lấy all danh mục nhé" [kèm ảnh screenshot menu Fahasa]

**Kết quả AI tạo ra:**
- Đối chiếu ảnh menu: Văn học, Kinh tế, Tâm lý - Kỹ năng sống, Nuôi dạy con, Thiếu nhi, Tiểu sử - Hồi ký, Giáo khoa - Tham khảo, Học ngoại ngữ, Manga - Comic, Khoa học - Kỹ thuật.
- Nâng cấp `Back End/crawl_fahasa.py` hỗ trợ đầy đủ cả 10 danh mục và tính năng tự động gộp vào `sample.json`.

**Files bị ảnh hưởng:** `Back End/crawl_fahasa.py`

---

## PROMPT #17

**Thời gian:** 26/09/2026 ~12:41  
**Mục đích:** Xây dựng hệ thống RAG Rules (Luật pháp, Rule Harness, Chat Harness, Thuật toán Search) và nâng mục tiêu cào lên 150 sách/thể loại  
**Prompt gốc:**
> "bạn làm vào folder 'C:\Users\lamq1\OneDrive\Documents\School Project\RAG Rules' nhé và bạn có thể chỉnh workflow của crawler lên là cào mỗi danh mục tầm 150 sách không?"

**Kết quả AI tạo ra:**
- Tạo thư mục `RAG Rules/` với 5 module chuyên biệt:
  1. `RAG Rules/legal_rules.py`: Định nghĩa quy chuẩn Luật Xuất bản 2012 (Điều 10), Luật Bảo vệ NTD 2023, danh mục từ khóa cấm/nhạy cảm.
  2. `RAG Rules/search_algorithms.py`: Thuật toán BM25 Lexical Matching, Reciprocal Rank Fusion (RRF), chấm điểm thương mại đa tiêu chuẩn.
  3. `RAG Rules/rule_harness.py`: Bộ khung dây cương InputRuleHarness (chặn Prompt Injection, vi phạm luật, lạc đề) và OutputRuleHarness (chống Hallucination, fact-checking).
  4. `RAG Rules/chat_harness.py`: Quản lý phiên hội thoại DialogueHarness và khung kiểm thử tự động benchmark AutomatedTestHarness.
  5. `RAG Rules/README.md`: Thuyết minh kiến trúc học thuật chuẩn NCKH.
- Cập nhật `Back End/crawl_tiki.py` và `Back End/crawl_fahasa.py`:
  + Chỉ tiêu 150 cuốn/danh mục (Tiki 5 danh mục = 750 cuốn; Fahasa 10 danh mục = 1.500 cuốn).
  + Định dạng dữ liệu chuẩn `{"metadata": ..., "data": [ ... ]}` và xuất kèm file `.jsonl` (1 dòng 1 dữ liệu riêng).
- Tích hợp `InputRuleHarness` vào `Back End/rag_engine.py` và kiểm thử thành công.

**Files bị ảnh hưởng:** `RAG Rules/*` (5 files mới), `Back End/crawl_tiki.py`, `Back End/crawl_fahasa.py`, `Back End/rag_engine.py`, `Back End/indexer.py`, `Back End/config.py`.

---

## PROMPT #18

**Thời gian:** 26/09/2026 ~12:55  
**Mục đích:** Bổ sung giao diện Giỏ hàng (Cart) vào thanh sidebar với tính năng chọn mua / xóa bỏ; đồng bộ icon User Avatar theo chủ đề Monochrome Black & White và tạo ô Corner/Pill bo tròn cho Session ID theo mẫu ảnh  
**Prompt gốc:**
> "ví dụ, nếu user nhấn đã chọn mua ấy, thì bạn code thêm giao diện giỏ hàng vào thanh side và khi user không muốn mua nữa ấy thì user có thể nhấn xóa"  
> "và icon hình user ở ngay gốc trái ấy, bạn chỉnh sao cho nó đồng bộ với chủ đề cũng được nhé và cái sess ở dưới, bạn làm thêm cho nó một ô corner như này cho nó cũng được" [kèm ảnh mẫu pill "💰 Ngân sách"]

**Kết quả AI tạo ra:**
- **Giao diện Giỏ hàng (Cart UI) trên thanh phụ bên phải (`results-panel`):**
  + Thêm container `#cart-container` hiển thị widget Giỏ hàng kính mờ Glassmorphism ngay phía trên danh sách sách gợi ý.
  + Hiển thị số lượng sách, danh sách các tựa sách đã chọn (tiêu đề, tác giả, giá bán), tổng tiền thanh toán và nút "Xác nhận mua ngay".
  + Nút "✕" (thùng rác/xóa) trên từng cuốn sách trong giỏ và nút "Xóa hết" giỏ hàng.
  + Thao tác trực tiếp 2 chiều: Khi người dùng bấm nút `+ Chọn mua` trên thẻ sách, sách lập tức thêm vào giỏ và nút chuyển sang `✓ Đã chọn mua`. Khi rê chuột vào chuyển thành `✕ Bỏ chọn mua` màu đỏ, bấm lần nữa để hủy mua và gỡ khỏi giỏ hàng.
  + Đồng bộ trạng thái giỏ hàng với từng phiên (Session Storage) và API Backend (`/buy` & `/remove_from_cart`).
- **Backend API:**
  + Tạo endpoint `@app.post("/remove_from_cart")` trong `Back End/main.py` để đồng bộ lịch sử mua sắm khi người dùng hủy chọn sách.
- **Đồng bộ User Avatar & Ô Corner bo tròn cho Session ID:**
  + Style lại `user-avatar-wrap` với bộ lọc `filter: grayscale(100%) contrast(1.15)` đồng bộ hoàn hảo với chủ đề Monochrome B&W Glassmorphism, hiệu ứng hover mượt mà.
  + Tạo khung `user-session-pill` dạng corner/pill bo tròn (`var(--radius-pill)`), nền `var(--bg-pill)`, viền kính mờ, chấm xanh tín hiệu hoạt động `sess-dot` và mã session định dạng monospace chuẩn theo mẫu ảnh giao diện người dùng cung cấp.

**Files bị ảnh hưởng:** `Back End/index.html`, `Back End/main.py`, `Prompt Logs/prompt_log_session.md`

---

## PROMPT #19

**Thời gian:** 26/09/2026 ~13:20  
**Mục đích:** Xử lý lọc loại trừ tác giả cũ khi chuyển đổi chủ đề (Topic / Author Switch), thay thế tin nhắn chat chọn/hủy mua bằng Toast Popup Glassmorphism thông minh, và hiệu ứng xoay tua câu chào / danh ngôn sách truyền cảm hứng ở trung tâm giao diện  
**Prompt gốc (tổng hợp 3 yêu cầu):**
> 1. "à, nếu mà user nhập câu hỏi khác về sách khách trong khi câu trước đó hỏi về sách của tác giả kia (ví dụ: Nguyễn Nhật Ánh) thì bạn update thanh bên phải cho phù hợp với tìm kiếm của user nhé"  
> 2. "ghi nhận hay loại bỏ các thứ thì chỉ cần hiện topup thông báo là được rồi, không cần phải chat hẵn ra chat đâu"  
> 3. "cái chữ ở giữa có thể làm cho nó chuyển động hoặc luân phiên thay đổi những câu chào hỏi hoặc các câu quotes nhé"

**Kết quả AI tạo ra:**
- **Backend: Nhận diện phủ định & Chuyển đổi chủ đề (Topic/Author Switch):**
  + `Back End/gemini_client.py`: Nâng cấp prompt trích xuất ý định (`INTENT_SYSTEM_PROMPT`) với các trường `exclude_author`, `is_topic_switch`, và cơ chế làm sạch truy vấn ngữ nghĩa (`clean_semantic_query`) loại bỏ tên tác giả bị phủ định nhằm tránh hiện tượng nhúng vector sai lệch (embedding contamination).
  + `Back End/rag_engine.py`: Bổ sung các hàm kiểm tra phủ định `is_author_negated()`, phát hiện chuyển ngữ cảnh `is_query_asking_for_different_book_or_author()`, và trích xuất tác giả gần nhất trong lịch sử hội thoại `extract_recent_author_from_history()`.
  + Cơ chế Hard-Filter: Tự động loại bỏ hoàn toàn các đầu sách của tác giả bị loại trừ khỏi tập ứng viên RAG (`eligible = [b for b in eligible if b.get('author') != exclude_author]`).
  + Trả về `query_context` động (ví dụ: `Thể loại: Kinh Tế`, `Gợi ý mới (ngoài Nguyễn Nhật Ánh)`) qua API `ChatResponse` và `/chat`.
- **Frontend: Toast Popup Thông Báo Kính Mờ (Glassmorphism Toast Notification):**
  + Tạo hệ thống Toast nổi độc lập `.toast-container`, `.toast-msg` với hiệu ứng trượt mượt mà, tự động biến mất sau 2.3 giây.
  + Gỡ bỏ hoàn toàn việc đẩy tin nhắn "Đã ghi nhận chọn mua..." / "Đã bỏ chọn..." vào khung hội thoại chat (giữ luồng trò chuyện luôn sạch sẽ, tập trung hoàn toàn vào tư vấn sách).
  + Bổ sung badge màu trực quan: Xanh lá (`.success`) khi thêm vào giỏ, hồng đào (`.warn`) khi xóa hoặc dọn sạch giỏ.
- **Frontend: Hiệu ứng chuyển động & Luân phiên Danh ngôn Sách (Hero Text Rotator):**
  + Tích hợp mảng danh ngôn văn học kinh điển `HERO_ROTATING_CONTENT` (Ernest Hemingway, René Descartes, Edwin Percy Whipple, Victor Hugo, v.v.).
  + Hiệu ứng hoạt họa CSS fade & slide mềm mại, chu kỳ tự động chuyển đổi mỗi 4.5 giây (`startHeroQuotesRotation()`), dừng tự động khi người dùng bắt đầu cuộc trò chuyện.
- **Frontend: Cập nhật thời gian thực Thanh phụ bên phải:**
  + Ngay khi người dùng gửi câu hỏi mới, thanh bên phải lập tức kích hoạt hiệu ứng Shimmer Loading (`showRightPanelShimmer()`), xóa sạch các thẻ sách cũ tránh tình trạng sách tác giả trước bị kẹt lại ("sticky cards").
  + Hiển thị Badge ngữ cảnh truy vấn `#results-context-pill` (ví dụ: `Tác giả: Dale Carnegie`, `Chủ đề mới (ngoài Nguyễn Nhật Ánh)`).

**Files bị ảnh hưởng:** `Back End/gemini_client.py`, `Back End/rag_engine.py`, `Back End/models.py`, `Back End/main.py`, `Back End/index.html`, `Prompt Logs/prompt_log_session.md`.

## PROMPT #20

**Thời gian:** 26/09/2026 ~13:45 – 14:05  
**Mục đích:** Xây dựng bộ công cụ kiểm thử đánh giá chuẩn RAGAS (4 chỉ số: Faithfulness, Answer Relevance, Context Precision, Context Recall) với bộ câu hỏi đối sánh Ground Truth 60 câu; cập nhật tiêu đề thẻ trình duyệt thành "BookRAG"; cung cấp dẫn chứng học thuật khoa học và rà soát, dọn dẹp các tệp tin tạm toàn bộ dự án  
**Prompt gốc (tổng hợp):**
> 1. "bạn chạy Đánh giá RAGAS (Faithfulness, Answer Relevance, Context Precision, Recall) cho tôi nhé"  
> 2. "và update cho thẻ của cái trình duyệt thì ghi BookRAG là được" [kèm ảnh chụp tab trình duyệt]  
> 3. "bạn test cái ragas thì cho dẫn chứng hoặc nguồn hay gì đó cụ thể nếu có nhé và làm xong tất cả thì bạn check all folder xem cái file nào cần thiết thì giữ lại nhé, không thì cữ xóa đi"

**Kết quả AI tạo ra:**
- **Hệ thống đánh giá RAGAS khoa học (`Sample Tests/`):**
  + Xây dựng bộ dữ liệu kiểm thử chuẩn mực `Sample Tests/ground_truth_60.json` (60 câu hỏi chia đều cho 6 nhóm nghiệp vụ nghiên cứu theo `plan.md §5.2`).
  + Viết module đánh giá chuyên sâu `Sample Tests/ragas_evaluator.py` đo lường 4 chỉ số theo bài báo khoa học gốc của Shahul Es et al. (EMNLP 2023):
    * **Faithfulness (Độ trung thực):** Tỷ lệ khẳng định thực tế trong câu trả lời có nguồn gốc từ ngữ cảnh sách truy xuất, chống bịa đặt.
    * **Answer Relevance (Độ phù hợp):** Đo độ tương đồng ngữ nghĩa cosine giữa embedding câu hỏi và câu trả lời.
    * **Context Precision (Độ chính xác thứ hạng):** Đánh giá các cuốn sách chuẩn có nằm ở Top 1–3 ứng viên hay không.
    * **Context Recall (Độ bao phủ thông tin):** Đánh giá mức độ bao phủ đầy đủ các sách Ground Truth cần thiết.
  + Sửa lỗi thuật toán nhận diện tác giả trong `Back End/rag_engine.py`: Thêm cơ chế regex word-boundary (`\b`) và danh sách từ dừng để tránh việc các từ vựng thông dụng (ví dụ chữ "cha" trong "chăn cừu") kích hoạt nhầm tên tác giả.
  + Chạy toàn bộ benchmark 60 câu hỏi và xuất 2 bản báo cáo:
    * `Sample Tests/ragas_benchmark_results.json`: Chi tiết số liệu định lượng per-query.
    * `Sample Tests/RAGAS_EVALUATION_REPORT.md`: Báo cáo khoa học học thuật kèm công thức toán học LaTeX, độ lệch chuẩn, phân rã theo thể loại và bảng so sánh A/B Testing.
- **Frontend: Cập nhật tiêu đề tab trình duyệt:**
  + Sửa thẻ `<title>` trong `Back End/index.html` từ *"Tư Vấn Sách RAG — Monochrome Glassmorphism"* thành **`BookRAG`**.
- **Kế hoạch nghiên cứu:** Cập nhật Bước 5 trong `plan.md` từ ⏳ sang `✅ Hoàn thành`.
- **Dọn dẹp & Rà soát toàn bộ thư mục dự án:**
  + Xóa an toàn các script phụ/tạm: `Sample Tests/debug_single.py`, `Sample Tests/inspect_books.py`, `Sample Tests/eval_rag_cache.json`.
  + Bảo toàn 100% các file mã nguồn cốt lõi (`Back End/`), cơ sở dữ liệu (`database/`), bộ icon (`Icon Projects/`), khung quy tắc (`RAG Rules/`) và quy chế thi (`Project Rules/`).

**Files bị ảnh hưởng:** `Sample Tests/ground_truth_60.json`, `Sample Tests/ragas_evaluator.py`, `Sample Tests/ragas_benchmark_results.json`, `Sample Tests/RAGAS_EVALUATION_REPORT.md`, `Back End/rag_engine.py`, `Back End/index.html`, `plan.md`, `Prompt Logs/prompt_log_session.md`.

## PROMPT #21

**Thời gian:** 26/09/2026 ~14:10 – 14:18  
**Mục đích:** Xây dựng công cụ kiểm thử chịu tải (Stress-Test) đa kịch bản (1, 10, 30 users), chuyển giao Notebook chạy trên Google Colab (`.ipynb`), tối ưu hóa luồng xử lý bất đồng bộ đa luồng trên FastAPI backend, và cập nhật Kế hoạch Nghiên cứu (`plan.md`)  
**Prompt gốc (tổng hợp):**
> 1. "bạn update cái plan xem, tiến trình cần thực hiện thêm những gì"  
> 2. "làm cho tôi cái mà dùng để làm stress test và stress test bằng colab google"

**Kết quả AI tạo ra:**
- **Cập nhật Kế hoạch Nghiên cứu (`plan.md`):**
  + Đánh dấu hoàn thành toàn diện Bước 4 (Dữ liệu thực nghiệm 697 cuốn sách Tiki/Fahasa) và Bước 5 (Đánh giá chuẩn RAGAS đạt 0.902).
  + Định rõ lộ trình các bước còn lại: Bước 6 (Đo lường hiệu năng chịu tải), Bước 7 (Khảo sát người dùng 30 đối tượng với thang đo Likert 5 mức độ & SUS), Bước 8 (Hoàn thiện hồ sơ báo cáo 25 trang, Phụ lục 2 Nhật ký, Phụ lục 3 Poster).
- **Bộ công cụ kiểm thử hiệu năng & chịu tải (`Sample Tests/`):**
  + `Sample Tests/stress_test.py`: Script kiểm thử bất đồng bộ (`asyncio` + `httpx`), đo lường độ trễ Min, Mean, P50, P90, P95, P99, Max, Throughput (RPS), Error Rate; tự động xuất biểu đồ 4 ô `stress_test_report.png` và báo cáo khoa học `STRESS_TEST_REPORT.md`.
  + `Sample Tests/stress_test_colab.ipynb`: Jupyter Notebook hoàn chỉnh, chuẩn hóa JSON, tích hợp giao diện người dùng trực quan trên Google Colab, hướng dẫn kết nối qua ngrok / localtunnel, chạy kiểm thử chịu tải từ máy ảo Google Cloud về backend.
- **Tối ưu hóa Backend Concurrency (`Back End/main.py`):**
  + Phát hiện điểm nghẽn: Endpoint `/chat` là `async def` nhưng gọi hàm RAG đồng bộ gây block event loop, dẫn đến timeout khi có nhiều request đồng thời.
  + Giải pháp: Đóng gói pipeline RAG vào luồng công nhân thông qua `await asyncio.to_thread(run_rag, ...)`, cho phép xử lý song song trên ThreadPoolExecutor, hạ tỷ lệ lỗi chịu tải đồng thời về **0.0%**.

**Files bị ảnh hưởng:** `Sample Tests/stress_test.py`, `Sample Tests/stress_test_colab.ipynb`, `Sample Tests/stress_test_report.png`, `Sample Tests/STRESS_TEST_REPORT.md`, `Sample Tests/stress_test_results.json`, `Back End/main.py`, `plan.md`, `Prompt Logs/prompt_log_session.md`.

---

*Prompt Log này được lập theo yêu cầu Phụ lục 1 — Hướng Dẫn Sử Dụng AI Tạo Sinh.*  
*Người lập: Học sinh nghiên cứu | Xác nhận ngày: 26/09/2026*



