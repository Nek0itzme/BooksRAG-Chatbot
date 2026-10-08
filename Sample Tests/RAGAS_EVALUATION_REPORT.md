# Báo Cáo Đánh Giá RAGAS (Retrieval Augmented Generation Assessment)
### Hệ Thống Tư Vấn Sách Tự Động Sử Dụng RAG Nhằm Giảm Sai Lệch Thông Tin Và Gợi Ý Theo Nhu Cầu Người Dùng

- **Đơn vị nghiên cứu:** Trường THPT Nguyễn Hữu Thọ, TP. Hồ Chí Minh  
- **Cuộc thi:** Cuộc thi NCKH KHKT dành cho học sinh trung học năm học 2026-2027  
- **Lĩnh vực:** Hệ thống phần mềm (Systems Software)  
- **Quy mô mẫu kiểm định:** 60 câu hỏi Ground Truth chia theo 6 nhóm nghiệp vụ  
- **Khung lý thuyết đối sánh:** Chuẩn RAGAS (Shahul Es et al., 2023)  

---

## 1. Kết Quả Đo Lường 4 Chỉ Số RAGAS (Đợt 1 Baseline vs Đợt 2 Post-Optimization)

Sau khi hoàn thành đợt kiểm thử đợt 1 (Baseline), nhóm nghiên cứu đã phân tích các trường hợp phát sinh lỗi và áp dụng 3 giải pháp kỹ thuật:
1. **Query Expansion kết hợp bảng ánh xạ khái niệm (`CATEGORY_CONCEPT_MAP`):** Kết nối các cách diễn đạt thông thường (ví dụ: "quà 18 tuổi", "học quản trị tiền bạc") với danh mục sách tương ứng ("Kinh tế", "Kỹ năng sống").
2. **Xử lý ranh giới từ bằng Word Boundary Regex (`\b`):** Ngăn chặn việc từ khóa "6 tuổi" bị khớp nhầm vào "16 tuổi", bảo đảm phân loại đúng độ tuổi.
3. **Áp dụng Strict Grounding và bổ sung Guardrails kiểm soát nội dung:** Mở rộng danh mục lọc theo Điều 10 Luật Xuất bản 2012 và quy định an toàn thông tin.

### Bảng Tổng Hợp 4 Chỉ Số RAGAS:

| Chỉ số RAGAS | Định nghĩa toán học | Đợt 1 (Mức cơ sở) | Đợt 2 (Sau tối ưu) | Mục tiêu đề ra | Chênh lệch ($\Delta$) | Đánh giá |
|---|---|---|---|---|---|---|
| **Context Precision** | $\frac{\sum_{k=1}^K (P@k \times v_k)}{\sum v_k}$ | 0.980 | **0.985** (±0.04) | $\ge 0.80$ | $+0.5\%$ | Đạt mục tiêu |
| **Context Recall** | $\frac{\|G \cap C\|}{\|G\|}$ | 0.751 | **0.885** (±0.06) | $\ge 0.85$ | **$+13.4\%$** | Đạt mục tiêu |
| **Faithfulness** | $\frac{\|S_{\text{supported}}\|}{\|S_{\text{total}}\|}$ | 0.834 | **0.940** (±0.05) | $\ge 0.90$ | **$+10.6\%$** | Đạt mục tiêu |
| **Answer Relevance** | $\frac{1}{N} \sum_{i=1}^N \cos(E_q, E_a)$ | 0.885 | **0.890** (±0.04) | $\ge 0.85$ | $+0.5\%$ | Đạt mục tiêu |

> **Điểm trung bình điều hòa RAGAS:**  
> $$\text{RAGAS Score} = \frac{4}{\frac{1}{0.985} + \frac{1}{0.885} + \frac{1}{0.940} + \frac{1}{0.890}} = \mathbf{0.924 / 1.000}$$  
> Kết quả đánh giá vượt ngưỡng mục tiêu 0.85 đề ra trong kế hoạch nghiên cứu.

---

## 2. Phân Tích Hiệu Năng Vận Hành Và Bộ Nhớ Đệm (Latency & Semantic Cache)

| Chỉ số hiệu năng | Không dùng Cache (gọi API) | Có Semantic Cache (Hit) | Guardrails Rule Harness (Chặn yêu cầu xấu) |
|---|---|---|---|
| **Độ trễ phản hồi** | Khoảng 7,780 ms | **1.8 ms** (truy xuất từ RAM Cache) | **0.4 ms** (Regex O(1) in-memory) |
| **Thời gian tìm kiếm nội bộ** | 42.5 ms (ChromaDB + Hybrid Score) | - | - |
| **Mức giảm lượt gọi LLM** | 0% | **100% cho các truy vấn lặp lại** | **100% (xử lý trực tiếp không qua LLM)** |
| **Thông lượng ước tính** | ~1.5 req/s (giới hạn Free Tier) | **> 1,200 req/s** | **> 5,000 req/s** |

---

## 3. Bảng Chi Tiết Theo 6 Nhóm Câu Hỏi Nghiên Cứu (Đợt 2)

| STT | Phân nhóm nghiệp vụ | Số câu | Precision | Recall | Faithfulness | Relevance | Nhận xét |
|---|---|---|---|---|---|---|---|
| 1 | Nhớ mang máng cốt truyện | 12 | 0.980 | 0.892 | 0.950 | 0.960 | Không gian vector 384 chiều khớp tốt với nội dung mô tả |
| 2 | Gợi ý cùng tác giả sau khi mua | 10 | 1.000 | 0.900 | 0.960 | 0.930 | Bộ lọc tác giả truy vấn chính xác danh mục tác phẩm |
| 3 | Lọc theo thể loại và ngân sách | 10 | 1.000 | 0.910 | 0.940 | 0.850 | Hệ số phạt $P_{\text{price}}$ loại bỏ các sách vượt mức giá |
| 4 | Tìm theo tâm trạng hoặc cảm xúc | 10 | 0.970 | 0.860 | 0.930 | 0.870 | Query Expansion mở rộng được các từ khóa đồng nghĩa |
| 5 | Tìm theo độ tuổi tặng quà | 10 | 0.980 | 0.870 | 0.920 | 0.860 | Xử lý tốt ranh giới từ, phân biệt đúng 6 tuổi và 16 tuổi |
| 6 | Câu hỏi bẫy và kiểm tra an toàn | 8 | 1.000 | 1.000 | 0.960 | 0.910 | Chặn kịp thời prompt injection và yêu cầu không phù hợp |

---

## 4. Đối Sánh Thử Nghiệm A/B

| Tiêu chí | Hệ thống đối chứng A (LLM thuần) | Hệ thống thực nghiệm B (RAG đề tài) | Nhận xét |
|---|---|---|---|
| **Faithfulness (Trung thực)** | 0.520 (thường tự tạo tên tác phẩm hoặc giá bán) | **0.940 (gắn với kho 697 cuốn sách thật)** | Giảm thiểu rủi ro cung cấp thông tin sai lệch |
| **Độ phủ danh mục (Recall)** | 0.450 (chủ yếu nhớ các tác phẩm rất phổ biến) | **0.885 (bao quát các đầu sách trong kho)** | Tìm được các đầu sách ít phổ biến hơn |
| **Kiểm soát nội dung và an toàn** | Dễ bị dẫn dắt bởi các câu hỏi prompt injection | **Nhận diện và xử lý từ chối trong 0.4 ms** | Đảm bảo an toàn thông tin theo quy định |
| **Tối ưu tài nguyên API** | Tất cả câu hỏi đều gửi lên dịch vụ đám mây | **Giảm 35-50% số lượt gọi nhờ Semantic Cache** | Giúp hệ thống hoạt động ổn định hơn |

---

## 5. Kết Luận

1. Hệ thống đạt cả 4 chỉ số RAGAS đặt ra trong kế hoạch nghiên cứu: Context Precision ($0.985 \ge 0.80$), Context Recall ($0.885 \ge 0.85$), Faithfulness ($0.940 \ge 0.90$), Answer Relevance ($0.890 \ge 0.85$).
2. Mô hình xếp hạng lai kết hợp Vector Embedding và các tiêu chí thương mại đem lại kết quả phù hợp hơn so với tìm kiếm từ khóa đơn lẻ hoặc mô hình ngôn ngữ không có dữ liệu đối chiếu.
3. Số liệu đánh giá có thể kiểm tra độc lập thông qua tệp kịch bản `Sample Tests/ground_truth_60.json`.
