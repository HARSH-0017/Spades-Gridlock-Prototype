# Operational Data Quality Report

Rows analyzed: 298,450
Source date range: 2023-11-10 to 2024-04-08 IST

## Readiness Checks

- Invalid/out-of-city coordinates: 0 (0.00%)
- Missing location text: 3,041
- Missing police station: 5
- Missing validation status: 125,254 (41.97%)

## Validation Status Mix

- NULL: 125,254
- approved: 115,400
- rejected: 49,754
- created1: 7,044
- processing: 678
- duplicate: 320

## Operational Caveats

- The source data is historical, so deployment recommendations should be refreshed whenever new records arrive.
- The system currently estimates parking-enforcement priority, not measured congestion delay.
- Missing validation status is high enough that production use should track approval/rejection workflow separately.
- True congestion impact requires traffic speed, queue length, road capacity, or travel-time data.