"""
Extract quarantine records for BaoMyTH's maintenance cluster to data/sgod/quarantine_baomy.json
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
        with open('data/sgod/quarantine.json', encoding='utf-8') as f:
            quarantine = json.load(f)
    except FileNotFoundError:
        print("data/sgod/quarantine.json not found.")
        return

    my_quarantine = [
        q for q in quarantine
        if q.get('expected_tool') in my_tools or any(alt in my_tools for alt in q.get('expected_tool_alternates', []))
    ]

    print('=== TRIAGE QUARANTINE CỤM BẢO TRÌ (BaoMyTH) ===')
    print(f'Tổng số hàng cần xử lý: {len(my_quarantine)}')

    # Lưu ra tệp riêng cho BaoMyTH làm việc
    out_path = 'data/sgod/quarantine_baomy.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(my_quarantine, f, ensure_ascii=False, indent=2)

    print(f'Đã trích xuất ra {out_path} để BaoMyTH rà soát.')

if __name__ == '__main__':
    main()
