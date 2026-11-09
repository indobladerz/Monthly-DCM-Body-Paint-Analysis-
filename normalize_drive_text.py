#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the text returned by the Google Drive connector (read_file_content) for a monthly
'LAPORAN NERACA & RUGILABA PT DCM BODYPAINT' PDF into the data/raw/<yyyy-mm>.txt layout parse_dcm.py expects.

Usage:  python3 normalize_drive_text.py INPUT.txt [-o data/raw/2026-10.txt]
INPUT may be the plain text or the connector's JSON ({"fileContent": "...", "title": ...}).
Without -o the month is read from the 'Period <Bulan> <yyyy> to ...' line and the file is written to data/raw/<yyyy-mm>.txt.

What it does (all observed in the connector output):
  * drops blank lines;
  * splits and drops the 'ACCURATE Accounting System Report' page footer, also when glued to the previous word;
  * drops the statement header block ('PT ... (Multi Periode)' + 'Period ...') when it repeats after a page break
    (the 'Description <month> ...' line carries data and is kept; parse_dcm.py strips it).
It never changes a number. It refuses to write if the period is not a single month or the two statements are missing.
"""
import re, sys, os, json

FOOTER = 'ACCURATE Accounting System Report'
MONTHS = ['januari', 'februari', 'maret', 'april', 'mei', 'juni', 'juli', 'agustus', 'september', 'oktober', 'november', 'desember']
PT = re.compile(r'^PT DUTA CENDANA MOBILINDO BODY PAINT (Neraca|Laba/Rugi) \(Multi Periode\)$')
PERIOD = re.compile(r'^Period ([A-Za-z]+) (\d{4}) to ([A-Za-z]+) (\d{4})$')

def load(path):
    raw = open(path, encoding='utf-8').read()
    s = raw.lstrip()
    if s.startswith('{'):
        try:
            return json.loads(s)['fileContent']
        except (ValueError, KeyError):
            pass
    return raw

def normalize(text):
    text = text.replace('\r\n', '\n').replace(FOOTER, '\n' + FOOTER + '\n')
    out, seen_pt, skip_period = [], set(), False
    for line in (l.strip() for l in text.split('\n')):
        if not line or line == FOOTER:
            continue
        m = PT.match(line)
        if m:
            if m.group(1) in seen_pt:       # repeated page header
                skip_period = True
                continue
            seen_pt.add(m.group(1))
        elif skip_period and PERIOD.match(line):
            skip_period = False
            continue
        else:
            skip_period = False
        out.append(line)
    return '\n'.join(out) + '\n', seen_pt

def period_key(text):
    for line in text.split('\n'):
        m = PERIOD.match(line)
        if m:
            a, ya, b, yb = m.group(1).lower(), m.group(2), m.group(3).lower(), m.group(4)
            if (a, ya) != (b, yb) or a not in MONTHS:
                raise SystemExit(f'not a single-month statement: {line!r}')
            return f'{ya}-{MONTHS.index(a) + 1:02d}'
    raise SystemExit('no "Period <month> <yyyy> to <month> <yyyy>" line found')

def main(argv):
    if not argv or argv[0].startswith('-'):
        sys.exit(__doc__)
    src, out = argv[0], None
    if '-o' in argv:
        out = argv[argv.index('-o') + 1]
    text, seen = normalize(load(src))
    if seen != {'Neraca', 'Laba/Rugi'}:
        raise SystemExit(f'expected both a Neraca and a Laba/Rugi statement, found {sorted(seen)}')
    key = period_key(text)
    out = out or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'raw', f'{key}.txt')
    open(out, 'w', encoding='utf-8').write(text)
    print(f'{key}: wrote {out} ({len(text)} chars)')

if __name__ == '__main__':
    main(sys.argv[1:])
