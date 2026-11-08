"""
Check yield rate for BaoMyTH's maintenance cluster from data/sgod/raw.json and verified.json
"""
import json

def main():
    my_tools = {
        'get_location',
        'list_locations',
        'get_maintenance_schedule',
        'list_maintenance_records',
        'list_maintenance_schedules',
        'list_maintenance_tasks',
        'get_unread_counts'
    }

    try:
        with open('data/sgod/raw.json', encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        print("data/sgod/raw.json not found.")
        return

    try:
        with open('data/sgod/verified.json', encoding='utf-8') as f:
            verified = json.load(f)
    except FileNotFoundError:
        print("data/sgod/verified.json not found.")
        return

    my_raw = [r for r in raw if r.get('expected_tool') in my_tools]
    my_verified = [v for v in verified if v.get('expected_tool') in my_tools]

    yield_rate = len(my_verified) / len(my_raw) if len(my_raw) > 0 else 0
    print('=== BÁO CÁO YIELD CỤM BẢO TRÌ (BaoMyTH) ===')
    print(f'Raw rows: {len(my_raw)}')
    print(f'Verified rows: {len(my_verified)}')
    print(f'Yield Rate: {yield_rate:.2%} (Kỳ vọng: ~58%, Sàn: >= 45%)')

    if yield_rate < 0.45:
        print('>>> CẢNH BÁO ĐỎ: Yield < 0.45! BaoMyTH cần phân tích lỗi và đề xuất sửa prompt datagen/prompts/!')
    else:
        print('>>> ĐẠT CHUẨN YIELD! Sẵn sàng cho khâu Triage Bước 4.')

if __name__ == '__main__':
    main()
