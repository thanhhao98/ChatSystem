# Kết quả chấm: `synthetic-sample` trên `xlam_2k.eval.json`

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `ebcae911` · scorer: `eval_toolcall/1.2 (strict first-call; params >= half of keys; unknown tool = violation)` · sampling: `{"temperature": 0, "synthetic": true, "seed": 1, "wrong_tool_every": 7, "drop_arg_every": 11, "empty_every": 23}`. Không so sánh với bảng ở trục khác. <!-- no-prov -->

| Số đo | Giá trị |
|---|---|
| n | 200 |
| passed (strict) | 149 |
| **accuracy (strict)** | **74.5%** |
| tool_name_acc | 82.5% |
| param_acc (≥ nửa số khoá) | 89.94% |
| params_exact | 89.94% |
| json_valid_rate | 96.0% |
| latency p50 / p95 (ms) | 60 / 96 |
| model · backend | synthetic-sample · synthetic |
| date · git_sha (dự đoán) | 2026-09-13 · null |

## Theo `source`

| group | n | passed | accuracy |
|---|---|---|---|
| public | 200 | 149 | 74.5% |

## Theo `user_role`

| group | n | passed | accuracy |
|---|---|---|---|
| employee | 200 | 149 | 74.5% |

<!-- no-prov-start -->
## Theo lý do (chẩn đoán)

| reason | count | tỷ lệ |
|---|---|---|
| ok | 149 | 74.5% |
| wrong_tool | 35 | 17.5% |
| missing_params | 16 | 8.0% |

## Bản ghi sai (tối đa 25 / 51)

| id | reason | expected | actual | detail |
|---|---|---|---|---|
| pub-0b0eb50f | wrong_tool | cell_density | unknown_tool | "expected one of ['cell_density'], got ['unknown_tool']" |
| pub-0fb5040d | missing_params | nearby_superchargers | nearby_superchargers | {"expected": ["lat", "lng", "radius"], "got": [], "matched": 0} |
| pub-120a6615 | wrong_tool | generate_a_qr_code_image | domain_check | "expected one of ['generate_a_qr_code_image'], got ['domain_check']" |
| pub-1d22a72b | wrong_tool | remove_duplicates | calculate_age | "expected one of ['remove_duplicates'], got ['calculate_age']" |
| pub-2070726d | missing_params | get_vessel_photo | get_vessel_photo | {"expected": ["shipid"], "got": [], "matched": 0} |
| pub-2265459a | wrong_tool | final_velocity | None | "expected one of ['final_velocity'], got none" |
| pub-274288ae | wrong_tool | get_ip_information | unknown_tool | "expected one of ['get_ip_information'], got ['unknown_tool']" |
| pub-2da214ce | missing_params | airplanes_ordered_by_descending | airplanes_ordered_by_descending | {"expected": ["ordering"], "got": [], "matched": 0} |
| pub-2dd6485d | wrong_tool | get_ip_location | get_city_from_zipcode | "expected one of ['get_ip_location'], got ['get_city_from_zipcode']" |
| pub-357b9fda | wrong_tool | ufc_fight_night_dern_vs_hill_may_20_2023 | match_team_statistics | "expected one of ['ufc_fight_night_dern_vs_hill_may_20_2023'], got ['match_team_statistics']" |
| pub-363d7316 | missing_params | find_missing_ranges | find_missing_ranges | {"expected": ["lower", "nums", "upper"], "got": [], "matched": 0} |
| pub-3a4afff2 | wrong_tool | find_longest_palindromic_substring | None | "expected one of ['find_longest_palindromic_substring'], got none" |
| pub-3fc28319 | wrong_tool | city_list | unknown_tool | "expected one of ['city_list'], got ['unknown_tool']" |
| pub-4415144a | missing_params | order_by_ascending | order_by_ascending | {"expected": ["ordering"], "got": [], "matched": 0} |
| pub-47cf73a9 | wrong_tool | calculate_angle | find_next_greater_element | "expected one of ['calculate_angle'], got ['find_next_greater_element']" |
| pub-4dea518c | wrong_tool | search_image | getcountrycode | "expected one of ['search_image'], got ['getcountrycode']" |
| pub-4f30879c | missing_params | getforecastweather | getforecastweather | {"expected": ["cnt", "q", "units"], "got": [], "matched": 0} |
| pub-522320df | wrong_tool | search_single_postcode | None | "expected one of ['search_single_postcode'], got none" |
| pub-524a33bb | wrong_tool | mean_confidence_interval | unknown_tool | "expected one of ['mean_confidence_interval'], got ['unknown_tool']" |
| pub-649a46fe | wrong_tool | simulate_query_database | unknown_tool | "expected one of ['simulate_query_database'], got ['unknown_tool']" |
| pub-6f093dde | wrong_tool | get_ip_location | is_valid_ip_address | "expected one of ['get_ip_location'], got ['is_valid_ip_address']" |
| pub-75308398 | missing_params | generate_a_qr_code_image | generate_a_qr_code_image | {"expected": ["addtext", "d", "qrsize", "txtcolor"], "got": [], "matched": 0} |
| pub-78b8f2b0 | wrong_tool | flame | unknown_tool | "expected one of ['flame'], got ['unknown_tool']" |
| pub-79c86b59 | wrong_tool | get_all_kfc_locations_by_state | None | "expected one of ['get_all_kfc_locations_by_state'], got none" |
| pub-80d6d156 | wrong_tool | runner_up | team_recent_form | "expected one of ['runner_up'], got ['team_recent_form']" |
<!-- no-prov-end -->

_Lệnh_: `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred data/public/sample_pred.jsonl --out /tmp/r.json --preamble prompts/system_preamble_v0.txt --md tests/fixtures/eval_report_ok.md`
