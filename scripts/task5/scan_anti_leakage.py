"""
Scan a target dataset against eval_v1.json and eval_human_core.jsonl to verify zero data leakage.
"""
import sys
import json
from difflib import SequenceMatcher

def main():
    target_file = sys.argv[1] if len(sys.argv) > 1 else 'data/sgod/verified.json'

    print('=== QUÉT CHỐNG RÒ RỈ ĐỘC LẬP (Hồ Văn Dinh - Anti-leakage Sentinel) ===')

    # 1. Nạp tập cấm rò rỉ
    eval_queries = []
    try:
        with open('data/sgod/eval_v1.json', encoding='utf-8') as f:
            for r in json.load(f):
                eval_queries.append(r.get('input', '').strip().lower())
    except FileNotFoundError:
        print("data/sgod/eval_v1.json not found.")

    try:
        with open('data/sgod/eval_human_core.jsonl', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    eval_queries.append(json.loads(line).get('input', '').strip().lower())
    except FileNotFoundError:
        print("data/sgod/eval_human_core.jsonl not found.")

    print(f'Tổng số câu benchmark cấm: {len(eval_queries)} câu')

    # 2. Quét tập candidate
    try:
        if target_file.endswith('.jsonl'):
            candidates = []
            with open(target_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        candidates.append(json.loads(line))
        else:
            with open(target_file, encoding='utf-8') as f:
                candidates = json.load(f)
    except FileNotFoundError:
        print(f"Target file {target_file} not found.")
        return

    max_sim = 0.0
    leaked_rows = []

    for idx, cand in enumerate(candidates):
        # Extract query text depending on schema (parity format messages or raw scenario input)
        q_cand = cand.get('input', '')
        if not q_cand and 'messages' in cand:
            user_msgs = [m.get('content', '') for m in cand.get('messages', []) if m.get('role') == 'user']
            if user_msgs:
                q_cand = user_msgs[0]
        q_cand = q_cand.strip().lower()

        for q_eval in eval_queries:
            sim = SequenceMatcher(None, q_cand, q_eval).ratio()
            if sim > max_sim:
                max_sim = sim
            if sim >= 0.65:
                leaked_rows.append((idx, cand.get('id', idx), sim, q_cand, q_eval))

    print(f'Target file: {target_file} ({len(candidates)} records)')
    print(f'Max Similarity to eval_v1: {max_sim:.4f} (Ngưỡng cấm: < 0.65)')
    print(f'Số câu vi phạm rò rỉ: {len(leaked_rows)}')

    if len(leaked_rows) > 0:
        print('>>> BÁO ĐỘNG ĐỎ: PHÁT HIỆN RÒ RỈ! Danh sách ID vi phạm:')
        for item in leaked_rows:
            print(f'  ID: {item[1]} | Sim: {item[2]:.4f} | Cand: "{item[3]}" <=> Eval: "{item[4]}"')
        print('>>> HỒ VĂN DINH THỰC THI QUY TẮC: DROP NGAY LẬP TỨC CÁC CÂU NÀY, CẤM PARAPHRASE!')
        sys.exit(1)
    else:
        print('>>> ZERO LEAKAGE CONFIRMED: HOÀN TOÀN SẠCH RÒ RỈ! (Max Sim < 0.65)')

if __name__ == '__main__':
    main()
