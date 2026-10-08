# BỘ HỒ SƠ KHẢO SÁT NGƯỜI DÙNG THỰC TẾ (USER USABILITY & RAG EXPERIENCE SURVEY)

**Đề tài NCKH 2026-2027:** Hệ Thống Tư Vấn Sách Tự Động Sử Dụng RAG Nhằm Giảm Sai Lệch Thông Tin Và Gợi Ý Theo Nhu Cầu Người Dùng  
**Lĩnh vực:** Hệ thống phần mềm (Software Systems)  
**Tiêu chuẩn áp dụng:** Thang đo chuẩn quốc tế SUS (System Usability Scale, Brooke, 1996) kết hợp thang đo Likert 5 mức độ đánh giá hệ thống RAG.

---

## 1. Kế Hoạch Và Kịch Bản Thực Nghiệm (Survey Protocol)

### 1.1 Mục tiêu khảo sát
1. Đánh giá tính khả dụng, độ thân thiện và trải nghiệm người dùng của hệ thống qua thang đo chuẩn SUS (mục tiêu đạt điểm $\ge 80/100$).
2. Đo lường sự tin cậy của độc giả đối với khả năng cung cấp thông tin chính xác và tính năng tìm sách qua mô tả cốt truyện.
3. Đánh giá tính hữu ích thực tế của tính năng gợi ý các tác phẩm của cùng tác giả sau khi chọn mua.

### 1.2 Đối tượng và mẫu khảo sát ($N = 30$)
- **Quy mô mẫu:** 30 người dùng độc lập, gồm:
  - **18 Học sinh THPT:** Người đọc trẻ tuổi, có nhu cầu tìm tiểu thuyết, truyện thanh thiếu niên và sách kỹ năng.
  - **6 Giáo viên:** Độc giả có nhu cầu tìm sách chuyên môn, văn học kinh điển và sách giáo dục.
  - **6 Phụ huynh học sinh:** Độc giả có nhu cầu tìm sách cho con em theo độ tuổi và ngân sách.

### 1.3 Quy trình thực nghiệm
1. **Giai đoạn 1 (Làm quen, 3 phút):** Người dùng truy cập giao diện web tại `http://localhost:8000/` và xem qua hướng dẫn cơ bản.
2. **Giai đoạn 2 (Thực hiện 4 nhiệm vụ tìm sách, 10 phút):**
   - **Nhiệm vụ 1 (Tìm qua cốt truyện):** Nhập 1 câu hỏi chỉ nhớ chi tiết nội dung (ví dụ: "Tôi nhớ có cuốn sách kể về cậu bé chăn cừu đi tìm kho báu ở kim tự tháp").
   - **Nhiệm vụ 2 (Tìm theo thể loại và ngân sách):** Nhập yêu cầu tìm sách theo chủ đề kèm mức giá (ví dụ: "Sách tâm lý học dễ hiểu giá dưới 100k").
   - **Nhiệm vụ 3 (Trải nghiệm gợi ý cùng tác giả):** Nhấn nút `+ Chọn mua` một cuốn sách và quan sát danh sách các tác phẩm cùng tác giả được đề xuất thêm.
   - **Nhiệm vụ 4 (Kiểm tra câu hỏi bẫy):** Đặt câu hỏi về sách không có thật hoặc kết hợp sai tác giả (ví dụ: "Tìm sách làm giàu trong 3 ngày của Murakami") để quan sát phản hồi của hệ thống.
3. **Giai đoạn 3 (Điền phiếu khảo sát, 5 phút):** Điền vào biểu mẫu đánh giá gồm 10 câu SUS và 5 câu hỏi chuyên sâu về RAG.

---

## 2. Bảng Câu Hỏi Chuẩn SUS (System Usability Scale, 10 Câu)

Thang đo: **1 = Hoàn toàn không đồng ý** đến **5 = Hoàn toàn đồng ý**.

| Mã | Nội dung câu hỏi (Tiếng Việt) | Tính chất |
|:---:|---|:---:|
| **SUS 1** | Tôi nghĩ rằng tôi sẽ muốn sử dụng hệ thống tư vấn sách này thường xuyên khi có nhu cầu tìm sách. | Thuận |
| **SUS 2** | Tôi thấy giao diện và quy trình sử dụng hệ thống này phức tạp không cần thiết. | Nghịch |
| **SUS 3** | Tôi thấy hệ thống dễ sử dụng ngay từ lần đầu tiên trải nghiệm. | Thuận |
| **SUS 4** | Tôi nghĩ rằng mình sẽ cần sự hỗ trợ của người am hiểu kỹ thuật để có thể sử dụng được hệ thống này. | Nghịch |
| **SUS 5** | Tôi nhận thấy các tính năng của hệ thống (hội thoại, hiển thị giỏ hàng, thông tin độ khớp) được tích hợp gắn kết. | Thuận |
| **SUS 6** | Tôi cảm thấy có những điểm thiếu nhất quán trong hệ thống này. | Nghịch |
| **SUS 7** | Tôi nghĩ rằng hầu hết mọi người sẽ làm quen với hệ thống này nhanh chóng. | Thuận |
| **SUS 8** | Tôi thấy hệ thống này khá rườm rà khi thao tác tìm kiếm sách. | Nghịch |
| **SUS 9** | Tôi cảm thấy tự tin khi thao tác trên hệ thống. | Thuận |
| **SUS 10** | Tôi cần phải học hỏi thêm nhiều điều trước khi có thể sử dụng thành thạo hệ thống này. | Nghịch |

> **Công thức tính điểm SUS (Brooke, 1996):**
> - Đối với câu thuận ($i = 1, 3, 5, 7, 9$): Điểm đóng góp = $X_i - 1$
> - Đối với câu nghịch ($i = 2, 4, 6, 8, 10$): Điểm đóng góp = $5 - X_i$
> - **Điểm SUS tổng thể** = $\left(\sum_{i=1}^{10} \text{Điểm đóng góp}_i\right) \times 2.5 \in [0, 100]$
> - Thang phân loại: $\ge 80.3$ thuộc Hạng A (Grade A, mức Best Imaginable); $\ge 68.0$ đạt mức trung bình chuẩn.

---

## 3. Bảng Câu Hỏi Likert 5 Mức Độ Về Tính Năng RAG (5 Câu)

| Mã | Khía cạnh đánh giá | Nội dung câu hỏi | Thang điểm |
|:---:|---|---|:---:|
| **RAG 1** | Tìm theo mô tả nội dung | Hệ thống nhận diện và gợi ý đúng cuốn sách tôi cần khi tôi chỉ miêu tả chi tiết cốt truyện. | 1 đến 5 |
| **RAG 2** | Gợi ý theo tác giả | Tính năng gợi ý thêm các tác phẩm của cùng tác giả sau khi tôi chọn mua sách hữu ích và phù hợp. | 1 đến 5 |
| **RAG 3** | Độ tin cậy thông tin | Tôi tin tưởng vào tính xác thực của thông tin sách (tác giả, giá niêm yết, nhà xuất bản), không gặp hiện tượng AI tự tạo thông tin. | 1 đến 5 |
| **RAG 4** | Minh bạch thuật toán | Việc hệ thống hiển thị điểm số Match % giúp tôi hiểu rõ lý do cuốn sách được gợi ý. | 1 đến 5 |
| **RAG 5** | So sánh với AI thuần | Tôi thấy hệ thống này cung cấp thông tin đáng tin cậy hơn so với việc hỏi các Chatbot thông thường không kết nối dữ liệu. | 1 đến 5 |

---

## 4. Thiết Lập Biểu Mẫu Khảo Sát

Các câu hỏi được thiết lập theo thang điểm tuyến tính từ 1 đến 5:
- 1: Hoàn toàn không đồng ý
- 5: Hoàn toàn đồng ý
- Dữ liệu thu thập được xuất sang file định dạng `.csv` lưu tại `Sample Tests/survey_responses.csv`.

Mã nguồn phân tích tự động tại `Sample Tests/survey_analyzer.py` sẽ tính toán các chỉ số thống kê (Mean, Std, Cronbach's Alpha, SUS Score) để đưa vào báo cáo nghiên cứu khoa học.
