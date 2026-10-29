# Báo cáo khảo sát trải nghiệm người dùng thực tế

Đề tài: Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin và hỗ trợ học tập  
Quy mô mẫu: N = 38 phản hồi thu thập từ Google Form (37 mẫu chuẩn hóa đưa vào tính toán thống kê chi tiết)  
Tiêu chuẩn đo lường: Thang đo System Usability Scale (Brooke, 1996) kết hợp thang đo Likert 5 mức độ chuyên sâu cho mô hình RAG.

---

## 1. Kết quả đo lường thang đo chuẩn quốc tế SUS

| Chỉ số thống kê | Giá trị thực nghiệm | Tiêu chuẩn học thuật (Bangor et al., 2008) | Kết luận |
|---|:---:|:---:|---|
| Điểm SUS trung bình (Mean) | 88.72 / 100 | >= 68.0 (Ngưỡng trung bình) | Vượt chuẩn trung bình 20.72 điểm |
| Độ lệch chuẩn (Std Dev) | +-10.68 | Phương sai thấp | Mức phân tán dữ liệu hẹp |
| Điểm trung vị (Median) | 90.00 | Phân phối tập trung mức cao | Đa số người dùng đánh giá rất tốt |
| Khoảng điểm (Min - Max) | 67.5 đến 100.0 | Hầu hết cá nhân đều đạt >= 75 | Đạt ngưỡng chấp nhận tốt |
| Phân hạng mức độ hài lòng | Hạng A (Xuất sắc) | Hạng A: >= 80.3 điểm | Mức Grade A theo thang Bangor |
| Hệ số Cronbach's Alpha | 0.939 | >= 0.70 (Chuẩn tin cậy) | Thang đo đạt độ tin cậy nội tại cao |

---

## 2. Đánh giá định lượng 5 khía cạnh cốt lõi của mô hình RAG

| Mã | Khía cạnh trải nghiệm độc giả | Điểm trung bình | Độ lệch chuẩn | Tỷ lệ đồng ý (điểm 4 và 5) |
|---|---|:---:|:---:|:---:|
| RAG 1 | Tìm đúng sách khi chỉ nhớ mang máng cốt truyện | 4.59 / 5.0 | +-0.50 | 100% |
| RAG 2 | Tính hữu ích khi gợi ý cùng tác giả sau khi mua | 4.49 / 5.0 | +-0.51 | 100% |
| RAG 3 | Độ tin cậy về giá bán và hạn chế suy diễn sai lệch | 4.78 / 5.0 | +-0.42 | 100% |
| RAG 4 | Tính minh bạch điểm số Match % (Ngữ nghĩa và Xếp hạng) | 4.68 / 5.0 | +-0.47 | 100% |
| RAG 5 | Mức độ hữu ích và tin cậy so với Chatbot thuần không RAG | 4.78 / 5.0 | +-0.42 | 100% |

Hệ số tin cậy nội tại của bộ 5 câu hỏi đánh giá tính năng RAG đạt $\alpha = 0.865$, phản ánh tính nhất quán cao giữa các tiêu chí đo lường.

---

## 3. Phân tích chi tiết theo nhóm người dùng

Dữ liệu khảo sát ghi nhận 3 nhóm đối tượng thực tế:

| Nhóm đối tượng | Số lượng | Điểm SUS trung bình | Đánh giá nổi bật từ người dùng |
|---|:---:|:---:|---|
| Giáo viên và cán bộ giáo dục | 6 | 92.50 | Đánh giá cao tính xác thực của giá bán, nhà xuất bản và tính năng tự động tạo đề trắc nghiệm từ tài liệu chuyên môn. |
| Phụ huynh học sinh và bạn đọc tự do | 12 | 89.17 | Hài lòng với gợi ý sách phù hợp lứa tuổi và ngân sách, hạn chế tình trạng mua nhầm sách không phù hợp. |
| Học sinh THPT | 20 | 87.24 | Thích thú với tính năng tìm sách qua cốt truyện mang máng, khả năng hiểu ngôn ngữ teencode học trò và giao diện dễ thao tác. |

---

## 4. Phân tích phản hồi định tính từ dữ liệu khảo sát gốc

Phân tích từ 38 câu trả lời chi tiết (`raw_google_form_survey_responses.csv`) cho thấy:

1. Về độ tin cậy của mô hình RAG:
   * 28.9% (11/38 người) khẳng định hệ thống cung cấp thông tin sách đáng tin cậy hơn hẳn so với việc hỏi các Chatbot AI thông thường không có kho dữ liệu.
   * 26.3% (10/38 người) tin tưởng vào tính xác thực của thông tin sách (tác giả, giá bìa niêm yết, nhà xuất bản), ghi nhận không thấy hiện tượng AI tự tạo sách không có thật.
   * 21.1% (8/38 người) đánh giá cao việc hệ thống minh bạch điểm số Match %, giúp người đọc hiểu rõ cơ sở gợi ý.
   * 13.2% (5/38 người) đánh giá cao khả năng truy tìm sách khi chỉ nhớ các chi tiết rời rạc của cốt truyện.
   * 10.5% (4/38 người) ghi nhận sự tiện lợi của tính năng tự động đề xuất tác phẩm cùng tác giả.

2. Về trải nghiệm tương tác (SUS):
   * 21.1% (8/38 người) nhận xét các tính năng hội thoại, hiển thị giỏ sách và thông tin độ khớp được tích hợp rất gắn kết.
   * 18.4% (7/38 người) đánh giá hệ thống dễ làm quen nhanh chóng.
   * 18.4% (7/38 người) bày tỏ mong muốn sử dụng hệ thống thường xuyên trong việc học tập và tra cứu sách.

---

## 5. Kết luận thực nghiệm

1. Điểm SUS tổng thể đạt 88.72 / 100 (Hạng A), chứng minh giao diện và quy trình vận hành của hệ thống đạt mức độ khả dụng cao đối với cả học sinh, giáo viên và phụ huynh.
2. Tiêu chí RAG 3 (Độ tin cậy thông tin) đạt 4.78 / 5.0, khẳng định giải pháp kết hợp kiểm soát hai đầu (Rule Harness) và cơ sở dữ liệu đối chiếu giúp loại bỏ hiệu quả hiện tượng bịa đặt thông tin của mô hình ngôn ngữ lớn.
