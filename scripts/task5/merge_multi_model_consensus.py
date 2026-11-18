#!/usr/bin/env python3
"""scripts/task5/merge_multi_model_consensus.py

Hợp nhất kết quả gán nhãn từ 2 lần chạy model độc lập (Model A & Model B) trên Colab
để tạo bằng chứng Consensus Labeling đa mô hình chuẩn theo Hợp đồng 3 và Hướng dẫn Task 5.

Usage:
  python scripts/task5/merge_multi_model_consensus.py \
      --label-a data/sgod/labeled_modelA.json \
      --report-a data/sgod/report_modelA.json \
      --label-b data/sgod/labeled_modelB.json \
      --report-b data/sgod/report_modelB.json \
      --output-labeled data/sgod/labeled.json \
      --output-report data/sgod/label_report.json
"""
import argparse
import json
import sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description="Merge two independent model labeling passes into a consensus labeled set.")
    p.add_argument("--label-a", default="data/sgod/labeled_modelA.json", help="Output labeled JSON từ Model A (Primary)")
    p.add_argument("--report-a", default="data/sgod/report_modelA.json", help="Report JSON từ Model A")
    p.add_argument("--label-b", default="data/sgod/labeled_modelB.json", help="Output labeled JSON từ Model B (Secondary)")
    p.add_argument("--report-b", default="data/sgod/report_modelB.json", help="Report JSON từ Model B")
    p.add_argument("--output-labeled", default="data/sgod/labeled.json", help="Output consensus labeled JSON")
    p.add_argument("--output-report", default="data/sgod/label_report.json", help="Output consensus report JSON")
    args = p.parse_args()

    for path in [args.label_a, args.report_a, args.label_b, args.report_b]:
        if not Path(path).exists():
            print(f"[ERROR] Không tìm thấy tệp: {path}", file=sys.stderr)
            sys.exit(1)

    with open(args.label_a, encoding="utf-8") as f:
        cases_a = {r["id"]: r for r in json.load(f)}
    with open(args.report_a, encoding="utf-8") as f:
        reports_a = {r["id"]: r for r in json.load(f)}

    with open(args.label_b, encoding="utf-8") as f:
        cases_b = {r["id"]: r for r in json.load(f)}
    with open(args.report_b, encoding="utf-8") as f:
        reports_b = {r["id"]: r for r in json.load(f)}

    model_a_name = reports_a[next(iter(reports_a))]["proposals"][0][0] if reports_a else "ModelA"
    model_b_name = reports_b[next(iter(reports_b))]["proposals"][0][0] if reports_b else "ModelB"
    print(f"=== HỢP NHẤT GÁN NHÃN ĐỒNG THUẬN: {model_a_name} (Primary) vs {model_b_name} (Secondary) ===")

    merged_cases = []
    merged_reports = []

    agree_count = 0
    disagree_count = 0

    for case_id, row_a in cases_a.items():
        row_b = cases_b.get(case_id)
        rep_a = reports_a.get(case_id, {})
        rep_b = reports_b.get(case_id, {})

        tool_a = rep_a.get("expected_tool")
        tool_b = rep_b.get("expected_tool") if rep_b else None

        # Kiểm tra đồng thuận công cụ giữa 2 model
        agree = (tool_a == tool_b)
        if agree:
            agree_count += 1
        else:
            disagree_count += 1

        proposals = []
        if rep_a and rep_a.get("proposals"):
            proposals.extend(rep_a["proposals"])
        else:
            proposals.append([model_a_name, tool_a])

        if rep_b and rep_b.get("proposals"):
            proposals.extend(rep_b["proposals"])
        else:
            proposals.append([model_b_name, tool_b])

        # Tạo bản ghi consensus
        merged_row = dict(row_a)
        if not agree:
            merged_row["_needs_review"] = True
            # Giữ đề xuất của model phụ vào alternates nếu có
            if tool_b:
                alts = merged_row.get("expected_tool_alternates") or []
                if tool_b not in alts and tool_b != tool_a:
                    alts.append(tool_b)
                merged_row["expected_tool_alternates"] = alts

        merged_cases.append(merged_row)

        merged_reports.append({
            "id": case_id,
            "proposals": proposals,
            "agree": agree,
            "expected_tool": tool_a,
            "permission": rep_a.get("permission", row_a.get("expected_permission")),
            "dropped_params": rep_a.get("dropped_params", [])
        })

    # Lưu đầu ra chuẩn
    with open(args.output_labeled, "w", encoding="utf-8") as f:
        json.dump(merged_cases, f, indent=2, ensure_ascii=False)

    with open(args.output_report, "w", encoding="utf-8") as f:
        json.dump(merged_reports, f, indent=2, ensure_ascii=False)

    total = len(merged_cases)
    agree_rate = (agree_count / total) * 100 if total > 0 else 0.0

    print(f"Tổng số kịch bản: {total}")
    print(f"  - Đồng thuận (Agree): {agree_count} ({agree_rate:.2f}%)")
    print(f"  - Bất đồng (Disagree/Needs review): {disagree_count} ({100 - agree_rate:.2f}%)")
    print(f">>> Đã ghi kết quả vào: {args.output_labeled} & {args.output_report}")
    print(f">>> Sau bước này, chạy: bash datagen/run_pipeline.sh --stage verify để cách ly các ca bất đồng vào quarantine.")

if __name__ == "__main__":
    main()
