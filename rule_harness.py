# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
rule_harness.py — Bộ khung "dây cương" quy tắc (Rule Harness) kiềm chế và định hướng AI
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Bao gồm 2 thành phần chính:
1. InputRuleHarness: Kiểm duyệt câu hỏi người dùng trước khi đi vào LLM/RAG (Chặn Prompt Injection, Pháp lý, Ngoài luồng).
2. OutputRuleHarness: Kiểm chứng câu trả lời của AI trước khi hiển thị (Fact-checking, Chống Hallucination, Minh bạch giá).
"""

import re
from typing import Dict, Any, List
try:
    from legal_rules import check_query_legal_safety, verify_answer_compliance
except ImportError:
    from .legal_rules import check_query_legal_safety, verify_answer_compliance


# ── MẪU CÂU PHÁT HIỆN TẤN CÔNG BẺ KHÓA (PROMPT INJECTION / JAILBREAK) ────────────
INJECTION_PATTERNS = [
    r"hãy quên (hết|tất cả) các (chỉ dẫn|hướng dẫn|lệnh)",
    r"bỏ qua\s+(mọi|hết|tất cả)?\s*(quy tắc|hệ thống|luật|chỉ dẫn|lệnh|giới hạn)",
    r"ignore\s+(all|previous)\s+instructions",
    r"you are now\s+(dan|unrestricted)",
    r"từ giờ bạn là",
    r"đóng vai\s+(một\s+)?(hacker|dan|ai đó không có quy tắc|tội phạm)",
    r"xâm nhập\s+(máy chủ|hệ thống|ngân hàng|server)",
    r"viết code\s+(xâm nhập|hack|tấn công|đánh cắp)",
    r"system override",
    r"prompt leak",
]

# ── CÁC CHỦ ĐỀ NGOÀI LUỒNG HOÀN TOÀN (OUT OF DOMAIN - OOD) ────────────────────────
OUT_OF_DOMAIN_PATTERNS = [
    r"thời tiết hôm nay",
    r"giải phương trình",
    r"viết code python giúp tôi",
    r"chứng khoán hôm nay tăng hay giảm",
    r"soi cầu lô đề",
    r"dự đoán bóng đá",
]


class InputRuleHarness:
    """Kiểm tra và tiền xử lý câu hỏi của người dùng trước khi chuyển tới RAG."""

    @staticmethod
    def evaluate(query: str) -> Dict[str, Any]:
        result = {
            "passed": True,
            "reason": None,
            "action": "PROCEED",  # PROCEED | REJECT | WARN
            "response": None,
        }

        if not query or len(query.strip()) < 2:
            result["passed"] = False
            result["reason"] = "QUERY_TOO_SHORT"
            result["action"] = "REJECT"
            result["response"] = "Xin chào! Bạn vui lòng nhập tên sách, tác giả hoặc mô tả nội dung cuốn sách bạn đang tìm kiếm nhé."
            return result

        # 1. Kiểm tra An toàn Pháp lý (Luật Xuất bản)
        legal_check = check_query_legal_safety(query)
        if not legal_check["is_safe"]:
            result["passed"] = False
            result["reason"] = f"LEGAL_VIOLATION:{legal_check['violation_type']}"
            result["action"] = "REJECT"
            result["response"] = legal_check["refusal_message"]
            return result

        # 2. Kiểm tra Prompt Injection
        for pat in INJECTION_PATTERNS:
            if re.search(pat, query, re.IGNORECASE):
                result["passed"] = False
                result["reason"] = "PROMPT_INJECTION_DETECTED"
                result["action"] = "REJECT"
                result["response"] = "⚠️ Yêu cầu không hợp lệ. Hệ thống được thiết lập chuyên biệt để tư vấn thông tin sách và bảo vệ tính an toàn dữ liệu."
                return result

        # 3. Kiểm tra Out-of-Domain (Hỏi lạc đề hoàn toàn)
        for pat in OUT_OF_DOMAIN_PATTERNS:
            if re.search(pat, query, re.IGNORECASE):
                result["passed"] = False
                result["reason"] = "OUT_OF_DOMAIN"
                result["action"] = "REJECT"
                result["response"] = "Tôi là trợ lý AI chuyên về tư vấn và gợi ý sách. Bạn có thể hỏi tôi về các tác phẩm văn học, kỹ năng, kinh tế hoặc tìm sách theo cảm xúc nhé!"
                return result

        return result


class OutputRuleHarness:
    """Hậu kiểm duyệt câu trả lời của AI nhằm loại trừ hoàn toàn việc bịa thông tin."""

    @staticmethod
    def verify(answer: str, retrieved_books: List[dict]) -> Dict[str, Any]:
        issues = []
        is_grounded = True

        # 1. Kiểm tra tuân thủ pháp lý của câu trả lời
        compliance = verify_answer_compliance(answer, retrieved_books)
        if not compliance["compliant"]:
            issues.extend(compliance["issues"])

        # 2. Fact-Checking: Kiểm tra tên sách trong câu trả lời có thuộc kho sách thật không
        # Nếu AI gợi ý sách mà trong retrieved_books không hề có cuốn nào
        valid_titles = [b.get("title", "").lower() for b in retrieved_books]
        
        # Nếu RAG không tìm thấy sách trong kho nhưng AI vẫn tự tiện giới thiệu tên sách lạ
        if not retrieved_books and any(k in answer.lower() for k in ["cuốn sách này", "tác phẩm", "giá bán:"]):
            issues.append("Cảnh báo: AI có dấu hiệu tự sinh nội dung sách khi kho dữ liệu rỗng.")
            is_grounded = False

        # 3. Chống bịa đặt giá tiền
        # Kiểm tra nếu AI báo giá sai lệch quá lớn so với giá thật trong retrieved_books
        known_prices = [b.get("price", 0) for b in retrieved_books if b.get("price")]
        if known_prices:
            # Phát hiện các con số dạng xxx.000 trong bài
            raw_nums = re.findall(r"\b(\d{2,3})[.,](\d{3})\b", answer)
            for part1, part2 in raw_nums:
                val = int(f"{part1}{part2}")
                # Nếu giá đưa ra không khớp với bất kỳ cuốn sách nào trong context (sai số > 10%)
                matched_price = any(abs(val - kp) / kp < 0.1 for kp in known_prices if kp > 0)
                if not matched_price and val > 10000:
                    issues.append(f"Mức giá {val:,}đ trong câu trả lời có thể không khớp chính xác với dữ liệu kho.")

        return {
            "verified": len(issues) == 0,
            "is_grounded": is_grounded,
            "issues": issues,
            "books_audited": len(retrieved_books)
        }
