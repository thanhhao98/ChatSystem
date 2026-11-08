"""
Audit and verify 300 irrelevance / no-call queries in data/sgod/irrelevance.json
"""
import json
from collections import Counter

def main():
    path = 'data/sgod/irrelevance.json'
    try:
        with open(path, encoding='utf-8') as f:
            irrel = json.load(f)
    except FileNotFoundError:
        print(f"File {path} not found.")
        return

    print('=== NGHIỆM THU IRRELEVANCE.JSON (BaoMyTH) ===')
    print(f'Tổng số câu: {len(irrel)} (Kỳ vọng: 300)')

    # 1. Kiểm tra tuyệt đối không có tool_call
    with_tools = [r for r in irrel if r.get('expected_tool') is not None]
    print(f'Số câu gọi nhầm tool: {len(with_tools)} (Bắt buộc = 0)')

    # 2. Đếm phân bổ categories
    cats = Counter(r.get('category', 'unknown') for r in irrel)
    print(f'Phân bổ danh mục: {dict(cats)}')

    # 3. Kiểm tra độ dài câu hỏi
    short_queries = [r for r in irrel if len(r.get('input', '').strip()) < 5]
    print(f'Số câu quá ngắn/bất thường: {len(short_queries)}')

    if len(irrel) == 300 and len(with_tools) == 0 and len(short_queries) == 0:
        print('>>> KẾT LUẬN: TẬP IRRELEVANCE ĐẠT CHUẨN NGHIỆM THU 100%!')
    else:
        print('>>> CẦN RÀ SOÁT LẠI TỆP IRRELEVANCE!')

if __name__ == '__main__':
    main()
