"""
Merge salvaged records from thehy, baomy, and dinh into data/sgod/verified.json and audit final yield.
"""
import json

def main():
    # 1. Nạp tệp verified gốc
    try:
        with open('data/sgod/verified.json', encoding='utf-8') as f:
            verified = json.load(f)
    except FileNotFoundError:
        print("data/sgod/verified.json not found.")
        return

    try:
        with open('data/sgod/raw.json', encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        print("data/sgod/raw.json not found.")
        return

    v_orig_count = len(verified)

    # 2. Nạp các tệp đã cứu chữa từ 3 thành viên
    salvaged_rows = []
    for member in ['thehy', 'baomy', 'dinh']:
        path = f'data/sgod/salvage_{member}.json'
        try:
            with open(path, encoding='utf-8') as f:
                rows = json.load(f)
                salvaged_rows.extend(rows)
                print(f'Nạp thành công {len(rows)} hàng cứu chữa từ {member}')
        except FileNotFoundError:
            print(f'Chưa có file {path} (hoặc không có hàng nào cứu chữa)')

    # 3. Gộp vào verified
    verified_final = verified + salvaged_rows
    with open('data/sgod/verified.json', 'w', encoding='utf-8') as f:
        json.dump(verified_final, f, ensure_ascii=False, indent=2)

    final_yield = len(verified_final) / len(raw) if len(raw) > 0 else 0
    print('=== BÁO CÁO TỔNG HỢP SALVAGE & YIELD CUỐI CÙNG (Lead Thehy-IT) ===')
    print(f'Verified ban đầu: {v_orig_count}')
    print(f'Số hàng cứu chữa thêm: {len(salvaged_rows)}')
    print(f'Verified cuối cùng: {len(verified_final)}')
    print(f'Raw tổng cộng: {len(raw)}')
    print(f'Yield Rate cuối cùng: {final_yield:.2%}')

    if final_yield < 0.45:
        print('>>> LỖI NGHIÊM TRỌNG: Yield cuối cùng < 0.45! BẮT BUỘC DỪNG LẠI ĐỂ SỬA PROMPT TRONG datagen/prompts/!')
    else:
        print('>>> YIELD RATE ĐẠT CHUẨN (>= 0.45)! ĐÃ MỞ KHÓA WAIT GATE 2 ĐỂ TIẾN HÀNH BƯỚC 5 (ASSEMBLE).')

if __name__ == '__main__':
    main()
