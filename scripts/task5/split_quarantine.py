"""
Partition quarantine.json records among 3 members: BaoMyTH, Ho Van Dinh, and Thehy-IT.
"""
import json

def main():
    try:
        with open('data/sgod/quarantine.json', encoding='utf-8') as f:
            quarantine = json.load(f)
    except FileNotFoundError:
        print("data/sgod/quarantine.json not found.")
        return

    baomy_tools = {
        'get_location', 'list_locations', 'get_maintenance_schedule',
        'list_maintenance_records', 'list_maintenance_schedules',
        'list_maintenance_tasks', 'get_unread_counts'
    }
    dinh_tools = {
        'get_asset_transfer', 'list_asset_transfers', 'get_transfer_summary',
        'get_staff_request_summary', 'list_staff_requests',
        'list_my_conversations', 'get_my_permissions'
    }
    thehy_tools = {
        'get_asset', 'get_asset_histories', 'get_asset_statistics',
        'get_enterprise_profile', 'list_my_assets', 'list_categories',
        'list_enterprise_users', 'get_my_profile'
    }

    q_baomy = [r for r in quarantine if r.get('expected_tool') in baomy_tools]
    q_dinh = [r for r in quarantine if r.get('expected_tool') in dinh_tools]
    q_thehy = [r for r in quarantine if r.get('expected_tool') in thehy_tools or r.get('expected_tool') is None]

    print('=== PHÂN CHIA QUARANTINE (Lead Thehy-IT) ===')
    print(f'Tổng số hàng quarantine: {len(quarantine)}')
    print(f'1. Giao BaoMyTH (Bảo trì): {len(q_baomy)} hàng -> data/sgod/quarantine_baomy.json')
    print(f'2. Giao Hồ Văn Dinh (Điều chuyển): {len(q_dinh)} hàng -> data/sgod/quarantine_dinh.json')
    print(f'3. Thehy-IT xử lý (Tài sản & RBAC): {len(q_thehy)} hàng -> data/sgod/quarantine_thehy.json')

    with open('data/sgod/quarantine_baomy.json', 'w', encoding='utf-8') as f:
        json.dump(q_baomy, f, ensure_ascii=False, indent=2)
    with open('data/sgod/quarantine_dinh.json', 'w', encoding='utf-8') as f:
        json.dump(q_dinh, f, ensure_ascii=False, indent=2)
    with open('data/sgod/quarantine_thehy.json', 'w', encoding='utf-8') as f:
        json.dump(q_thehy, f, ensure_ascii=False, indent=2)

    print('>>> ĐÃ XUẤT 3 TỆP THÀNH CÔNG! BÀN GIAO CHO CÁC THÀNH VIÊN.')

if __name__ == '__main__':
    main()
