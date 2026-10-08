# -*- coding: utf-8 -*-
"""
crawl_all.py: Điều khiển quy trình thu thập dữ liệu và cập nhật chỉ mục Vector
Đề tài: Nghiên cứu và xây dựng hệ thống tư vấn sách tự động tích hợp RAG nhằm giảm thiểu sai lệch thông tin

Tác vụ chính:
1. Điều phối thu thập dữ liệu sách tự động từ Tiki và Fahasa.
2. Hợp nhất và chuẩn hóa cấu trúc dữ liệu lưu vào database/sample.json.
3. Kích hoạt indexer.py để đồng bộ cơ sở dữ liệu vector ChromaDB sau khi cào xong.
"""

import sys
import os
import subprocess
import time

sys.stdout.reconfigure(encoding="utf-8")


def run_command(cmd: list, desc: str) -> int:
    """Thực thi lệnh shell và đo lường thời gian xử lý."""
    print("\n" + "=" * 75)
    print(f"BẮT ĐẦU TIẾN TRÌNH: {desc}")
    print(f"Lệnh thực thi: {' '.join(cmd)}")
    print("=" * 75)
    start_time = time.time()
    res = subprocess.run(cmd)
    elapsed = time.time() - start_time
    if res.returncode == 0:
        print(f"\n✅ HOÀN THÀNH: {desc} (Thời gian xử lý: {elapsed:.1f}s)")
    else:
        print(f"\n⚠️ CẢNH BÁO: {desc} kết thúc với mã lỗi {res.returncode}")
    return res.returncode


def main():
    target_source = "all"
    limit = 50

    # Phân tích tham số dòng lệnh (CLI Argument Parsing)
    args = sys.argv[1:]
    for arg in args:
        if arg.isdigit():
            limit = int(arg)
        elif arg.lower() in ["tiki", "fahasa", "all"]:
            target_source = arg.lower()

    print("=" * 75)
    print("TRÌNH ĐIỀU KHIỂN THU THẬP DỮ LIỆU & ĐỒNG BỘ VECTOR DATABASE")
    print(f"Chế độ: Nguồn '{target_source.upper()}' | Mục tiêu: {limit} cuốn mới / danh mục")
    print("=" * 75)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    # 1. Thu thập dữ liệu Tiki
    if target_source in ["all", "tiki"]:
        tiki_script = os.path.join(base_dir, "crawl_tiki.py")
        run_command([python_exe, tiki_script, str(limit)], f"Cào dữ liệu từ TIKI ({limit} cuốn mới/danh mục)")

    # 2. Thu thập dữ liệu Fahasa
    if target_source in ["all", "fahasa"]:
        fahasa_script = os.path.join(base_dir, "crawl_fahasa.py")
        run_command([python_exe, fahasa_script, str(limit)], f"Cào dữ liệu từ FAHASA ({limit} cuốn mới/danh mục)")

    # 3. Tự động đồng bộ hóa Vector Database qua indexer.py
    indexer_script = os.path.join(base_dir, "indexer.py")
    if os.path.exists(indexer_script):
        run_command([python_exe, indexer_script], "Đồng bộ hóa Vector Database (ChromaDB)")

    print("\n" + "=" * 50)
    print("TIẾN TRÌNH THU THẬP VÀ ĐỒNG BỘ DỮ LIỆU ĐÃ HOÀN TẤT.")
    print("Dữ liệu kho sách đã sẵn sàng phục vụ hệ thống.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
