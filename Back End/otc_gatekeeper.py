# -*- coding: utf-8 -*-
"""
[AI-Assisted Code] Prompt #15 — Tra cứu an toàn dược học lâm sàng OTC
otc_gatekeeper.py — Phân hệ kiểm soát an toàn & tra cứu Dược học không kê đơn (Cross-Domain POC)
Dành cho đề tài NCKH: "Hệ Thống Tư Vấn Bán Sách Tự Động Tích Hợp RAG"
(Phân hệ mở rộng chứng minh năng lực tổng quát hóa của kiến trúc Hybrid RAG & Rule Harness)

Bao gồm 3 lớp kiểm soát an toàn:
1. Rx Gatekeeper: Chặn 100% thuốc kê đơn (Kháng sinh, An thần, Tim mạch, Kháng viêm steroid)
2. Contraindication Checker: Đối chiếu hồ sơ bệnh lý người dùng (Dạ dày, Gan, Thận, Thai kỳ, G6PD)
3. Pharmacopoeia Grounding: Trích xuất thông tin chuẩn từ Dược Thư Quốc Gia Việt Nam & Long Châu / Pharmacity
"""

import os
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# ── Nạp cơ sở tri thức thuốc OTC ──────────────────────────────────────────────
_DB_PATH = Path(__file__).parent.parent / "database" / "otc_medicines_kb.json"

_OTC_DATA: List[Dict[str, Any]] = []
if _DB_PATH.exists():
    try:
        _OTC_DATA = json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Không nạp được otc_medicines_kb.json: {e}")


# ── 1. DANH MỤC THUỐC KÊ ĐƠN (Rx) BỊ CẤM TƯ VẤN ──────────────────────────────
# Biên dịch trước biểu thức chính quy cho nhóm thuốc kê đơn đặc thù
_RX_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(amoxicillin|augmentin|cephalexin|cefuroxim|cefixim|ciprofloxacin|azithromycin|clarithromycin|tetracyclin|levofloxacin)\b",
        r"\b(diazepam|lexomil|seduxen|clonazepam|alprazolam|zolpidem|phenobarbital)\b",
        r"\b(prednisolon|dexamethason|medrol|methylprednisolon|betamethason)\b",
        r"\b(amlodipin|captopril|losartan|enalapril|atorvastatin|metformin|insulin)\b",
        r"\b(tramadol|morphin|fentanyl|codein\s+liều\s+cao)\b",
    ]
]


def contains_rx_drug(text: str) -> Optional[str]:
    """
    FIX: hàm dùng chung cho cả otc_gatekeeper và med_gatekeeper — trước đây 2 module giữ
    2 blocklist khác nhau (med chặn cả "ung thư|hóa trị" vốn là bệnh chứ không phải thuốc;
    otc thiếu cefuroxim). Trả về tên hoạt chất khớp, hoặc None.
    """
    if not text:
        return None
    for pat in _RX_PATTERNS:
        match = pat.search(text)
        if match:
            return match.group(0).upper()
    return None


def _strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp không dấu (vd user gõ 'da day', 'mang thai' vẫn bắt được)."""
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


# Khuyến cáo y tế bắt buộc kèm mọi phản hồi tư vấn dược (compliance, không phải chẩn đoán).
MED_DISCLAIMER = (
    "\n\n⚕️ **Lưu ý y tế:** Thông tin trên chỉ mang tính tham khảo, không thay thế chẩn đoán "
    "hay chỉ định của bác sĩ/dược sĩ. Nếu triệu chứng nặng, kéo dài hoặc thuộc nhóm báo động đỏ, "
    "hãy đến cơ sở y tế ngay."
)


def check_rx_gatekeeper(query: str) -> Optional[str]:
    """
    Kiểm tra xem câu hỏi có chứa yêu cầu tư vấn thuốc kê đơn (Rx) hay không.
    Nếu có, lập tức trả về thông báo từ chối an toàn.
    """
    for pat in _RX_PATTERNS:
        match = pat.search(query)
        if match:
            drug_name = match.group(0).upper()
            return (
                f"🚫 **CẢNH BÁO AN TOÀN DƯỢC HỌC (OTC GATEKEEPER):**\n\n"
                f"Hoạt chất/Thuốc **'{drug_name}'** thuộc danh mục **Thuốc Kê Đơn (Rx)** theo quy định của Bộ Y Tế.\n"
                f"- Hệ thống AI từ chối tư vấn liều dùng và cách điều trị đối với thuốc kê đơn.\n"
                f"- **Khuyến nghị:** Bạn cần đến trực tiếp cơ sở y tế hoặc bệnh viện để được Bác sĩ thăm khám, chẩn đoán và kê đơn phù hợp."
                + MED_DISCLAIMER
            )
    return None


# ── 2. KIỂM TRA CHỐNG CHỈ ĐỊNH DỰA TRÊN HỒ SƠ BỆNH LÝ & WEBMD TRIAGE ─────────
def check_contraindications(
    drug: Dict[str, Any],
    user_conditions: List[str],
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> List[str]:
    """
    Thuật toán đối chiếu chéo giữa tiền sử bệnh, độ tuổi, giới tính và tiêu chuẩn DrugBank/WebMD:
    Warnings = {c in Drug.contraindications | condition_match(c, user_conditions)} ∪ Age_Contra ∪ Gender_Contra
    """
    warnings = []
    drug_contra = " ".join(drug.get("contraindications", [])).lower()
    # FIX: so khớp song song cả bản có dấu và không dấu — trước đây user gõ "da day",
    # "suy than", "mang thai" không dấu thì không nhánh nào bắt được, thuốc nguy hiểm
    # vẫn bị gắn cờ "an toàn".
    drug_contra_na = _strip_accents(drug_contra)
    active_ing = drug.get("active_ingredient", "").lower()
    user_conditions = user_conditions or []

    # 1. Kiểm tra bệnh nền
    for cond in user_conditions:
        c_clean = cond.strip().lower()
        if not c_clean:
            continue
        c_na = _strip_accents(c_clean)

        # Nhận diện xung đột bệnh lý phổ biến
        if "dạ dày" in c_clean or "loét" in c_clean or "da day" in c_na or "loet" in c_na:
            if "dạ dày" in drug_contra or "loét" in drug_contra or "xuất huyết" in drug_contra or "da day" in drug_contra_na or "xuat huyet" in drug_contra_na or "ibuprofen" in active_ing:
                warnings.append(f"Tiền sử bệnh '{cond}': ⚠️ Xung đột: Thuốc có nguy cơ kích ứng/chảy máu niêm mạc dạ dày.")
        elif "gan" in c_na:
            if "gan" in drug_contra_na:
                warnings.append(f"Tiền sử bệnh '{cond}': ⚠️ Xung đột: Thuốc chuyển hóa qua gan, chống chỉ định suy gan.")
        elif "thận" in c_clean or "than" in c_na or "sỏi" in c_clean or "soi" in c_na:
            if "thận" in drug_contra or "sỏi" in drug_contra or "than" in drug_contra_na or "soi" in drug_contra_na:
                warnings.append(f"Tiền sử bệnh '{cond}': ⚠️ Xung đột: Nguy cơ tích tụ độc tính hoặc lắng cặn sỏi thận.")
        elif "mang thai" in c_clean or "thai kỳ" in c_clean or "bầu" in c_clean or "mang thai" in c_na or "thai ky" in c_na or "bau" in c_na:
            if "mang thai" in drug_contra or "thai" in drug_contra or "ibuprofen" in active_ing:
                warnings.append(f"Tình trạng '{cond}': ⚠️ Chống chỉ định phụ nữ có thai.")
        elif "g6pd" in c_clean:
            if "g6pd" in drug_contra:
                warnings.append(f"Cơ địa '{cond}': ⚠️ Nguy cơ tan máu cấp tính ở người thiếu men G6PD.")
        elif "huyết áp" in c_clean or "tim mạch" in c_clean or "huyet ap" in c_na or "tim mach" in c_na:
            if "huyết áp" in drug_contra or "tim" in drug_contra or "huyet ap" in drug_contra_na or "phenylephrine" in active_ing:
                warnings.append(f"Tiền sử '{cond}': ⚠️ Thuốc có hoạt chất co mạch, làm tăng huyết áp hoặc hồi hộp tim.")

    # 2. Khuyến cáo an toàn theo Độ Tuổi
    if age is not None:
        try:
            age_val = int(age)
            min_age = int(drug.get("min_age", 0))
            if min_age > 0 and age_val < min_age:
                warnings.append(f"Độ tuổi ({age_val} tuổi): ⚠️ Chống chỉ định cho trẻ dưới {min_age} tuổi theo Dược Thư.")
            elif age_val < 12 and ("caffeine" in drug.get("active_ingredient", "").lower() or "phenylephrine" in drug.get("active_ingredient", "").lower()):
                warnings.append(f"Độ tuổi nhi khoa ({age_val} tuổi): ⚠️ Chứa hoạt chất kích thích thần kinh/co mạch, không khuyến cáo cho trẻ < 12 tuổi.")
            elif age_val >= 65:
                if "chlorpheniramine" in drug.get("active_ingredient", "").lower():
                    warnings.append(f"Người cao tuổi ({age_val} tuổi): ⚠️ Cảnh báo — Kháng histamin thế hệ 1 tăng nguy cơ buồn ngủ quá mức, té ngã và bí tiểu.")
                elif "ibuprofen" in drug.get("active_ingredient", "").lower():
                    warnings.append(f"Người cao tuổi ({age_val} tuổi): ⚠️ Cảnh báo — NSAID tăng nguy cơ loét dạ dày thầm lặng và suy giảm chức năng thận.")
        except Exception:
            pass

    # 3. Khuyến cáo an toàn cho Phụ nữ có thai & Cho con bú
    g_clean = (gender or "").lower()
    is_preg = "pregnant" in g_clean or "mang thai" in g_clean or any("mang thai" in c.lower() or "thai kỳ" in c.lower() for c in user_conditions)
    if is_preg:
        if "thai" in drug_contra or "sảy thai" in drug_contra or "tử cung" in drug_contra or "ibuprofen" in drug.get("active_ingredient", "").lower() or "berberin" in drug.get("active_ingredient", "").lower():
            warnings.append("Cảnh báo an toàn thai kỳ: 🚫 Chống chỉ định — Hoạt chất có thể qua nhau thai hoặc kích thích co bóp tử cung gây nguy cơ sảy thai.")

    return warnings


# ── 3. TRÍCH XUẤT NHÂN KHẨU & TIỀN SỬ BỆNH LÝ TỪ CÂU HỎI (PATIENT PROFILE PARSER) ─
# Biên dịch trước biểu thức chính quy nhận diện tuổi, giới tính và bệnh nền
# FIX: (\d{1,2}) cũ không bắt tuổi 3 chữ số; `t\b` bắt nhầm chữ "t" đứng riêng
# (vd "8 t" vô nghĩa vẫn thành 8 tuổi). Clamp 1–120 khi dùng (xem extract_patient_profile).
_AGE_EXTRACT_RE = re.compile(r"(\d{1,3})\s*(?:tuổi|tuoi|yo|year(?:s)?\s*old)\b", re.IGNORECASE)
_GENDER_MALE_RE = re.compile(r"\b(nam|con trai|đàn ông|anh|ông|chú|bác trai)\b", re.IGNORECASE)
_GENDER_FEMALE_RE = re.compile(r"\b(nữ|con gái|phụ nữ|chị|cô|bà|bác gái)\b", re.IGNORECASE)
_PREGNANT_RE = re.compile(r"\b(mang thai|thai kỳ|có bầu|bầu|sau sinh|cho con bú|đang có em bé)\b", re.IGNORECASE)

_CONDITION_KEYWORDS_MAP = {
    "mang thai": ["mang thai", "thai kỳ", "có bầu", "bầu", "cho con bú", "sau sinh"],
    "dạ dày": [
        "dạ dày", "bao tử", "loét", "chảy máu dạ dày", "xuất huyết", "trào ngược",
        "viêm hang vị", "đi ngoài ra máu", "tiêu ra máu", "phân đen", "ỉa ra máu", "ra máu"
    ],
    "gan": ["gan", "suy gan", "men gan", "viêm gan"],
    "thận": ["thận", "suy thận", "sỏi thận", "chạy thận"],
    "g6pd": ["g6pd", "thiếu men", "tan máu", "thiếu g6pd"],
    "huyết áp": ["huyết áp", "cao huyết áp", "tăng huyết áp", "tim mạch", "mạch vành", "đột quỵ"],
    "tre_em": ["trẻ em", "dưới 12 tuổi", "trẻ nhỏ", "bé", "sơ sinh", "nhi khoa"]
}

_RED_FLAG_PATTERNS = [
    (re.compile(r"\b(đi ngoài ra máu|tiêu ra máu|phân đen|chảy máu tiêu hóa|ỉa ra máu)\b", re.IGNORECASE),
     "Xuất huyết đường tiêu hóa / Dấu hiệu cảnh báo đỏ (Red Flag)"),
    (re.compile(r"\b(đau ngực dữ dội|khó thở nặng|ngất xỉu|nôn ra máu)\b", re.IGNORECASE),
     "Cơn đau thắt ngực / Xuất huyết cấp / Suy hô hấp"),
    (re.compile(r"\b(sốt cao co giật|mất ý thức|hôn mê)\b", re.IGNORECASE),
     "Sốt cao ác tính / Dấu hiệu nhiễm trùng nặng")
]


def extract_patient_profile(
    query: str,
    existing_conditions: Optional[List[str]] = None,
    existing_age: Optional[int] = None,
    existing_gender: Optional[str] = None
) -> Tuple[Optional[int], Optional[str], List[str], List[str]]:
    """
    Trích xuất tự động thông tin nhân khẩu (tuổi, giới tính) và tiền sử bệnh lý từ câu hỏi của người dùng.
    Trả về: (effective_age, effective_gender, all_conditions, newly_detected_conditions)
    """
    q_lower = query.lower()
    new_conditions: List[str] = []

    # 1. Tuổi
    age = existing_age
    age_match = _AGE_EXTRACT_RE.search(query)
    if age_match:
        try:
            # FIX: clamp 1–120 — trước đây "200 tuổi" vẫn thành 200, lọt vào nhánh >= 65 sai.
            age = max(1, min(int(age_match.group(1)), 120))
        except Exception:
            pass
    elif not age:
        if any(k in q_lower for k in ["bé", "trẻ nhỏ", "con nít"]):
            age = 8
        elif any(k in q_lower for k in ["ông", "bà", "người cao tuổi", "bác"]):
            age = 68

    # 2. Giới tính
    gender = existing_gender
    if _PREGNANT_RE.search(query):
        gender = "pregnant"
        if "mang thai" not in new_conditions:
            new_conditions.append("mang thai")
    elif _GENDER_MALE_RE.search(query) and not (existing_gender and existing_gender == "pregnant"):
        gender = "male"
    elif _GENDER_FEMALE_RE.search(query):
        gender = "female"

    # 3. Tiền sử bệnh lý
    for cond_key, kw_list in _CONDITION_KEYWORDS_MAP.items():
        if any(kw in q_lower for kw in kw_list):
            if cond_key not in new_conditions:
                new_conditions.append(cond_key)

    if age is not None and age < 12 and "tre_em" not in new_conditions:
        new_conditions.append("tre_em")

    all_conditions = list(dict.fromkeys((existing_conditions or []) + new_conditions))
    return age, gender, all_conditions, new_conditions


def detect_red_flags(query: str) -> List[str]:
    """Phát hiện các triệu chứng báo động đỏ nguy hiểm cần đi bệnh viện cấp cứu."""
    flags = []
    for pat, desc in _RED_FLAG_PATTERNS:
        if pat.search(query):
            flags.append(desc)
    return flags


def _generate_fallback_advice(
    query: str,
    conditions: List[str],
    age: Optional[int],
    gender: Optional[str],
    matched_kb: List[Dict[str, Any]],
    red_flags: List[str]
) -> str:
    """Tạo tư vấn dự phòng chuẩn Dược lâm sàng khi không kết nối được Gemini."""
    parts = []
    if red_flags:
        parts.append(
            f"🚨 **CẢNH BÁO NGUY HIỂM — DẤU HIỆU BÁO ĐỘNG ĐỎ (RED FLAG):**\n"
            f"Triệu chứng bạn mô tả ({'; '.join(red_flags)}) là dấu hiệu tổn thương sâu hoặc xuất huyết nguy hiểm. "
            f"**Tuyệt đối KHÔNG tự ý mua thuốc cầm tiêu chảy, kháng sinh hoặc thuốc giảm đau tự điều trị tại nhà.** "
            f"Bạn cần đến cơ sở y tế hoặc bệnh viện có chuyên khoa Tiêu hóa để được nội soi và xét nghiệm khẩn cấp!"
        )
    else:
        parts.append("📋 **ĐÁNH GIÁ LÂM SÀNG BAN ĐẦU:**\nTriệu chứng của bạn đã được đối chiếu với hệ thống phân tầng triệu chứng WebMD và Dược Thư Quốc Gia.")

    if matched_kb:
        safe_drugs = [m for m in matched_kb if m.get("is_safe_for_user")]
        unsafe_drugs = [m for m in matched_kb if not m.get("is_safe_for_user")]
        
        if safe_drugs:
            parts.append("\n💊 **THUỐC / HOẠT CHẤT OTC AN TOÀN ĐƯỢC GỢI Ý:**")
            for m in safe_drugs[:2]:
                d = m.get("drug_info", {})
                parts.append(f"• **{d.get('trade_name')}** ({d.get('active_ingredient')}): {d.get('safe_usage_note', 'Dùng đúng liều lượng chỉ định.')}")
        
        if unsafe_drugs:
            parts.append("\n⚠️ **CẢNH BÁO CHỐNG CHỈ ĐỊNH VỚI THỂ TRẠNG HIỆN TẠI:**")
            for m in unsafe_drugs[:2]:
                d = m.get("drug_info", {})
                warns = "; ".join(m.get("contraindication_warnings", []))
                parts.append(f"• **{d.get('trade_name')}**: {warns}")
    else:
        parts.append("\n💧 **LƯU Ý XỬ TRÍ BAN ĐẦU AN TOÀN:**\n• Nếu mất nước hoặc tiêu chảy: Bù nước và điện giải bằng dung dịch Oresol pha đúng tỉ lệ.\n• Ăn đồ lỏng, dễ tiêu hóa, kiêng thức ăn cay nóng, dầu mỡ và đồ uống có cồn.\n• Theo dõi sát sao tình trạng cơ thể.")

    parts.append(
        "\n\n📚 **NGUỒN THAM CHIẾU KHOA HỌC:**\n"
        "• 📖 *Dược Thư Quốc Gia Việt Nam* (Ấn bản mới nhất — Bộ Y Tế Việt Nam)\n"
        "• 🔬 *DrugBank Online* (Clinical Drug Data & Adverse Interaction Index)\n"
        "• 🌐 *WebMD Symptom Checker & Clinical Triage*"
    )
    return "\n".join(parts)


def _matches_query(target: str, query: str) -> bool:
    """Kiểm tra từ hoặc cụm từ có xuất hiện nguyên từ trong câu hỏi hay không (loại bỏ trường hợp ký tự đơn như 'c' trong Vitamin C)."""
    if not target or not query:
        return False
    t_clean = target.strip().lower()
    q_clean = query.strip().lower()
    if len(t_clean) < 3:
        return False
    pattern = r'(?<!\w)' + re.escape(t_clean) + r'(?!\w)'
    return bool(re.search(pattern, q_clean))


def _consult_with_gemini(
    query: str,
    conditions: List[str],
    age: Optional[int],
    gender: Optional[str],
    matched_kb: List[Dict[str, Any]],
    red_flags: List[str]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Gọi Google Gemini làm Trợ lý Dược sĩ Lâm sàng AI (Clinical Pharmacist AI):
    - Đánh giá lâm sàng & phân tầng triệu chứng (WebMD Triage)
    - Tự động tìm kiếm và đề xuất 1-3 thuốc/hoạt chất OTC phù hợp nhất với triệu chứng
    - Thẩm định chống chỉ định với tiền sử bệnh lý, tuổi, giới tính
    - Trích dẫn nguồn khoa học minh bạch (Dược Thư QG, DrugBank, WebMD, Bộ Y Tế).
    - Trả về tuple: (ai_advice_text, structured_suggested_drugs)
    """
    cond_str = ", ".join(conditions) if conditions else "Chưa ghi nhận bệnh nền"
    age_str = f"{age} tuổi" if age else "Chưa rõ"
    gender_str = "Nam" if gender == "male" else ("Nữ (Thai kỳ)" if gender == "pregnant" else ("Nữ" if gender == "female" else "Chưa rõ"))

    kb_summaries = []
    for m in matched_kb[:4]:
        d = m.get("drug_info", {})
        kb_summaries.append(f"- {d.get('trade_name')} ({d.get('active_ingredient')}): Chỉ định: {', '.join(d.get('common_symptoms', []))}; Chống chỉ định: {', '.join(d.get('contraindications', []))}")
    kb_context = "\n".join(kb_summaries) if kb_summaries else "Kho dữ liệu mẫu không có thuốc khớp trực tiếp; hãy tra cứu và đề xuất các thuốc/hoạt chất OTC chuẩn y khoa phù hợp với triệu chứng của người dùng."

    rf_context = ""
    if red_flags:
        rf_context = f"\n⚠️ PHÁT HIỆN DẤU HIỆU CẢNH BÁO ĐỎ (RED FLAG): {'; '.join(red_flags)}. Bắt buộc cảnh báo khẩn cấp bệnh nhân KHÔNG tự ý uống thuốc bừa bãi và phải đi bệnh viện khám chuyên khoa Tiêu hóa / Huyết học ngay!\n"

    prompt = f"""Bạn là Trợ Lý Dược Sĩ Lâm Sàng AI (Clinical Pharmacist AI) chuyên nghiệp, tuân thủ nghiêm ngặt Dược Thư Quốc Gia Việt Nam, DrugBank Online, và WebMD Clinical Triage.

THÔNG TIN BỆNH NHÂN:
- Câu hỏi / Nhu cầu điều trị: "{query}"
- Độ tuổi: {age_str}
- Giới tính: {gender_str}
- Tiền sử bệnh nền & Thể trạng: {cond_str}
{rf_context}
DANH MỤC THUỐC MẪU TRONG KHO (NẾU KHÔNG LIÊN QUAN THÌ TUYỆT ĐỐI KHÔNG ÉP DÙNG):
{kb_context}

YÊU CẦU NỘI DUNG TƯ VẤN:
1. ĐÁNH GIÁ LÂM SÀNG & NGUY CƠ:
   - Phân tích triệu chứng người dùng hỏi.
   - Nếu có dấu hiệu báo động đỏ (chảy máu, khó thở...), cảnh báo đi viện ngay.
2. ĐỀ XUẤT THUỐC / HOẠT CHẤT OTC PHÙ HỢP NHẤT:
   - Dựa trên Dược Thư Quốc Gia và DrugBank, tự xác định 1-3 thuốc hoặc hoạt chất OTC chuẩn mực,
     hiệu quả nhất cho triệu chứng này; nêu rõ cơ chế tác dụng, liều dùng an toàn và thời điểm sử dụng.
   - TUYỆT ĐỐI KHÔNG ép giới thiệu các thuốc không liên quan trong kho mẫu; chỉ dùng kho mẫu khi thực sự khớp triệu chứng.
   - Với mỗi đề xuất, giải thích ngắn gọn vì sao phù hợp với triệu chứng đã nêu.
3. CHỐNG CHỈ ĐỊNH ĐỐI CHIẾU:
   - Đối chiếu với tiền sử ({cond_str}), độ tuổi ({age_str}), giới tính ({gender_str}).
4. TRÍCH NGUỒN THAM CHIẾU KHOA HỌC (BẮT BUỘC):
   - Trích nguồn cụ thể ở cuối bài viết: Dược Thư Quốc Gia Việt Nam, DrugBank Online, WebMD, Bộ Y Tế.

BẮT BUỘC Ở CUỐI CÙNG PHẢN HỒI, xuất một khối JSON chuẩn dạng ```json ... ``` chứa mảng "suggested_drugs" để hệ thống tạo thẻ thuốc:
```json
{{
  "suggested_drugs": [
    {{
      "trade_name": "Tên biệt dược hoặc hoạt chất kèm dạng dùng",
      "active_ingredient": "Tên hoạt chất chính & hàm lượng",
      "drugbank_id": "Mã DrugBank ID (VD: DB00350 hoặc N/A)",
      "category": "Phân loại nhóm thuốc OTC",
      "common_symptoms": ["Triệu chứng 1", "Triệu chứng 2"],
      "mechanism_of_action": "Cơ chế tác động dược lý (DrugBank)",
      "safe_usage_note": "Hướng dẫn liều dùng và cách dùng an toàn",
      "pharmacopoeia_ref": "Nguồn tham chiếu Dược Thư QG / DrugBank"
    }}
  ]
}}
```"""

    suggested_drugs: List[Dict[str, Any]] = []
    clean_advice = ""

    try:
        from gemini_client import _call_gemini
        raw_resp = _call_gemini(prompt)
        if raw_resp and raw_resp.strip():
            # Tách khối JSON suggested_drugs
            # FIX: regex cũ dùng non-greedy `\{[\s\S]*?\}` nên dừng ở dấu `}` đầu tiên
            # (kết thúc object thuốc đầu tiên) → json.loads nổ → mất toàn bộ suggested_drugs
            # mà không báo lỗi. Dùng greedy + fallback cân bằng ngoặc.
            json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw_resp)
            raw_json_text = json_match.group(1) if json_match else None
            if raw_json_text is None:
                brace_start = raw_resp.find("{")
                brace_end = raw_resp.rfind("}")
                if brace_start != -1 and brace_end > brace_start:
                    raw_json_text = raw_resp[brace_start:brace_end + 1]
            if raw_json_text:
                try:
                    data = json.loads(raw_json_text)
                    raw_drugs = data.get("suggested_drugs", [])
                    for d in raw_drugs:
                        c_warns = check_contraindications(d, conditions, age=age, gender=gender)
                        suggested_drugs.append({
                            "drug_info": d,
                            "score": 5,
                            "contraindication_warnings": c_warns,
                            "is_safe_for_user": len(c_warns) == 0,
                            "drugbank_id": d.get("drugbank_id", ""),
                            "drugbank_url": f"https://go.drugbank.com/drugs/{d.get('drugbank_id')}" if d.get("drugbank_id") and d.get("drugbank_id").startswith("DB") else "https://go.drugbank.com/",
                            "mechanism_of_action": d.get("mechanism_of_action", ""),
                            "is_ai_suggested": True
                        })
                except Exception as e:
                    print(f"[WARN] Error parsing suggested_drugs JSON: {e}")
                # FIX: json_match có thể None khi JSON nằm ngoài fence (lấy qua brace fallback) —
                # code cũ gọi json_match.start() unconditional → AttributeError rơi vào except
                # ngoài và trả fallback, vứt bỏ cả advice Gemini vừa tạo.
                if json_match:
                    clean_advice = raw_resp[:json_match.start()].strip()
                elif raw_json_text:
                    clean_advice = raw_resp.replace(raw_json_text, "").strip()
                else:
                    clean_advice = raw_resp.strip()
                if not clean_advice:
                    clean_advice = raw_resp.strip()
            else:
                clean_advice = raw_resp.strip()
            return clean_advice, suggested_drugs
    except Exception as e:
        print(f"[WARN] Gemini consult failed, using fallback: {e}")

    fallback_advice = _generate_fallback_advice(query, conditions, age, gender, matched_kb, red_flags)
    return fallback_advice, suggested_drugs


# ── 4. TRUY VẤN VÀ TƯ VẤN DƯỢC HỌC OTC (HYBRID RAG & AI CONSULTANT) ─────────
def consult_otc_medicine(
    query: str,
    user_conditions: Optional[List[str]] = None,
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Hàm thực thi RAG Dược học OTC:
    1. Kiểm tra Cổng Rx Gatekeeper
    2. Tự động trích xuất thông tin nhân khẩu (tuổi, giới tính) & tiền sử bệnh từ câu hỏi
    3. Tìm kiếm thuốc khớp thực sự trong otc_medicines_kb.json (loại bỏ bẫy ký tự đơn)
    4. Thẩm định an toàn với Hồ sơ bệnh, độ tuổi, giới tính người dùng
    5. Sử dụng Google Gemini làm Trợ lý Dược sĩ Lâm sàng AI tra cứu sâu & đề xuất thuốc phù hợp
    6. Trả về kết quả kèm danh sách suggested_drugs để Frontend hiển thị thẻ thuốc liên quan
    """
    user_conditions = user_conditions or []

    # Bước 1: Gatekeeper
    rx_block = check_rx_gatekeeper(query)
    if rx_block:
        return {
            "status": "blocked_rx",
            "is_safe": False,
            "message": rx_block,
            "matched_drugs": [],
            "suggested_drugs": []
        }

    # Bước 2: Tự động trích xuất nhân khẩu và tiền sử bệnh lý từ câu hỏi
    eff_age, eff_gender, all_conditions, new_conds = extract_patient_profile(
        query, existing_conditions=user_conditions, existing_age=age, existing_gender=gender
    )
    red_flags = detect_red_flags(query)

    query_lower = query.lower()
    matched: List[Dict[str, Any]] = []

    # Sử dụng dữ liệu tham chiếu đã nạp sẵn ở import (tránh đọc + parse JSON từ đĩa mỗi request).
    # FIX: trước đây mỗi request /api/med/consult đều json.loads toàn bộ file KB (~I/O + CPU
    # lãng phí, và race khi file đang được ghi). Chỉ đọc lại khi _OTC_DATA rỗng.
    kb_data = _OTC_DATA
    if not kb_data and _DB_PATH.exists():
        try:
            kb_data = json.loads(_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            kb_data = _OTC_DATA

    # Bước 3: Khớp dữ liệu từ KB với thuật toán so khớp nguyên từ chuẩn xác
    for drug in kb_data:
        trade_name  = drug.get("trade_name", "").lower()
        active_ing  = drug.get("active_ingredient", "").lower()
        symptoms    = [s.lower() for s in drug.get("common_symptoms", [])]
        webmd_syms  = [s.lower() for s in drug.get("webmd_symptoms", [])]

        matched_score = 0
        if _matches_query(trade_name, query_lower):
            matched_score += 4
        else:
            for part in trade_name.split():
                if len(part) >= 4 and _matches_query(part, query_lower):
                    matched_score += 3

        act_first = active_ing.split()[0] if active_ing else ""
        if len(act_first) >= 4 and _matches_query(act_first, query_lower):
            matched_score += 3

        for s in symptoms:
            if _matches_query(s, query_lower):
                matched_score += 2
        for w in webmd_syms:
            if _matches_query(w, query_lower):
                matched_score += 2

        # Chỉ đưa vào kết quả nếu điểm khớp thực sự từ 3 trở lên
        if matched_score >= 3:
            c_warnings = check_contraindications(drug, all_conditions, age=eff_age, gender=eff_gender)
            matched.append({
                "drug_info": drug,
                "score": matched_score,
                "contraindication_warnings": c_warnings,
                "is_safe_for_user": len(c_warnings) == 0,
                "drugbank_id": drug.get("drugbank_id", ""),
                "drugbank_url": drug.get("drugbank_url", "https://go.drugbank.com/"),
                "mechanism_of_action": drug.get("mechanism_of_action", ""),
                "webmd_ref": drug.get("webmd_ref", "https://symptoms.webmd.com/")
            })

    matched.sort(key=lambda x: (x["is_safe_for_user"], x["score"]), reverse=True)

    # Bước 4: Gọi Gemini tư vấn Dược lâm sàng sâu & đề xuất danh mục thuốc phù hợp
    ai_advice, suggested_drugs = _consult_with_gemini(
        query=query,
        conditions=all_conditions,
        age=eff_age,
        gender=eff_gender,
        matched_kb=matched,
        red_flags=red_flags
    )
    # FIX: gắn khuyến cáo y tế vào mọi phản hồi tư vấn (cả nhánh Gemini lẫn fallback).
    if MED_DISCLAIMER.strip() not in ai_advice:
        ai_advice = ai_advice.rstrip() + MED_DISCLAIMER

    # Bước 5: Hồ sơ tóm tắt người dùng theo mô hình WebMD
    profile_tags = []
    if eff_age is not None:
        profile_tags.append(f"{eff_age} tuổi")
    if eff_gender:
        g_name = "Nam" if eff_gender == "male" else ("Nữ (Thai kỳ/Cho con bú)" if "pregnant" in eff_gender.lower() else "Nữ")
        profile_tags.append(g_name)
    if all_conditions:
        profile_tags.append(f"Tiền sử: {', '.join(all_conditions)}")

    triage_summary = f"Đối tượng: { ' • '.join(profile_tags) if profile_tags else 'Chưa cung cấp hồ sơ' }"

    all_display_drugs = suggested_drugs if suggested_drugs else matched

    return {
        "status": "success",
        "is_safe": all(m["is_safe_for_user"] for m in all_display_drugs) if all_display_drugs else (len(red_flags) == 0),
        "total_matched": len(matched),
        "triage_summary": triage_summary,
        "extracted_profile": {
            "age": eff_age,
            "gender": eff_gender,
            "conditions": all_conditions,
            "newly_added_conditions": new_conds
        },
        "red_flags": red_flags,
        "ai_advice": ai_advice,
        "results": matched,
        "suggested_drugs": suggested_drugs,
        "disclaimer": MED_DISCLAIMER.strip(),
    }


