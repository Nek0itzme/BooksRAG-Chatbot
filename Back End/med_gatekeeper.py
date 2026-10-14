# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #15 — Tra cứu an toàn dược học
med_gatekeeper.py — Cổng an toàn OTC-Only cho mô-đun Tra cứu Dược học (Cross-Domain POC)
Dành cho đề tài NCKH: chứng minh kiến trúc Hybrid RAG + Rule Harness tổng quát hóa đa miền.

Công thức kiểm duyệt: Is Safe = Empty(User Conditions ∩ Drug Contraindications)
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

# FIX: dùng chung blocklist Rx với otc_gatekeeper — trước đây 2 module lệch nhau
# (bên này chặn cả "ung thư|hóa trị" vốn là bệnh chứ không phải thuốc → user hỏi về bệnh
# cũng bị báo "thuốc kê đơn"). Fallback regex cục bộ chỉ dùng khi import thất bại.
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from otc_gatekeeper import contains_rx_drug, MED_DISCLAIMER  # type: ignore
    _HAS_SHARED_RX = True
except Exception:
    contains_rx_drug = None  # type: ignore
    MED_DISCLAIMER = ""
    _HAS_SHARED_RX = False

# Nạp dữ liệu tra cứu khi cần thiết
_KB_PATH = Path(__file__).parent.parent / "database" / "otc_medicines_kb.json"
_KB: Optional[list] = None

# shortcut: blocklist Rx theo tên hoạt chất phổ biến, upgrade khi có Dược Thư đầy đủ
# (chỉ dùng khi không import được contains_rx_drug từ otc_gatekeeper)
_RX_RE = re.compile(
    r"amoxicillin|cephalexin|cefuroxim|ciprofloxacin|azithromycin|"
    r"losartan|amlodipin|metformin|insulin|prednisolon|dexamethason|"
    r"diazepam|alprazolam|morphin|codein",
    re.IGNORECASE,
)


def _is_rx_drug(text: str) -> Optional[str]:
    if _HAS_SHARED_RX and contains_rx_drug is not None:
        return contains_rx_drug(text)
    m = _RX_RE.search(text or "")
    return m.group(0).upper() if m else None

# Chuẩn hóa thuật ngữ bệnh lý phổ biến
_STOP = {"người", "nguoi", "bị", "bi", "có", "co", "đang", "dang", "tiền",
        "tien", "sử", "su", "bệnh", "benh", "với", "voi", "của", "cua",
        "và", "va", "hay", "từng", "tung", "tôi", "toi", "mình", "minh", "em"}


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"\w+", (s or "").lower())
            if len(t) >= 2 and t not in _STOP]


def _load_kb() -> list:
    global _KB
    if _KB is None:
        try:
            _KB = json.loads(_KB_PATH.read_text(encoding="utf-8"))
        except Exception:
            _KB = []
    return _KB or []


def check_drug_safety(
    drug_query: str,
    user_conditions: list[str],
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> dict:
    """
    Kiểm tra an toàn thuốc OTC tích hợp WebMD Symptom Checker & DrugBank.
    Trả về dict: {allowed, drug, warning, safe_note, drugbank_id, drugbank_url}.
    """
    rx_hit = _is_rx_drug(drug_query or "")
    if rx_hit:
        return {
            "allowed": False,
            "drug": None,
            "warning": "Đây là thuốc kê đơn (Rx), bắt buộc phải có chỉ định trực tiếp từ Bác sĩ. Hệ thống chỉ hỗ trợ thuốc OTC.",
            "safe_note": "",
            "disclaimer": MED_DISCLAIMER.strip(),
        }
    kb = _load_kb()
    q = (drug_query or "").lower()
    drug = next(
        (d for d in kb
         if q in d.get("trade_name", "").lower()
         or q in d.get("active_ingredient", "").lower()),
        None,
    )
    if drug is None:
        return {
            "allowed": False,
            "drug": None,
            "warning": "Không tìm thấy thuốc OTC phù hợp trong danh mục mẫu. Vui lòng hỏi dược sĩ hoặc bác sĩ.",
            "safe_note": "",
            "disclaimer": MED_DISCLAIMER.strip(),
        }
    conds = [(c or "").lower() for c in (user_conditions or [])]
    user_toks: set[str] = set()
    for c in conds:
        user_toks.update(_tokens(c))
    hits = []
    for c in drug.get("contraindications", []):
        cl = c.lower()
        if any(kw in cl for kw in conds if kw):  # khớp cụm từ nguyên văn
            hits.append(c)
            continue
        ct = set(_tokens(c))
        if len(user_toks & ct) >= (2 if len(ct) >= 4 else 1):
            hits.append(c)

    # Khuyến cáo WebMD theo tuổi
    if age is not None:
        try:
            age_val = int(age)
            min_age = int(drug.get("min_age", 0))
            if min_age > 0 and age_val < min_age:
                hits.append(f"Chống chỉ định độ tuổi: dưới {min_age} tuổi (WebMD / Dược Thư)")
        except Exception:
            pass

    # Khuyến cáo WebMD / DrugBank theo thai kỳ
    g_str = (gender or "").lower()
    if "pregnant" in g_str or "mang thai" in g_str or any("mang thai" in c for c in conds):
        if "thai" in " ".join(drug.get("contraindications", [])).lower() or "ibuprofen" in drug.get("active_ingredient", "").lower():
            hits.append("Chống chỉ định thai kỳ & cho con bú (DrugBank)")

    if hits:
        return {
            "allowed": False,
            "drug": drug,
            "warning": f"CẢNH BÁO: chống chỉ định với thể trạng/độ tuổi của bạn — {'; '.join(hits)}. Không tự ý dùng, hãy gặp bác sĩ/dược sĩ.",
            "safe_note": "",
            "drugbank_id": drug.get("drugbank_id", ""),
            "drugbank_url": drug.get("drugbank_url", ""),
            "disclaimer": MED_DISCLAIMER.strip(),
        }
    return {
        "allowed": True,
        "drug": drug,
        "warning": "",
        "safe_note": drug.get("safe_usage_note", ""),
        "drugbank_id": drug.get("drugbank_id", ""),
        "drugbank_url": drug.get("drugbank_url", ""),
        "disclaimer": MED_DISCLAIMER.strip(),
    }
