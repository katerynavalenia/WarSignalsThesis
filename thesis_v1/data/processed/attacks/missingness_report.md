# Phase 2 — Missingness & Revision Report

**Date:** 2026-06-28


## 1. Raw data missingness

Total records: 3812


| Column | Missing | % |
|---|---|---|
| `turbojet` | 3809 | 99.9% |
| `turbojet_destroyed` | 3809 | 99.9% |
| `launched_details` | 3806 | 99.8% |
| `launch_place_details` | 3805 | 99.8% |
| `target_main` | 3748 | 98.3% |
| `affected region` | 3597 | 94.4% |
| `still_attacking` | 3586 | 94.1% |
| `is_shahed` | 3573 | 93.7% |
| `carrier` | 3501 | 91.8% |
| `num_fall_fragment_location` | 3433 | 90.1% |
| `num_hit_location` | 3416 | 89.6% |
| `not_reach_goal` | 3096 | 81.2% |
| `destroyed_details` | 2950 | 77.4% |
| `launch_place` | 1819 | 47.7% |
| `target` | 30 | 0.8% |
| `destroyed` | 6 | 0.2% |
| `launched` | 3 | 0.1% |

## 2. Day-level coverage

Days in daily table: 809
Date range: 2022-09-29 to 2026-06-21
Days with at least one attack: 809
Days with zero attacks: 0

## 3. Calendar gaps

Missing dates in daily table: [datetime.date(2022, 9, 30), datetime.date(2022, 10, 3), datetime.date(2022, 10, 4), datetime.date(2022, 10, 12), datetime.date(2022, 10, 14), datetime.date(2022, 10, 18), datetime.date(2022, 10, 21), datetime.date(2022, 10, 24), datetime.date(2022, 10, 27), datetime.date(2022, 10, 28)]...

## 4. Notes

- The raw dataset begins 2022-09-29. Earlier attacks are not in the data.
- `target_main` is missing in 98% of rows; `target` and `affected region` are more complete.
- `launched_details`, `launch_place_details`, `turbojet`, `turbojet_destroyed` are 99%+ missing — these were experimental fields, not used in modeling.
- All raw records have a `source` URL pointing to the original UAF or southern command Facebook post.
- The dataset is **cumulative-retrospective** — i.e., counts may be revised after initial publication. The `validation_table.csv` samples 25 random days and confirms the aggregated count matches the raw count for the same date.