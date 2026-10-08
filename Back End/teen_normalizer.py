# -*- coding: utf-8 -*-
"""
[AI-Assisted Code]
teen_normalizer.py — Chuẩn hóa truy vấn tiếng Việt phi hình thức (Teencode / Từ lóng / Tiếng lòng)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"

Module này nạp dữ liệu từ file 'database/teencode_lexicon.json' để:
1. Chuẩn hóa từ viết tắt, teencode (BM25 và Vector Search không hiểu được "k bt" hay "vl").
2. Phát hiện "tiếng lòng" / tâm trạng để bổ sung gợi ý thể loại sách phù hợp (Mood-to-Genre Alignment).
"""

import json
import re
from pathlib import Path
from typing import Tuple, Optional, List

# Đường dẫn đến file JSON từ điển tổng hợp
_LEXICON_PATH = Path(__file__).parent.parent / "database" / "teencode_lexicon.json"

# Dữ liệu dự phòng mặc định (Fallback nếu không tìm thấy file JSON)
_DEFAULT_TEENCODE = [
    ("k bt", "không biết"), ("k biet", "không biết"), ("ko bt", "không biết"),
    ("ntn", "như thế nào"), ("tac gia", "tác giả"), ("sach j", "sách gì"),
    ("cuon j", "cuốn gì"), ("doc j", "đọc gì"), ("hay vcl", "rất hay"),
    ("buon qua", "buồn lắm"), ("stress qua", "căng thẳng"), ("that tinh", "thất tình"),
    ("ko", "không"), ("k", "không"), ("dc", "được"), ("đc", "được"),
    ("j", "gì"), ("bt", "biết"), ("tg", "tác giả"), ("nxb", "nhà xuất bản"),
    ("vcl", "rất"), ("vl", "rất"), ("lm", "lắm"), ("mk", "mình"),
    ("t", "tôi"), ("bn", "bạn"), ("s", "sao"), ("v", "vậy")
]

_DEFAULT_MOOD = [
    (re.compile(r"thất tình|chia tay|cô đơn|buồn|sad|heartbreak", re.I), "chữa lành cảm xúc yêu thương bản thân"),
    (re.compile(r"stress|áp lực|overthinking|lo lắng|căng thẳng", re.I), "tâm lý tích cực chánh niệm giảm căng thẳng"),
    (re.compile(r"lười|trì hoãn|mất động lực|chán nản", re.I), "kỷ luật bản thân thói quen thành công"),
    (re.compile(r"hết tiền|cháy túi|nghèo|kiếm tiền", re.I), "tài chính cá nhân đầu tư tiết kiệm"),
    (re.compile(r"ngại giao tiếp|hướng nội|sợ đám đông", re.I), "kỹ năng giao tiếp tự tin"),
    (re.compile(r"mông lung|mất phương hướng|lạc lõng", re.I), "định hướng cuộc sống ý nghĩa mục tiêu"),
]


def _load_lexicon() -> Tuple[List[Tuple[re.Pattern, str]], List[Tuple[re.Pattern, str]]]:
    """Nạp từ điển teencode và bản đồ cảm xúc từ file JSON, biên dịch sẵn Regex."""
    if _LEXICON_PATH.exists():
        try:
            with open(_LEXICON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. Nạp Teencode dict
            raw_dict = data.get("teencode_dict", {})
            # Sắp xếp theo độ dài khóa giảm dần để cụm từ dài khớp trước từ ngắn
            sorted_items = sorted(raw_dict.items(), key=lambda x: len(x[0]), reverse=True)
            teencode_compiled = [
                (re.compile(r"(?<!\w)" + re.escape(src) + r"(?!\w)", re.IGNORECASE), dst)
                for src, dst in sorted_items
            ]

            # 2. Nạp Mood map
            raw_moods = data.get("mood_map", [])
            mood_compiled = [
                (re.compile(m["pattern"], re.IGNORECASE), m["hint"])
                for m in raw_moods if "pattern" in m and "hint" in m
            ]
            return teencode_compiled, mood_compiled
        except Exception:
            pass

    # Fallback nếu lỗi hoặc không tìm thấy file
    teencode_compiled = [
        (re.compile(r"(?<!\w)" + re.escape(src) + r"(?!\w)", re.IGNORECASE), dst)
        for src, dst in _DEFAULT_TEENCODE
    ]
    return teencode_compiled, _DEFAULT_MOOD


# Nạp 1 lần duy nhất khi khởi động module (Module-level pre-compiled)
_TEENCODE_COMPILED, _MOOD_MAP = _load_lexicon()


def normalize_query(query: str) -> Tuple[str, Optional[str]]:
    """
    Nhận câu hỏi thô (có thể chứa teencode / tiếng lòng) và trả về:
    - query đã được chuẩn hóa để đưa vào pipeline RAG
    - mood_hint (Optional): gợi ý thể loại theo tâm trạng (None nếu không phát hiện)
    """
    if not query:
        return "", None

    # Bước 1: Chuẩn hóa teencode
    result = query
    for pattern, replacement in _TEENCODE_COMPILED:
        result = pattern.sub(replacement, result)

    # Bước 2: Phát hiện tiếng lòng và bổ sung mood hint vào cuối query
    mood_hint: Optional[str] = None
    for pattern, hint in _MOOD_MAP:
        if pattern.search(query):   # tìm trên query gốc
            mood_hint = hint
            if hint not in result:
                result = f"{result} {hint}"
            break

    return result.strip(), mood_hint


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    print(f"[*] Đã nạp từ điển từ: {_LEXICON_PATH.name}")
    print(f"    • Số mẫu teencode: {len(_TEENCODE_COMPILED)}")
    print(f"    • Số chủ đề tiếng lòng: {len(_MOOD_MAP)}\n")

    tests = [
        "k bt nen doc cuon j hay vcl",
        "tg nguyen nhat anh co sach j",
        "dang stress qua, muon doc sach tam ly",
        "that tinh roi, can sach doc cho qua",
        "sach kinh doanh hay nhat dc k",
    ]
    for t in tests:
        q, mood = normalize_query(t)
        print(f"  IN : {t}")
        print(f"  OUT: {q}")
        if mood:
            print(f"  MOOD: {mood}")
        print()
