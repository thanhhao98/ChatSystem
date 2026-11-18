"""
Verify BaoMyTH's 7 tools in tools/sgod/sgod_tools.json
"""
import json

def get_tool_name(t):
    if 'name' in t:
        return t['name']
    if 'function' in t and isinstance(t['function'], dict):
        return t['function'].get('name')
    return None

def main():
    tools_path = 'tools/sgod/sgod_tools.json'
    with open(tools_path, encoding='utf-8') as f:
        tools = json.load(f)
    my_tools = {
        'get_location',
        'list_locations',
        'get_maintenance_schedule',
        'list_maintenance_records',
        'list_maintenance_schedules',
        'list_maintenance_tasks',
        'get_unread_counts'
    }
    found = [name for t in tools if (name := get_tool_name(t)) and name in my_tools]
    print(f'BaoMyTH Tools Verified: {len(found)}/7 tools -> {found}')

if __name__ == '__main__':
    main()
