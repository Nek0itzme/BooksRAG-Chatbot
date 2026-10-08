# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
legal_rules.py — Bộ quy tắc an toàn nội dung và minh bạch thông tin xuất bản
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Căn cứ pháp lý:
1. Luật Xuất bản Việt Nam số 19/2012/QH13 (Điều 10 về nội dung và hành vi bị cấm).
2. Luật Bảo vệ quyền lợi người tiêu dùng số 19/2023/QH15 (Tính trung thực, minh bạch thông tin).
3. Nghị định 147/2024/NĐ-CP về quản lý, cung cấp, sử dụng dịch vụ Internet và thông tin trên mạng.
4. Quy chế sử dụng AI tạo sinh có trách nhiệm (Phụ lục 1 - KH-SGDĐT 2026).

Module thực hiện 2 nhiệm vụ:
1. Kiểm tra đầu vào: Chặn các truy vấn liên quan đến nội dung cấm, sách lậu hoặc kích động bạo lực.
2. Kiểm tra đầu ra: Đảm bảo phản hồi của mô hình ngôn ngữ không chứa nội dung độc hại và giá tiền niêm yết rõ ràng (VNĐ).
"""

import re
from typing import Dict, Any, List

# Pre-compile regex phát hiện số tiền trong câu trả lời (hiệu năng tốt hơn khi gọi nhiều lần)
_PRICE_RE = re.compile(r"\b\d{2,3}[.,]\d{3}\b")

# 1. Danh sách từ khóa và chủ đề không phù hợp theo quy định xuất bản
FORBIDDEN_THEMES: Dict[str, List[str]] = {
    "chong_pha_nha_nuoc": [
        "lật đổ chính quyền", "chống phá nhà nước", "tuyên truyền chống phá", 
        "chia rẽ khối đại đoàn kết", "xuyên tạc lịch sử cách mạng", "phản động"
    ],
    "bao_luc_khieu_dam": [
        "khiêu dâm đồi trụy", "kích động bạo lực", "cổ xúy tệ nạn",
        "hướng dẫn chế tạo vũ khí", "hướng dẫn tự tử", "chất gây nghiện cấm",
        "chế tạo bom", "bom xăng", "vũ khí tự chế"
    ],
    "xuc_pham_danh_du": [
        "xúc phạm danh dự", "vu khống bôi nhọ", "xúc phạm uy tín cơ quan",
        "phân biệt chủng tộc", "kỳ thị tôn giáo", "kỳ thị giới tính cực đoan"
    ],
    "an_pham_lau": [
        "sách lậu", "sách in lậu", "không có bản quyền", "sách cấm lưu hành",
        "sách bị thu hồi", "sách trốn thuế", "bản scan lậu"
    ],
    "vi_pham_phap_luat_kinh_te": [
        "trốn thuế", "rửa tiền", "gian lận thuế", "buôn lậu", "chuyển giá trái phép",
        "tiền ảo bất hợp pháp", "chiếm đoạt tài sản"
    ]
}

# Các từ khóa nhạy cảm cần kiểm tra kỹ theo ranh giới từ
SENSITIVE_KEYWORDS: List[str] = [
    "sách cấm", "sách lậu", "chế tạo bom", "chế tạo vũ khí", "bom xăng", "khiêu dâm",
    "xuyên tạc", "tuyên truyền phản động", "lừa đảo", "trúng số chắc chắn",
    "tà đạo", "mê tín dị đoan cực đoan", "trốn thuế", "rửa tiền", "vũ khí tự chế"
]

# Quy tắc minh bạch thông tin cho độc giả
CONSUMER_PROTECTION_RULES: Dict[str, str] = {
    "price_transparency": "Giá sách phải được niêm yết rõ ràng bằng đồng Việt Nam (VNĐ).",
    "stock_authenticity": "Thông báo trung thực tình trạng còn hàng hay hết hàng.",
    "origin_disclosure": "Ghi nhận đúng Nhà xuất bản hoặc đơn vị phát hành.",
    "anti_deceptive_summary": "Tóm tắt bám sát nội dung sách thực tế, không suy diễn sai lệch."
}


def check_query_legal_safety(query: str) -> Dict[str, Any]:
    """
    Kiểm tra câu hỏi của người dùng trước khi gửi vào RAG.
    Nếu phát hiện yêu cầu tìm sách cấm, sách lậu hoặc từ khóa nguy hại thì từ chối ngay.
    """
    if not query or not query.strip():
        return {
            "is_safe": True,
            "violation_type": None,
            "matched_terms": [],
            "refusal_message": None
        }

    query_lower = query.lower()
    matched_terms: List[str] = []
    violation_type = None

    # Quét theo các nhóm chủ đề cấm
    for theme, terms in FORBIDDEN_THEMES.items():
        for term in terms:
            if term in query_lower:
                matched_terms.append(term)
                violation_type = theme
                break
        if violation_type:
            break

    # Quét theo danh sách từ khóa nhạy cảm
    if not violation_type:
        for kw in SENSITIVE_KEYWORDS:
            kw_tokens = kw.split()
            if len(kw_tokens) == 1:
                query_tokens = query_lower.split()
                if kw in query_tokens:
                    matched_terms.append(kw)
                    violation_type = "noi_dung_nhay_cam"
                    break
            else:
                if kw in query_lower:
                    matched_terms.append(kw)
                    violation_type = "noi_dung_nhay_cam"
                    break

    if violation_type:
        return {
            "is_safe": False,
            "violation_type": violation_type,
            "matched_terms": matched_terms,
            "refusal_message": (
                "Hệ thống không thể hỗ trợ yêu cầu này do liên quan đến nội dung nhạy cảm, "
                "ấn phẩm hạn chế lưu hành hoặc vấn đề bản quyền sách theo quy định."
            )
        }

    return {
        "is_safe": True,
        "violation_type": None,
        "matched_terms": [],
        "refusal_message": None
    }


def verify_answer_compliance(answer: str, context_books: List[dict]) -> Dict[str, Any]:
    """
    Kiểm tra câu trả lời sinh ra từ mô hình:
    - Không chứa thuật ngữ nhạy cảm.
    - Giá tiền có kèm đơn vị tiền tệ rõ ràng (VNĐ, đ).
    - Ghi nhận số lượng sách thực tế trong ngữ cảnh để đối chiếu.
    """
    issues: List[str] = []
    
    # 1. Quét từ khóa không phù hợp trong câu trả lời
    for theme, terms in FORBIDDEN_THEMES.items():
        for term in terms:
            if term in answer.lower():
                issues.append(f"Cảnh báo: Câu trả lời chứa thuật ngữ nhạy cảm '{term}'")

    # 2. Kiểm tra đơn vị tiền tệ khi có nhắc đến giá
    price_pattern = _PRICE_RE.findall(answer)
    has_currency = any(curr in answer.lower() for curr in ["đ", "vnđ", "đồng", "k", "vnd"])
    if price_pattern and not has_currency:
        issues.append("Cảnh báo: Báo giá chưa niêm yết rõ đơn vị tiền tệ (VNĐ).")

    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "verified_books_count": len(context_books)
    }
