# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
rule_harness.py — Bộ khung "dây cương" quy tắc (Rule Harness) kiểm chế và định hướng AI
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Bao gồm 2 thành phần chính:
1. InputRuleHarness: Kiểm duyệt câu hỏi người dùng trước khi đi vào LLM/RAG (Chặn Prompt Injection, Pháp lý, Ngoài luồng).
2. OutputRuleHarness: Kiểm chứng câu trả lời của AI trước khi hiển thị (Fact-checking, Chống Hallucination, Minh bạch giá).
"""

import sys
from pathlib import Path
import re
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent))
from legal_rules import check_query_legal_safety, verify_answer_compliance


# Pre-compile tất cả regex injection patterns — compile 1 lần khi load module, không re-compile mỗi request
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"hãy quên (hết|tất cả) các (chỉ dẫn|hướng dẫn|lệnh)",
    r"bỏ qua\s+(mọi|hết|tất cả)?\s*(quy tắc|hệ thống|luật|chỉ dẫn|lệnh|giới hạn)",
    r"ignore\s+.{0,30}?\binstructions\b",
    r"you are now\s+(dan|unrestricted)",
    r"từ giờ bạn là",
    r"đóng vai\s+(một\s+)?(hacker|dan|ai đó không có quy tắc|tội phạm)",
    r"xâm nhập\s+(máy chủ|hệ thống|ngân hàng|server)",
    r"viết code\s+(xâm nhập|hack|tấn công|đánh cắp)",
    r"system override",
    r"prompt leak",
]]

_OOD_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"thời tiết hôm nay",
    r"giải phương trình",
    r"viết code python giúp tôi",
    r"chứng khoán hôm nay tăng hay giảm",
    r"soi cầu lô đề",
    r"dự đoán bóng đá",
]]

# Pre-compile regex phát hiện số tiền trong câu trả lời (OutputRuleHarness)
_PRICE_NUM_RE = re.compile(r"\b(\d{2,3})[.,](\d{3})\b")


class InputRuleHarness:
    """Bộ kiểm soát câu hỏi đầu vào của người dùng trước khi chuyển tới RAG."""

    @staticmethod
    def evaluate(query: str) -> Dict[str, Any]:
        result = {
            "passed": True,
            "reason": None,
            "action": "PROCEED",
            "response": None,
        }

        # 1. Kiểm tra câu hỏi quá ngắn
        if not query or len(query.strip()) < 2:
            result["passed"] = False
            result["reason"] = "QUERY_TOO_SHORT"
            result["action"] = "REJECT"
            result["response"] = "Xin chào bạn, vui lòng nhập tên tác phẩm, tác giả hoặc mô tả nhu cầu đọc sách để tôi hỗ trợ nhé."
            return result

        # 2. Kiểm tra an toàn nội dung theo quy định
        legal_check = check_query_legal_safety(query)
        if not legal_check["is_safe"]:
            result["passed"] = False
            result["reason"] = f"LEGAL_VIOLATION:{legal_check['violation_type']}"
            result["action"] = "REJECT"
            result["response"] = legal_check["refusal_message"]
            return result

        # 3. Kiểm tra Prompt Injection
        if any(p.search(query) for p in _INJECTION_RE):
            result["passed"] = False
            result["reason"] = "PROMPT_INJECTION_DETECTED"
            result["action"] = "REJECT"
            result["response"] = "Yêu cầu không phù hợp. Hệ thống chỉ xử lý các truy vấn liên quan đến tra cứu và giới thiệu sách theo dữ liệu có sẵn."
            return result

        # 4. Kiểm tra câu hỏi ngoài phạm vi
        if any(p.search(query) for p in _OOD_RE):
            result["passed"] = False
            result["reason"] = "OUT_OF_DOMAIN"
            result["action"] = "REJECT"
            result["response"] = "Hệ thống hiện chỉ hỗ trợ tra cứu và gợi ý sách. Bạn vui lòng đặt câu hỏi liên quan đến tác phẩm, tác giả hoặc chủ đề cần tìm."
            return result

        return result


class OutputRuleHarness:
    """Bộ kiểm tra câu trả lời sinh ra từ mô hình đối chiếu với danh sách sách thực tế."""

    @staticmethod
    def verify(answer: str, retrieved_books: List[dict]) -> Dict[str, Any]:
        issues: List[str] = []
        is_grounded = True

        # 1. Kiểm tra tuân thủ nội dung và đơn vị giá
        compliance = verify_answer_compliance(answer, retrieved_books)
        if not compliance["compliant"]:
            issues.extend(compliance["issues"])

        # 2. Cảnh báo nếu không có sách trong kho mà câu trả lời vẫn cam kết cụ thể
        if not retrieved_books and any(k in answer.lower() for k in ["cuốn sách này", "tác phẩm sau đây", "giá bán:"]):
            issues.append("Cảnh báo: Phát hiện dấu hiệu tự sinh nội dung sách khi kho dữ liệu rỗng (Hallucination).")
            is_grounded = False

        # 3. Kiểm tra độ khớp của giá bán được nhắc tới
        known_prices = [b.get("price", 0) for b in retrieved_books if b.get("price")]
        if known_prices:
            raw_nums = re.findall(r"\b(\d{2,3})[.,](\d{3})\b", answer)
            for part1, part2 in raw_nums:
                val = int(f"{part1}{part2}")
                matched_price = any(abs(val - kp) / kp < 0.1 for kp in known_prices if kp > 0)
                if not matched_price and val > 10000:
                    issues.append(f"Mức giá {val:,}đ trong câu trả lời có thể không khớp chính xác với dữ liệu kho.")

        return {
            "verified": len(issues) == 0,
            "is_grounded": is_grounded,
            "issues": issues,
            "books_audited": len(retrieved_books)
        }
