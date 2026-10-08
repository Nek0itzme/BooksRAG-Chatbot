# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
chat_harness.py — Khung điều phối phiên hội thoại & Kiểm thử tự động (Chat & Test Harness)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Bao gồm:
1. DialogueHarness: Điều phối trạng thái phiên chat nhiều lượt (Multi-turn Session & State Management),
   lưu vết giỏ hàng, tác giả yêu thích để phục vụ gợi ý cá nhân hóa (Personalization).
2. AutomatedTestHarness: Khung kiểm thử tự động chạy toàn bộ bộ dữ liệu kiểm thử (Ground Truth),
   đo lường độ trễ (latency), tỷ lệ tuân thủ quy tắc (Rule Compliance) và độ trung thực (Faithfulness).
"""

import sys
from pathlib import Path
import time
import json
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from rule_harness import InputRuleHarness, OutputRuleHarness


class DialogueHarness:
    """Quản lý trạng thái và lịch sử tin nhắn trong một phiên làm việc."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: List[Dict[str, Any]] = []          # Lịch sử chat [{role, content, timestamp}]
        self.purchased_books: List[dict] = []             # Danh sách sách đã chọn mua
        self.preferred_categories: List[str] = []         # Thể loại quan tâm
        self.last_author_focused: Optional[str] = None    # Tác giả vừa tương tác
        self.created_at = time.time()

    def add_message(self, role: str, content: str) -> None:
        """Thêm tin nhắn mới vào lịch sử (giữ tối đa 20 tin nhắn gần nhất)."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def record_purchase(self, book: dict) -> None:
        """Ghi nhận sách đã chọn mua để phục vụ gợi ý cùng tác giả/thể loại."""
        self.purchased_books.append(book)
        if book.get("author"):
            self.last_author_focused = book["author"]
        if book.get("category") and book["category"] not in self.preferred_categories:
            self.preferred_categories.append(book["category"])

    def get_context_summary(self) -> Dict[str, Any]:
        """Tổng hợp thông tin tóm tắt của phiên."""
        return {
            "session_id": self.session_id,
            "total_messages": len(self.history),
            "purchased_count": len(self.purchased_books),
            "preferred_categories": self.preferred_categories,
            "focused_author": self.last_author_focused,
            "session_duration_sec": round(time.time() - self.created_at, 1),
        }


class AutomatedTestHarness:
    """Bộ chạy kiểm thử tự động trên tập câu hỏi mẫu để đo độ trễ và độ chính xác."""

    def __init__(self, rag_engine_callable):
        self.rag_engine = rag_engine_callable
        self.test_cases: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

    def load_test_cases(self, test_cases_file_or_list) -> None:
        """Nạp danh sách câu hỏi kiểm thử từ file JSON hoặc list."""
        if isinstance(test_cases_file_or_list, (str, Path)):
            with open(test_cases_file_or_list, "r", encoding="utf-8") as f:
                self.test_cases = json.load(f)
        else:
            self.test_cases = test_cases_file_or_list

    def run_benchmark(self) -> Dict[str, Any]:
        """Thực thi kiểm thử toàn bộ câu hỏi và tổng hợp kết quả đo lường."""
        self.results = []
        latencies: List[float] = []
        rule_passed_count = 0
        grounded_count = 0

        print(f"\nBắt đầu chạy kiểm thử {len(self.test_cases)} câu hỏi mẫu...")

        for idx, tc in enumerate(self.test_cases, start=1):
            query = tc.get("query", "")
            expected_book = tc.get("expected_book", "")
            tc_type = tc.get("type", "normal")

            t0 = time.time()
            
            # 1. Kiểm tra đầu vào qua InputRuleHarness
            input_eval = InputRuleHarness.evaluate(query)
            
            if not input_eval["passed"]:
                latency = round((time.time() - t0) * 1000, 1)
                latencies.append(latency)
                is_correct = tc_type in ["trap", "legal_violation", "prompt_injection", "out_of_domain"]
                
                self.results.append({
                    "id": idx,
                    "query": query,
                    "type": tc_type,
                    "status": "BLOCKED_BY_INPUT_HARNESS",
                    "reason": input_eval["reason"],
                    "latency_ms": latency,
                    "correct": is_correct,
                })
                if is_correct:
                    rule_passed_count += 1
                continue

            rule_passed_count += 1

            # 2. Xử lý qua RAG Engine
            try:
                rag_out = self.rag_engine(query)
                answer = rag_out.get("answer", "")
                books = rag_out.get("books", [])
            except Exception as e:
                answer = f"Error: {e}"
                books = []

            # 3. Kiểm tra đầu ra qua OutputRuleHarness
            output_eval = OutputRuleHarness.verify(answer, books)
            latency = round((time.time() - t0) * 1000, 1)
            latencies.append(latency)

            is_correct = False
            if expected_book:
                is_correct = (
                    any(expected_book.lower() in b.get("title", "").lower() for b in books) or 
                    (expected_book.lower() in answer.lower())
                )
            else:
                is_correct = output_eval["verified"]

            if output_eval["is_grounded"]:
                grounded_count += 1

            self.results.append({
                "id": idx,
                "query": query,
                "type": tc_type,
                "status": "PASSED",
                "latency_ms": latency,
                "retrieved_books_count": len(books),
                "is_grounded": output_eval["is_grounded"],
                "correct": is_correct,
            })

            status_icon = "PASS" if is_correct else "FAIL"
            print(f"  [{idx:02d}/{len(self.test_cases):02d}] [{status_icon}] {query[:35]}... -> {latency}ms")

        # 4. Tính toán số liệu thống kê
        total = max(1, len(self.test_cases))
        avg_latency = sum(latencies) / total
        latencies_sorted = sorted(latencies)
        p95_latency = latencies_sorted[int(total * 0.95)] if total > 1 else latencies_sorted[0]
        accuracy_rate = sum(1 for r in self.results if r.get("correct")) / total
        grounded_rate = grounded_count / total

        summary = {
            "total_queries": total,
            "average_latency_ms": round(avg_latency, 1),
            "p95_latency_ms": round(p95_latency, 1),
            "accuracy_rate": round(accuracy_rate * 100, 2),
            "grounded_rate": round(grounded_rate * 100, 2),
            "rule_compliance_rate": round((rule_passed_count / total) * 100, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        print("\nKết quả kiểm thử tự động:")
        print(f"  • Tổng câu hỏi:        {summary['total_queries']}")
        print(f"  • Độ trễ trung bình:   {summary['average_latency_ms']} ms")
        print(f"  • Độ trễ P95:          {summary['p95_latency_ms']} ms")
        print(f"  • Độ chính xác:        {summary['accuracy_rate']} %")
        print(f"  • Tỷ lệ đúng dữ liệu:  {summary['grounded_rate']} %")
        print(f"  • Tuân thủ quy tắc:    {summary['rule_compliance_rate']} %\n")

        return summary
