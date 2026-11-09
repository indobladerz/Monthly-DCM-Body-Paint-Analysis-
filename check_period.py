#!/usr/bin/env python3
"""Offline check for the scheduled run (no network).

  python3 check_period.py YYYY-MM

Prints one line per fact and exits 0 only when data/<period>.json exists AND the period is newer than
config/baseline.txt (the last period already analysed and emailed). Exit codes:
  0  parsed data exists and period > baseline: safe to build the report for it
  1  data/<period>.json is missing (nothing parsed yet)
  2  period <= baseline: must NOT be emailed again
  3  bad argument
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main(argv):
    if len(argv) != 1 or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', argv[0]):
        print('usage: check_period.py YYYY-MM'); return 3
    period = argv[0]
    baseline = open(os.path.join(HERE, 'config', 'baseline.txt'), encoding='utf-8').read().strip()
    assert re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', baseline), f'config/baseline.txt is not YYYY-MM: {baseline!r}'
    exists = os.path.exists(os.path.join(HERE, 'data', f'{period}.json'))
    print(f'period={period} baseline={baseline} data_exists={str(exists).lower()} newer_than_baseline={str(period > baseline).lower()}')
    if period <= baseline:
        print('BLOCK: period is not newer than the baseline; do not email it.'); return 2
    if not exists:
        print(f'MISSING: data/{period}.json not found; run normalize_drive_text.py then parse_dcm.py first.'); return 1
    print('OK'); return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
