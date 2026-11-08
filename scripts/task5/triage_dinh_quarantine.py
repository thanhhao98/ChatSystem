"""
Triage quarantine records for Dinh's transfer cluster and audit invented parameters against catalogue.
"""
import json

def get_tool_info(t):
    if 'name' in t:
        name = t['name']
        props = t.get('parameters', {}).get('properties', {}).keys()
        return name, set(props)
    if 'function' in t and isinstance(t['function'], dict):
        fn = t['function']
        name = fn.get('name')
        props = fn.get('parameters', {}).get('properties', {}).keys()
        return name, set(props)
    return None, set()

def main():
    my_tools = {
        'get_asset_transfer',
        'list_asset_transfers',
        'get_transfer_summary',
        'get_staff_request_summary',
        'list_staff_requests',
        'list_my_conversations',
        'get_my_permissions'
    }

    try:
        with open('tools/sgod/sgod_tools.json', encoding='utf-8') as f:
            raw_tools = json.load(f)
            catalogue = {}
            for t in raw_tools:
                name, props = get_tool_info(t)
                if name:
                    catalogue[name] = props
    except FileNotFoundError:
        print("tools/sgod/sgod_tools.json not found.")
        return

    try:
        with open('data/sgod/quarantine.json', encoding='utf-8') as f:
            quarantine = json.load(f)
    except FileNotFoundError:
        print("data/sgod/quarantine.json not found.")
        return

    my_quarantine = [q for q in quarantine if q.get('expected_tool') in my_tools]
    print('=== TRIAGE & KIỂM TOÁN THAM SỐ BỊA CỤM ĐIỀU CHUYỂN (Hồ Văn Dinh) ===')
    print(f'Số hàng thuộc cụm: {len(my_quarantine)}')

    invented_cases = []
    for q in my_quarantine:
        tool = q.get('expected_tool')
        params = q.get('expected_params', {})
        if tool in catalogue:
            allowed = catalogue[tool]
            invented = set(params.keys()) - allowed
            if invented:
                invented_cases.append((q.get('id'), tool, list(invented)))

    print(f'Số ca bịa tham số (Invented Params): {len(invented_cases)}')
    for c in invented_cases:
        print(f'  ID: {c[0]} | Tool: {c[1]} | Tham số bịa: {c[2]}')

    # Xuất ra file riêng cho Hồ Văn Dinh xử lý
    out_path = 'data/sgod/quarantine_dinh.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(my_quarantine, f, ensure_ascii=False, indent=2)

    print(f'Đã trích xuất ra {out_path} để Hồ Văn Dinh hiệu chỉnh.')

if __name__ == '__main__':
    main()
