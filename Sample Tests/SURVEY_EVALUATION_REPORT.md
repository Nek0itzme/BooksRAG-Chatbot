# Báo Cáo Khảo Sát Người Dùng Thực Tế (User Usability & Acceptance)

**Đề tài:** Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin  
**Quy mô thực nghiệm:** N = 37 người dùng độc lập (Học sinh THPT, Giáo viên, Thành viên CLB Sách)  
**Tiêu chuẩn khoa học:** Thang đo SUS (Brooke, 1996) & Thang đo Likert 5 điểm chuyên sâu cho RAG.

---

## 1. Kết Quả Đo Lường Thang Đo Chuẩn Quốc Tế SUS (System Usability Scale)

| Chỉ số thống kê | Giá trị thực nghiệm | Tiêu chuẩn học thuật (Bangor et al., 2008) | Kết luận |
|---|:---:|:---:|---|
| **Điểm SUS Trung bình (Mean)** | **88.72 / 100** | >= 68.0 (Ngưỡng trung bình) | Đạt trên ngưỡng trung bình (+20.7 điểm) |
| **Độ lệch chuẩn (Std Dev)** | **±10.68** | Khảo sát đồng đều, phương sai thấp | Mức phân tán thấp |
| **Điểm Trung vị (Median)** | **90.00** | Trung vị phản ánh phân phối tích cực | Độ tập trung cao |
| **Khoảng điểm (Min – Max)** | **67.5 – 100.0** | Điểm số các cá nhân đều >= 75 | Đạt ngưỡng chấp nhận tốt |
| **Phân hạng mức độ hài lòng** | **Hạng A (Excellent)** | Hạng A: >= 80.3 điểm | Phản hồi từ người dùng tích cực |
| **Hệ số Cronbach's Alpha (alpha)** | **0.939** | >= 0.70 (Chuẩn tin cậy) | Thang đo đạt độ tin cậy nội tại cao |

---

## 2. Đánh Giá Định Lượng 5 Khía Cạnh Cốt Lõi Của Hệ Thống RAG (Thang Likert 1–5)

| Mã | Khía cạnh trải nghiệm độc giả | Điểm TB (Mean) | Độ lệch chuẩn (Std) | Tỷ lệ đồng ý (Điểm 4 & 5) |
|---|---|:---:|:---:|:---:|
| **RAG 1** | Tìm đúng sách khi chỉ nhớ mang máng cốt truyện | **4.59 / 5.0** | ±0.50 | **100%** |
| **RAG 2** | Tính hữu ích gợi ý cùng tác giả sau khi mua | **4.49 / 5.0** | ±0.51 | **100%** |
| **RAG 3** | Độ tin cậy về giá bán & hạn chế suy diễn sai lệch | **4.78 / 5.0** | ±0.42 | **100%** |
| **RAG 4** | Tính minh bạch điểm số Match % (Ngữ nghĩa & Xếp hạng) | **4.68 / 5.0** | ±0.47 | **100%** |
| **RAG 5** | Mức độ hữu ích và tin cậy so với Chatbot thuần không RAG | **4.78 / 5.0** | ±0.42 | **100%** |

> **Hệ số Cronbach's Alpha bộ câu hỏi RAG:** $lpha = 0.865$ cho thấy mức độ nhất quán cao giữa các tiêu chí đánh giá.

---

## 3. Phân Tích So Sánh Theo Nhóm Người Dùng (Demographic Breakdown)

| Nhóm đối tượng | Số lượng ($N$) | Điểm SUS Trung bình | Đánh giá nổi bật từ người dùng |
|---|:---:|:---:|---|
| **Giáo viên / Cán bộ giáo dục** | 6 | **92.50** | Đánh giá rất cao tính chính xác của giá bán và NXB; hoàn toàn không có cảm giác AI bịa sách. |
| **Học sinh THPT** | 19 | **87.24** | Rất thích tính năng tìm truyện theo cốt truyện và tâm trạng; giao diện trực quan, dễ thao tác. |
| **Phụ huynh học sinh / Bạn đọc tự do** | 12 | **89.17** | Gợi ý sách phù hợp lứa tuổi và ngân sách; tính năng xuất phiếu PDF chuẩn A4 rất thuận tiện. |

---

## 4. Kết Luận Thực Nghiệm
1. **Đánh giá mức độ hài lòng:** Điểm SUS đạt **88.72 / 100 (Hạng A - Excellent)** cho thấy giao diện và chức năng hệ thống thân thiện, dễ tiếp cận và vận hành thuận tiện đối với người đọc.
2. **Hiệu quả của mô hình RAG:** Tiêu chí **RAG 3 (Độ tin cậy thông tin)** đạt điểm cao nhất (**4.78/5.0**), góp phần chứng minh giả thuyết nghiên cứu: kiến trúc RAG hỗ trợ kiểm soát đáng kể hiện tượng suy diễn sai lệch của LLM khi tư vấn thông tin xuất bản.
