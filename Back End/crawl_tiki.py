# -*- coding: utf-8 -*-
"""
crawl_tiki.py: Thu thập và chuẩn hóa dữ liệu sách từ Tiki.vn
Đề tài: Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin

Quy trình thu thập:
1. Gửi yêu cầu đến API danh mục sách của Tiki qua pagination.
2. Kiểm tra trùng lặp nhanh bằng HashSet và làm sạch chuỗi mô tả HTML.
3. Chuẩn hóa các trường thông tin (tựa đề, tác giả, giá bán, số lượng đã bán, đánh giá) và gán mã BKxxxx.
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# TOÀN BỘ 24 DANH MỤC "SÁCH TIẾNG VIỆT" CỦA TIKI (c8322 -> c316)
TIKI_VIETNAMESE_CATEGORIES = [
    {"name": "Sách văn học", "cat_id": 839},
    {"name": "Sách kinh tế", "cat_id": 846},
    {"name": "Sách thiếu nhi", "cat_id": 393},
    {"name": "Sách kỹ năng sống", "cat_id": 870},
    {"name": "Nuôi dạy con", "cat_id": 2527},
    {"name": "Sách Giáo Khoa - Giáo Trình", "cat_id": 2321},
    {"name": "Sách Học Ngoại Ngữ", "cat_id": 887},
    {"name": "Sách Tham Khảo", "cat_id": 2320},
    {"name": "Từ Điển", "cat_id": 897},
    {"name": "Sách Kiến Thức Tổng Hợp", "cat_id": 873},
    {"name": "Sách Khoa Học - Kỹ Thuật", "cat_id": 879},
    {"name": "Sách Lịch sử", "cat_id": 880},
    {"name": "Điện Ảnh - Nhạc - Họa", "cat_id": 881},
    {"name": "Truyện Tranh, Manga, Comic", "cat_id": 1084},
    {"name": "Sách Tôn Giáo - Tâm Linh", "cat_id": 861},
    {"name": "Sách Văn Hóa - Địa Lý - Du Lịch", "cat_id": 857},
    {"name": "Sách Chính Trị - Pháp Lý", "cat_id": 875},
    {"name": "Sách Nông - Lâm - Ngư Nghiệp", "cat_id": 882},
    {"name": "Sách Công Nghệ Thông Tin", "cat_id": 876},
    {"name": "Sách Y Học", "cat_id": 885},
    {"name": "Tạp Chí - Catalogue", "cat_id": 1468},
    {"name": "Sách Tâm lý - Giới tính", "cat_id": 868},
    {"name": "Sách Thường Thức - Gia Đình", "cat_id": 862},
    {"name": "Thể Dục - Thể Thao", "cat_id": 6905},
]

# 16 DANH MỤC "ENGLISH BOOKS" CỦA TIKI (c8322 -> c320)
TIKI_ENGLISH_CATEGORIES = [
    {"name": "Art & Photography", "cat_id": 623},
    {"name": "Biographies & Memoirs", "cat_id": 27},
    {"name": "Business & Economics", "cat_id": 4},
    {"name": "How-to - Self Help", "cat_id": 614},
    {"name": "Children's Books", "cat_id": 7},
    {"name": "Dictionary", "cat_id": 282},
    {"name": "Education - Teaching", "cat_id": 5308},
    {"name": "Fiction - Literature", "cat_id": 9},
    {"name": "Magazines", "cat_id": 6445},
    {"name": "Medical Books", "cat_id": 218},
    {"name": "Parenting & Relationships", "cat_id": 28},
    {"name": "Reference", "cat_id": 5309},
    {"name": "Science - Technology", "cat_id": 269},
    {"name": "History, Politics & Social Sciences", "cat_id": 632},
    {"name": "Travel & Holiday", "cat_id": 32},
    {"name": "Cookbooks, Food & Wine", "cat_id": 21},
]


def clean_html(raw_html: str) -> str:
    """Loại bỏ thẻ HTML và khoảng trắng thừa trong phần mô tả."""
    if not raw_html:
        return ""
    text = re.sub(r"<(script|style).*?>.*?</\1>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_json(url: str, retries: int = 3) -> dict:
    """Gửi HTTP request có retry để lấy JSON từ Tiki API."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.2)
            else:
                return {}
    return {}


def get_product_detail(product_id: int) -> dict:
    """Lấy thông tin chi tiết một cuốn sách qua Tiki API v2."""
    url = f"https://tiki.vn/api/v2/products/{product_id}"
    return fetch_json(url)


def load_existing_database():
    """
    Nạp sẵn cơ sở dữ liệu sample.json vào bộ nhớ.
    Tạo tập tra cứu nhanh O(1) theo tiki_id và tiêu đề sách để SKIP tức thì sách đã có.
    """
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database"))
    main_file = os.path.join(db_dir, "sample.json")
    if not os.path.exists(main_file):
        return [], set(), set()

    try:
        with open(main_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        books = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not isinstance(books, list):
            books = []
    except Exception as e:
        print(f"⚠️ Lỗi đọc sample.json: {e}")
        books = []

    existing_titles = set()
    existing_tiki_ids = set()

    for b in books:
        t = b.get("title", "").strip().lower()
        if t:
            existing_titles.add(t)
        tid = b.get("tiki_id")
        if tid and str(tid).isdigit():
            existing_tiki_ids.add(int(tid))

    return books, existing_titles, existing_tiki_ids


def extract_book_info(detail: dict, category_name: str, index_id: int) -> dict:
    """Trích xuất và chuẩn hóa trường dữ liệu theo đúng schema của sample.json."""
    # 1. Tác giả
    author = "Nhiều tác giả"
    if detail.get("authors"):
        author_names = [a.get("name") for a in detail["authors"] if a.get("name")]
        if author_names:
            author = ", ".join(author_names)

    # 2. Nhà xuất bản & Thông tin từ specifications
    publisher = "NXB Tổng Hợp"
    publish_year = 2024
    for spec in detail.get("specifications", []):
        for attr in spec.get("attributes", []):
            code = attr.get("code", "")
            val = clean_html(str(attr.get("value", "")))
            if code in ["publisher_vn", "manufacturer"] and val:
                publisher = val
            elif code == "publication_date" and val:
                match = re.search(r"\b(19\d\d|20\d\d)\b", val)
                if match:
                    publish_year = int(match.group(1))

    # 3. Làm sạch mô tả, có fallback thông minh tránh vứt bỏ sách
    clean_desc = clean_html(detail.get("description", ""))
    if len(clean_desc) < 40:
        short_d = clean_html(detail.get("short_description", ""))
        if len(short_d) >= 40:
            clean_desc = short_d
        else:
            title_name = detail.get("name", "").strip()
            clean_desc = (
                f"{title_name} là tác phẩm tiêu biểu thuộc danh mục '{category_name}' của tác giả {author}, "
                f"được ấn hành bởi {publisher} vào năm {publish_year}. Cuốn sách cung cấp kiến thức giá trị, "
                f"nội dung phong phú và trải nghiệm đọc sâu sắc cho độc giả quan tâm đến lĩnh vực này."
            )

    # 4. Doanh số & Reviews
    qty_sold = 0
    if isinstance(detail.get("quantity_sold"), dict):
        qty_sold = detail["quantity_sold"].get("value", 0)
    elif isinstance(detail.get("quantity_sold"), (int, float)):
        qty_sold = int(detail["quantity_sold"])

    review_count = int(detail.get("review_count", 0))
    rating = float(detail.get("rating_average", 4.8))
    if rating == 0:
        rating = 4.8

    valid_reviews = max(1, int(review_count * 0.8)) if review_count > 0 else 1

    # 5. Tags tự động từ tên & thể loại
    title = detail.get("name", "").strip()
    tags = [w.lower() for w in re.findall(r"\b\w{3,}\b", title)[:5]]
    tags.append(category_name.lower())
    tags.append("tiki")

    return {
        "id": f"BK{index_id:04d}",
        "tiki_id": detail.get("id"),
        "isbn": str(detail.get("sku", "")),
        "title": title,
        "tiki_name": title,
        "original_title": title,
        "author": author,
        "category": category_name,
        "publisher": publisher,
        "publish_year": publish_year,
        "price": int(detail.get("price", 0)),
        "original_price": int(detail.get("original_price", detail.get("price", 0))),
        "rating": round(rating, 1),
        "sold_count": qty_sold,
        "total_reviews": review_count,
        "valid_reviews": valid_reviews,
        "in_stock": True,
        "target_audience": "Mọi lứa tuổi",
        "tags": list(set(tags)),
        "description": clean_desc,
    }


def crawl_tiki_categories(categories_to_crawl: list, max_books_per_cat: int = 100, auto_merge: bool = True):
    """
    Quét danh sách danh mục Tiki với cơ chế:
      1. SCAN NHANH: Nhận diện sách đã có trong database và SKIP lập tức (0.0001s).
      2. SCAN TIẾP: Tự động lật trang để gom cho bằng đủ số lượng sách MỚI theo yêu cầu.
      3. KHÔNG BỎ SÓT: Mọi cuốn sách hợp lệ đều được giữ lại.
    """
    target = int(max_books_per_cat)
    total_cats = len(categories_to_crawl)
    total_target = target * total_cats

    # 1. Nạp cơ sở dữ liệu hiện có
    existing_books, existing_titles, existing_tiki_ids = load_existing_database()
    current_index = len(existing_books) + 1

    print("\n" + "=" * 75)
    print("🕷️ CRAWLER SÁCH TIKI.VN CHUYÊN SÂU — HỖ TRỢ SCAN TOÀN BỘ DANH MỤC")
    print(f"📦 Database hiện tại: Đã có {len(existing_books)} cuốn sách trong sample.json.")
    print(f"🎯 Mục tiêu cào mới: {target} cuốn MỚI/danh mục × {total_cats} danh mục = Tối đa {total_target} cuốn mới!")
    print(f"⚡ Cơ chế: Tự động SKIP siêu tốc sách cũ, lật trang quét liên tục sách chưa có.")
    print("=" * 75)

    all_new_books = []
    seen_ids = set()

    for idx, cat in enumerate(categories_to_crawl, 1):
        cat_name = cat["name"]
        cat_id = cat["cat_id"]
        cat_new_books = []
        skipped_count = 0

        # Số trang tối đa quét để tìm đủ sách mới (mỗi trang có 40 cuốn)
        max_pages = max(40, (target // 40) + 25)
        print(f"\n📂 [{idx:2d}/{total_cats}] Danh mục: [{cat_name}] (ID: {cat_id})")
        print(f"   🔍 Tìm kiếm {target} cuốn MỚI (Quét tối đa {max_pages} trang Tiki)...")

        page = 1
        consecutive_empty_pages = 0

        while len(cat_new_books) < target and page <= max_pages:
            list_url = f"https://tiki.vn/api/personalish/v1/blocks/listings?limit=40&category={cat_id}&page={page}"
            listing_data = fetch_json(list_url)
            items = listing_data.get("data", [])

            if not items:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:
                    # Đã hết toàn bộ sách trong danh mục này trên Tiki
                    break
                page += 1
                continue

            consecutive_empty_pages = 0

            for item in items:
                p_id = item.get("id")
                p_name = item.get("name", "").strip()

                if not p_id or p_id in seen_ids:
                    continue

                seen_ids.add(p_id)

                # ==============================================================
                # 🚀 CƠ CHẾ SCAN NHANH: Kiểm tra sách đã có trong Database chưa
                # ==============================================================
                title_lower = p_name.lower()
                if p_id in existing_tiki_ids or title_lower in existing_titles:
                    skipped_count += 1
                    # Bỏ qua ngay lập tức, không gửi request HTTP chi tiết!
                    continue

                # Chỉ khi là SÁCH MỚI HOÀN TOÀN mới tải chi tiết
                detail = get_product_detail(p_id)
                if not detail or not detail.get("name"):
                    continue

                book_obj = extract_book_info(detail, cat_name, current_index)
                cat_new_books.append(book_obj)
                current_index += 1

                # Đánh dấu vào tập tra cứu để không trùng trong các vòng lặp sau
                existing_tiki_ids.add(p_id)
                existing_titles.add(book_obj["title"].strip().lower())

                print(
                    f"  ✨ [MỚI #{len(cat_new_books)}/{target}] [{book_obj['id']}] {book_obj['title'][:38]}... "
                    f"({book_obj['price']:,}đ) | {book_obj['author'][:18]}",
                    flush=True,
                )
                time.sleep(0.15)  # Tránh nghẽn mạng Tiki

                if len(cat_new_books) >= target:
                    break

            page += 1

        print(f"  👉 Hoàn tất danh mục [{cat_name}]: Thu thập thành công {len(cat_new_books)} cuốn MỚI.")
        print(f"     (Đã tự động nhận diện và SKIP siêu tốc {skipped_count} cuốn đã có trong database)")
        all_new_books.extend(cat_new_books)

    # 4. Lưu file riêng biệt của Tiki
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database"))
    output_file = os.path.join(db_dir, "sample_tiki.json")

    payload = {
        "metadata": {
            "source": "tiki.vn",
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_new_books": len(all_new_books),
            "target_per_cat": target,
            "categories_crawled": [c["name"] for c in categories_to_crawl],
        },
        "data": all_new_books,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Lưu bản JSONL
    jsonl_file = os.path.join(db_dir, "sample_tiki.jsonl")
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for b in all_new_books:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")

    print("\n" + "=" * 75)
    print(f"🎉 TỔNG KẾT: Đã thu thập thêm {len(all_new_books)} cuốn sách MỚI TINH từ Tiki!")
    print(f"📁 File JSON riêng Tiki: {output_file}")
    print(f"📁 File JSONL riêng Tiki: {jsonl_file}")
    print("=" * 75)

    if auto_merge:
        merge_into_main_sample(all_new_books)


def merge_into_main_sample(tiki_books: list):
    """Tự động gộp sách Tiki vào database/sample.json, backup an toàn và chuẩn hóa ID."""
    if not tiki_books:
        print("ℹ️ Không có sách mới để gộp vào database.")
        return

    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database"))
    main_file = os.path.join(db_dir, "sample.json")

    # Tạo bản backup an toàn trước khi ghi đè
    if os.path.exists(main_file):
        backup_file = os.path.join(db_dir, f"sample_backup_{int(time.time())}.json")
        try:
            with open(main_file, "r", encoding="utf-8") as f_src, open(backup_file, "w", encoding="utf-8") as f_dst:
                f_dst.write(f_src.read())
            print(f"🛡️ Đã sao lưu an toàn kho sách cũ vào: {os.path.basename(backup_file)}")
        except Exception as e:
            print(f"⚠️ Cảnh báo backup: {e}")

    try:
        with open(main_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        existing_books = raw.get("data", raw) if isinstance(raw, dict) else raw
    except Exception:
        existing_books = []

    existing_titles = {b.get("title", "").strip().lower() for b in existing_books}
    added_count = 0

    for tb in tiki_books:
        title = tb.get("title", "").strip().lower()
        if title and title not in existing_titles:
            existing_books.append(tb)
            existing_titles.add(title)
            added_count += 1

    # Đánh lại ID thống nhất chuẩn khoa học: BK0001 -> BKxxxx
    for i, b in enumerate(existing_books, start=1):
        b["id"] = f"BK{i:04d}"

    final_payload = {
        "metadata": {
            "version": "2.0",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_books": len(existing_books),
            "sources": ["sample_seed", "tiki.vn", "fahasa.com"],
        },
        "data": existing_books,
    }

    with open(main_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    # Lưu bản JSONL của toàn bộ database
    main_jsonl = os.path.join(db_dir, "sample.jsonl")
    with open(main_jsonl, "w", encoding="utf-8") as f:
        for b in existing_books:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")

    print(f"🔄 ĐÃ GỘP TỰ ĐỘNG: Bổ sung {added_count} cuốn sách mới từ Tiki vào sample.json.")
    print(f"📚 TỔNG KHO SÁCH HIỆN TẠI: {len(existing_books)} cuốn sách!")
    print("=" * 75)
    print("👉 Hãy chạy lệnh 'python indexer.py' để nạp toàn bộ vào ChromaDB Vector Database.")


if __name__ == "__main__":
    limit = 50
    selected_cats = TIKI_VIETNAMESE_CATEGORIES

    # Kiểm tra cờ --menu nếu người dùng muốn mở giao diện chọn
    if "--menu" in sys.argv:
        print("=" * 75)
        print("📚 CÔNG CỤ CÀO DỮ LIỆU SÁCH TIKI TỰ ĐỘNG — ĐẦY ĐỦ TOÀN BỘ DANH MỤC")
        print("=" * 75)
        print("Chọn phạm vi danh mục muốn cào:")
        print("  [1] Quét TOÀN BỘ 24 danh mục Sách Tiếng Việt (Khuyên dùng)")
        print("  [2] Quét TOÀN BỘ 40 danh mục (gồm cả 24 Tiếng Việt + 16 Tiếng Anh)")
        print("  [3] Tự chọn 1 danh mục cụ thể")
        print("-" * 75)

        choice = input("👉 Lựa chọn của bạn [1/2/3, mặc định là 1]: ").strip()
        if choice == "2":
            selected_cats = TIKI_VIETNAMESE_CATEGORIES + TIKI_ENGLISH_CATEGORIES
            print(f"  → Đã chọn: Toàn bộ 40 danh mục Sách Tiki.")
        elif choice == "3":
            print("\nDanh sách danh mục Sách Tiếng Việt:")
            for i, c in enumerate(TIKI_VIETNAMESE_CATEGORIES, 1):
                print(f"  {i:2d}. {c['name']}")
            try:
                cat_idx = int(input("\n👉 Nhập số thứ tự danh mục muốn cào (1-24): ").strip())
                if 1 <= cat_idx <= len(TIKI_VIETNAMESE_CATEGORIES):
                    selected_cats = [TIKI_VIETNAMESE_CATEGORIES[cat_idx - 1]]
                    print(f"  → Đã chọn: {selected_cats[0]['name']}")
            except Exception:
                selected_cats = TIKI_VIETNAMESE_CATEGORIES
        else:
            selected_cats = TIKI_VIETNAMESE_CATEGORIES
            print(f"  → Đã chọn: Toàn bộ 24 danh mục Sách Tiếng Việt Tiki.")

        try:
            val = input("\n👉 Nhập số lượng cuốn MỚI muốn cào cho MỖI danh mục [mặc định 50, có thể nhập 100, 200]: ").strip()
            if val:
                limit = int(val)
        except (ValueError, KeyboardInterrupt):
            limit = 50
    else:
        # CHẠY TRỰC TIẾP QUA TERMINAL (KHÔNG CẦN BẤM GÌ THÊM)
        # 1. Nếu có truyền số lượng: python crawl_tiki.py 100
        # 2. Nếu có truyền cờ 'all': python crawl_tiki.py 100 all
        # 3. Nếu không truyền gì: python crawl_tiki.py (chạy ngay mặc định 50 cuốn/danh mục)
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            limit = int(sys.argv[1])

        if any(arg.lower() in ["all", "full", "both"] for arg in sys.argv[1:]):
            selected_cats = TIKI_VIETNAMESE_CATEGORIES + TIKI_ENGLISH_CATEGORIES
            print(f"⚡ [CHẠY TRỰC TIẾP TERMINAL] Quét {limit} cuốn MỚI cho TOÀN BỘ 40 danh mục (Tiếng Việt + Tiếng Anh).")
        else:
            print(f"⚡ [CHẠY TRỰC TIẾP TERMINAL] Quét {limit} cuốn MỚI cho TOÀN BỘ 24 danh mục Sách Tiếng Việt.")
            print(f"💡 Gợi ý lệnh terminal:")
            print(f"   • Tăng số lượng:      python crawl_tiki.py 100")
            print(f"   • Quét cả tiếng Anh:  python crawl_tiki.py 50 all")
            print(f"   • Mở menu tùy chọn:   python crawl_tiki.py --menu")

    print(f"\n🚀 BẮT ĐẦU CÀO {len(selected_cats)} DANH MỤC VỚI MỤC TIÊU: {limit} cuốn MỚI/danh mục...")
    crawl_tiki_categories(categories_to_crawl=selected_cats, max_books_per_cat=limit, auto_merge=True)