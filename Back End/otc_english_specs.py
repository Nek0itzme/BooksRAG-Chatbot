# -*- coding: utf-8 -*-
"""
otc_english_specs.py — Standardized Plain English specifications for OTC Medicines.
Maps Vietnamese medical terms, categories, symptoms, and contraindications directly
into clear, friendly Plain English (CEFR A2-B1) without relying on fragile machine translation.
"""

from typing import Dict, Any, List

# Standard Category Translations
CATEGORY_EN_MAP = {
    "Thuốc giảm đau - hạ sốt không kê đơn (OTC)": "Pain Relief & Fever Reducer (OTC)",
    "Thuốc giảm đau hạ sốt dạng sủi không kê đơn (OTC)": "Effervescent Pain & Fever Relief (OTC)",
    "Thuốc giảm đau hạ sốt tăng cường không kê đơn (OTC)": "Enhanced Pain & Fever Relief (OTC)",
    "Thuốc kháng viêm hạ sốt giảm đau không steroid (NSAID)": "Pain, Fever & Anti-Inflammatory (NSAID)",
    "Thuốc trị cảm cúm nghẹt mũi không kê đơn (OTC)": "Cold, Flu & Nasal Decongestant (OTC)",
    "Thuốc trị cảm cúm, sổ mũi không kê đơn (OTC)": "Cold & Runny Nose Relief (OTC)",
    "Thuốc cảm cúm kháng dị ứng không kê đơn (OTC)": "Cold, Allergy & Decongestant (OTC)",
    "Thuốc kháng histamin chống dị ứng không kê đơn (OTC)": "Allergy & Itch Relief (OTC)",
    "Thuốc chống dị ứng mẩn ngứa không kê đơn (OTC)": "Anti-Allergy & Hives Relief (OTC)",
    "Thuốc chống dị ứng thế hệ mới không gây buồn ngủ (OTC)": "Non-Drowsy Allergy Relief (OTC)",
    "Thuốc kháng histamin giảm dị ứng thế hệ 1 (OTC)": "Nighttime Allergy & Itch Relief (OTC)",
    "Thuốc ho thảo dược long đờm không kê đơn (OTC)": "Herbal Cough & Mucus Relief (OTC)",
    "Thuốc tiêu nhầy long đờm phế quản không kê đơn (OTC)": "Chest Congestion & Mucus Thinner (OTC)",
    "Thuốc long đờm tiêu dịch nhầy đường hô hấp (OTC)": "Mucus Clearing & Cough Relief (OTC)",
    "Siro ho thảo dược tiêu nhầy chống co thắt (OTC)": "Herbal Cough Syrup & Bronchial Soother (OTC)",
    "Thuốc ức chế phản xạ ho cắt cơn ho khan (OTC)": "Dry Cough Suppressant (OTC)",
    "Thuốc ho đông dược bổ phế hóa đờm (OTC)": "Traditional Herbal Lung & Cough Syrup (OTC)",
    "Viên ngậm sát trùng giảm đau họng tại chỗ (OTC)": "Sore Throat Sucking Lozenges (OTC)",
    "Thuốc co mạch chống nghẹt mũi tại chỗ cho trẻ em (OTC)": "Children's Nasal Decongestant Drops (OTC)",
    "Thuốc xịt mũi co mạch giảm nghẹt tức thì người lớn (OTC)": "Instant Nasal Decongestant Spray (OTC)",
    "Dung dịch vệ sinh và làm sạch khoang mũi đẳng trương (OTC)": "Daily Sea Water Nasal Cleanser (OTC)",
    "Dung dịch nhỏ mắt mũi sinh lý an toàn cho mọi lứa tuổi (OTC)": "Pure Saline Eye & Nose Drops (0.9% NaCl)",
    "Thuốc bù nước và cân bằng điện giải thẩm thấu thấp (OTC)": "Oral Rehydration & Electrolyte Solution (OTC)",
    "Men vi sinh vi khuẩn có lợi đường ruột (OTC)": "Gut Probiotics (Healthy Live Spores)",
    "Cốm vi sinh bổ sung lợi khuẩn và vi chất dinh dưỡng (OTC)": "Probiotics & Essential Micronutrients (OTC)",
    "Thuốc trị tiêu chảy không kê đơn (OTC)": "Anti-Diarrheal & Gut Cleanser (OTC)",
    "Thuốc bao phủ niêm mạc & cầm tiêu chảy không kê đơn (OTC)": "Gut Lining Protector & Anti-Diarrheal (OTC)",
    "Thuốc làm giảm nhu động cầm tiêu chảy cấp (OTC)": "Acute Diarrhea Controller (OTC)",
    "Thuốc kháng acid & chống trào ngược dạ dày (OTC)": "Antacid & Heartburn Barrier (OTC)",
    "Thuốc kháng acid dạ dày dạng gel bảo vệ niêm mạc (OTC)": "Stomach Lining Barrier Gel (OTC)",
    "Thuốc dạ dày chữ Y kháng acid giảm trào ngược (OTC)": "Fast-Acting Antacid Sachet (OTC)",
    "Thuốc kháng acid kết hợp chống đầy hơi sình bụng (OTC)": "Antacid & Gas Relief Chewable (OTC)",
    "Thuốc chống nôn và điều hòa nhu động tiêu hóa (OTC)": "Anti-Nausea & Digestion Normalizer (OTC)",
    "Thuốc nhuận tràng thẩm thấu làm mềm phân an toàn (OTC)": "Gentle Stool Softener Laxative (OTC)",
    "Thuốc nhuận tràng kích thích nhu động đại tràng (OTC)": "Overnight Stimulant Laxative (OTC)",
    "Thuốc hỗ trợ tiêu hóa mật và nhuận tràng thẩm thấu (OTC)": "Digestive Support & Mild Laxative (OTC)",
    "Thuốc phá bọt khí điều trị chứng đầy hơi chướng bụng (OTC)": "Anti-Gas & Bloating Relief (OTC)",
    "Enzyme men tiêu hóa tinh bột và đạm (OTC)": "Natural Digestive Enzymes (OTC)",
    "Thuốc chống say tàu xe và nôn nao tiền đình (OTC)": "Motion Sickness & Anti-Nausea (OTC)",
    "Miếng dán và gel giảm đau kháng viêm tại chỗ ngoài da (OTC)": "Pain Relief Patch & Gel (OTC)",
    "Gel bôi kháng viêm giảm đau cơ xương khớp ngoài da (OTC)": "Topical Muscle & Joint Anti-Inflammatory (OTC)",
    "Dung dịch sát khuẩn ngoài da phổ rộng không rát buốt (OTC)": "Antiseptic Skin Solution (OTC)",
    "Dung dịch sủi bọt rửa sạch cơ học vết thương hở (OTC)": "Wound Cleansing Hydrogen Peroxide (3%)",
    "Dung dịch sát trùng da lành và dụng cụ y tế (OTC)": "Medical Rubbing Alcohol (70% Ethanol)",
    "Mỡ bôi phục hồi tái tạo da và chống hăm lành tính (OTC)": "Healing & Diaper Rash Ointment (OTC)",
    "Kem bôi trị nấm da ngoài da phổ rộng (OTC)": "Broad-Spectrum Antifungal Cream (OTC)",
    "Kem bôi trị vi nấm và viêm da tiết bã (OTC)": "Dandruff & Antifungal Cream (OTC)",
    "Thuốc mỡ tra mắt điều trị nhiễm khuẩn bề mặt mắt (OTC)": "Eye Antibacterial Ointment (1% Tetracycline)",
    "Gel gây tê và kháng viêm trị nhiệt loét niêm mạc miệng (OTC)": "Mouth Ulcer & Canker Sore Gel (OTC)",
    "Dung dịch nhỏ mắt kháng khuẩn giảm viêm ngứa (OTC)": "Antibacterial & Itch-Relief Eye Drops (OTC)",
    "Nước mắt nhân tạo bôi trơn và dưỡng ẩm giác mạc cao cấp (OTC)": "Dry Eye Lubricant & Artificial Tears (OTC)",
    "Vitamin bổ sung không kê đơn (OTC)": "Daily Essential Vitamin Supplement (OTC)",
    "Viên sủi bổ sung đa vi chất và giải tỏa căng thẳng thần kinh (OTC)": "Multivitamin & Energy Effervescent (OTC)",
    "Viên nang dầu cá bổ mắt và hỗ trợ tim mạch (OTC)": "Omega-3 Fish Oil (Eye & Heart Health)",
    "Thuốc tăng cường tuần hoàn máu não thảo dược (OTC)": "Ginkgo Biloba Brain Circulation Support (OTC)",
    "Thuốc bổ sung khoáng chất canxi và vitamin D chống loãng xương (OTC)": "Calcium & Vitamin D3 Bone Health (OTC)",
    "Khoáng chất kẽm phục hồi niêm mạc ruột và tăng đề kháng (OTC)": "Zinc Gluconate (Immune & Gut Health)",
    "Thuốc trợ tĩnh mạch điều trị cơn trĩ cấp và suy tĩnh mạch (OTC)": "Vein Support & Hemorrhoid Relief (OTC)",
    "Dung dịch xịt xua đuổi côn trùng và phòng muỗi đốt ngoài da (OTC)": "Mosquito & Insect Repellent Spray (OTC)"
}

# Symptom translations to Plain English
SYMPTOM_MAP = {
    "sốt": "Fever",
    "sốt cao": "High fever",
    "đau đầu": "Headache",
    "đau răng": "Toothache",
    "đau nhức cơ bắp": "Muscle aches",
    "đau nhức cơ thể": "Body aches",
    "tiêu chảy": "Diarrhea",
    "đau quặn bụng": "Stomach cramps",
    "đau bụng": "Stomach pain",
    "đi ngoài phân lỏng": "Watery stool",
    "nhiễm khuẩn ruột": "Mild gut infection",
    "rối loạn tiêu hóa": "Upset stomach / indigestion",
    "mệt mỏi": "Fatigue / tiredness",
    "giảm đề kháng": "Low immunity",
    "chảy máu chân răng": "Bleeding gums",
    "phục hồi sức khỏe": "Post-illness recovery",
    "ợ chua": "Acid reflux / heartburn",
    "ợ nóng": "Burning sensation in chest",
    "đau rát ngực": "Chest burning",
    "trào ngược dạ dày": "Stomach acid reflux",
    "khó tiêu": "Indigestion",
    "ho có đờm": "Cough with mucus",
    "đau họng": "Sore throat",
    "rát cổ": "Scratchy / irritated throat",
    "khản giọng": "Hoarse voice",
    "cảm lạnh": "Common cold",
    "nghẹt mũi": "Stuffy / blocked nose",
    "sổ mũi": "Runny nose",
    "hắt hơi": "Sneezing",
    "mẩn ngứa": "Skin itchiness",
    "mề đay": "Hives / rash",
    "dị ứng": "Allergies",
    "say xe": "Motion sickness",
    "buồn nôn": "Nausea / vomiting",
    "táo bón": "Constipation",
    "khô mắt": "Dry eyes"
}

def translate_symptom(sym: str) -> str:
    s_clean = sym.strip().lower()
    for k, v in SYMPTOM_MAP.items():
        if k in s_clean:
            return v
    return sym.title()

def to_english_specs(drug: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo bản specs tiếng Anh đơn giản hóa (Plain English) từ thuốc gốc."""
    d_en = dict(drug)
    d_en["trade_name"] = drug.get("trade_name", "")
    
    # Category
    orig_cat = drug.get("category", "")
    d_en["category"] = CATEGORY_EN_MAP.get(orig_cat, "Over-The-Counter Medicine (OTC)")
    
    # Symptoms
    orig_syms = drug.get("common_symptoms", [])
    d_en["common_symptoms"] = [translate_symptom(s) for s in orig_syms]
    
    # WebMD Symptoms
    orig_webmd = drug.get("webmd_symptoms", [])
    d_en["webmd_symptoms"] = [translate_symptom(s) for s in orig_webmd]

    # Contraindications to Plain English
    en_contras = []
    for c in drug.get("contraindications", []):
        cl = c.lower()
        if "suy gan" in cl or "viêm gan" in cl:
            en_contras.append("People with severe liver disease or liver failure")
        elif "g6pd" in cl:
            en_contras.append("People with G6PD enzyme deficiency (risk of red blood cell breakdown)")
        elif "dị ứng" in cl or "mẫn cảm" in cl:
            en_contras.append("Anyone allergic to the active ingredient")
        elif "mang thai" in cl or "thai kỳ" in cl:
            en_contras.append("Pregnant women (especially during the 3rd trimester)")
        elif "dạ dày" in cl or "loét" in cl or "xuất huyết" in cl:
            en_contras.append("People with active stomach ulcers or history of stomach bleeding")
        elif "thận" in cl or "sỏi" in cl:
            en_contras.append("People with severe kidney failure or kidney stones")
        elif "huyết áp" in cl or "mạch vành" in cl:
            en_contras.append("People with severe high blood pressure or coronary heart disease")
        elif "hen suyễn" in cl or "suy hô hấp" in cl:
            en_contras.append("People with asthma or severe breathing difficulties")
        elif "tiền liệt tuyến" in cl or "bí tiểu" in cl:
            en_contras.append("Men with enlarged prostate or trouble urinating")
        elif "glaucoma" in cl or "nhãn áp" in cl:
            en_contras.append("People with narrow-angle glaucoma (high eye pressure)")
        elif "trẻ" in cl or "tuổi" in cl:
            en_contras.append(f"Children under {drug.get('min_age', 0)} years old")
        else:
            en_contras.append(c)
    d_en["contraindications"] = en_contras

    # Dangerous interactions to Plain English
    en_inters = []
    for inter in drug.get("dangerous_interactions", []):
        il = inter.lower()
        if "rượu bia" in il:
            en_inters.append("Alcohol (greatly increases liver toxicity and dizziness risk)")
        elif "paracetamol" in il:
            en_inters.append("Other cold/flu medicines containing Paracetamol (risk of accidental overdose)")
        elif "chống đông" in il or "warfarin" in il or "aspirin" in il:
            en_inters.append("Blood thinners like Warfarin or Aspirin (increases bleeding risk)")
        elif "an thần" in il or "thuốc ngủ" in il:
            en_inters.append("Sleeping pills or tranquilizers (causes extreme drowsiness)")
        elif "kháng sinh" in il or "tetracyclin" in il or "sắt" in il:
            en_inters.append("Antibiotics or iron supplements (take at least 2 hours apart)")
        elif "ức chế mao" in il or "mao" in il:
            en_inters.append("MAO inhibitors or antidepressant medications")
        else:
            en_inters.append(inter)
    d_en["dangerous_interactions"] = en_inters

    # Safe usage note to Plain English
    su = drug.get("safe_usage_note", "")
    sul = su.lower()
    if "4-6 giờ" in sul or "4 đến 6 giờ" in sul:
        d_en["safe_usage_note"] = "Wait at least 4 to 6 hours between doses. Do not exceed the maximum daily limit."
    elif "sau ăn" in sul or "sau bữa ăn" in sul:
        d_en["safe_usage_note"] = "Take after a full meal with a full glass of water to protect your stomach."
    elif "trước khi đi ngủ" in sul:
        d_en["safe_usage_note"] = "Take in the evening before bedtime with plenty of water."
    elif "không dùng quá" in sul or "5-7 ngày" in sul:
        d_en["safe_usage_note"] = "Do not use for more than 5 to 7 days in a row without a doctor's advice."
    elif "ngậm" in sul:
        d_en["safe_usage_note"] = "Slowly dissolve in mouth every 2 to 3 hours when throat feels painful."
    elif "bôi" in sul or "xoa" in sul:
        d_en["safe_usage_note"] = "Apply a thin layer to clean, dry skin 2 to 3 times daily. Wash hands after use."
    elif "nhỏ" in sul or "mắt" in sul or "mũi" in sul:
        d_en["safe_usage_note"] = "Instill 1 to 2 drops into each eye or nostril as needed. Do not touch nozzle to skin."
    else:
        d_en["safe_usage_note"] = "Follow product label guidelines. Consult a pharmacist if symptoms persist."

    # Mechanism of action to Plain English
    moa = drug.get("mechanism_of_action", "")
    moal = moa.lower()
    if "paracetamol" in moal or "prostaglandin" in moal:
        d_en["mechanism_of_action"] = "Acts on brain pain-control centers to lower fever and block pain sensations."
    elif "berberin" in moal:
        d_en["mechanism_of_action"] = "Natural herbal compound that stops bad intestinal bacteria and relieves diarrhea."
    elif "alginate" in moal or "bọt" in moal:
        d_en["mechanism_of_action"] = "Forms a soothing protective foam raft on top of stomach acid to stop acid reflux."
    elif "ibuprofen" in moal or "cox" in moal:
        d_en["mechanism_of_action"] = "Blocks inflammation enzymes to quickly reduce swelling, joint stiffness, and pain."
    elif "histamin" in moal:
        d_en["mechanism_of_action"] = "Blocks histamine receptors to relieve runny nose, sneezing, and itchy skin allergies."
    elif "acetylcysteine" in moal or "bromhexine" in moal or "thường xuân" in moal:
        d_en["mechanism_of_action"] = "Thins out thick lung mucus so coughs can clear the airways naturally."
    elif "dextromethorphan" in moal:
        d_en["mechanism_of_action"] = "Calms the cough reflex trigger in the brain to quickly stop dry, irritated coughs."
    elif "xylometazoline" in moal or "co mạch" in moal:
        d_en["mechanism_of_action"] = "Gently narrows swollen blood vessels in the nose to restore easy breathing in 2 minutes."
    elif "simethicone" in moal or "khí" in moal:
        d_en["mechanism_of_action"] = "Breaks down trapped gas bubbles in the stomach and gut to relieve bloating."
    elif "lactulose" in moal or "nhuận tràng" in moal:
        d_en["mechanism_of_action"] = "Attracts water into the intestines to soften hard stool and gently ease bowel movements."
    elif "clotrimazole" in moal or "ketoconazole" in moal or "nấm" in moal:
        d_en["mechanism_of_action"] = "Destroys fungal cell walls to clear athlete's foot, ringworm, and skin fungi."
    else:
        d_en["mechanism_of_action"] = "Certified therapeutic mechanism according to official pharmacopoeia reference."

    return d_en
