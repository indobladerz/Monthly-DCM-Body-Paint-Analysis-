#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse the PT DCM Body Paint monthly statements (ACCURATE 'Neraca' + 'Laba/Rugi', text layer of the PDFs)
into data/<yyyy-mm>.json. One statement per month (data/raw/<yyyy-mm>.txt is discovered automatically);
the Sep–Oct 2025 file holds two columns.

Every leaf account is kept with its booked name. Parent (header) accounts are dropped. The parser asserts
that leaf accounts re-add to the booked subtotals (sales, discounts, COGS, selling, G&A, opex, other, net)
and that the balance sheet balances, so a transcription error cannot pass silently.
"""
import re, sys, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'data', 'raw')
NUM = re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$')

def to_num(t):
    return float(t.replace('.', '').replace(',', '.'))

def pairs(text, ncol):
    """Yield (label, [values...]) for every label followed by ncol numbers (P&L has an extra 'Jumlah' column)."""
    toks = text.split()
    out, lab = [], []
    i = 0
    while i < len(toks):
        if NUM.match(toks[i]):
            nums = []
            while i < len(toks) and NUM.match(toks[i]):
                nums.append(to_num(toks[i])); i += 1
            if lab:
                out.append((' '.join(lab), nums)); lab = []
        else:
            lab.append(toks[i]); i += 1
    return out


SECTION_WORDS = ['Aktiva Lancar', 'Kas dan Bank', 'Aktiva lancar lainnya', 'Aktiva Tetap', 'Nilai histori', 'Kewajiban dan Ekuitas',
                 'Kewajiban lancar lain', 'Kewajiban jangka panjang', 'Kewajiban lancar', 'Kewajiban', 'Ekuitas', 'Aktiva',
                 'Piutang Dagang', 'Persediaan', 'Akumulasi Penyusutan', 'OTHER ASSETS', 'Hutang Dagang']

def norm_bs(lab):
    """Drop section headings that the text layer glues in front of the first account of a section.
    A heading is stripped only when what follows is itself a heading, a 'Jumlah ...' line or an ALL-CAPS group account,
    so leaf names such as 'Persediaan Barang' or 'Akumulasi Penyusutan Gedung' are left intact."""
    changed = True
    while changed:
        changed = False
        for w in sorted(SECTION_WORDS, key=len, reverse=True):
            if lab.startswith(w + ' '):
                rest = lab[len(w) + 1:]
                first = rest.split(' ')[0]
                if rest.startswith('Jumlah ') or first.isupper() or any(rest.startswith(x + ' ') for x in SECTION_WORDS) or w == 'Ekuitas':
                    lab = rest; changed = True; break
    return lab

# headers (parents) that are sums of the leaves that follow them
PL_HEADERS = {'PENDAPATAN', 'Penjualan', 'Potongan Penjualan', 'Jumlah Pendapatan', 'Harga Pokok Penjualan',
              'Jumlah Harga Pokok Penjualan', 'LABA KOTOR', 'BEBAN PENJUALAN', 'Biaya Pemasaran', 'Biaya Transportasi',
              'BIAYA ADMINISTRASI DAN UMUM', 'Biaya Gaji dan Tunjangan Karyawan', 'Tunjangan Karyawan Lainnya',
              'Biaya Listrik, Air dan Gas', 'Biaya Telekomunikasi & Informasi', 'Biaya Korespondensi Pos', 'Biaya Assuransi',
              'Biaya Training & Recruitment', 'Biaya Keperluan Kantor', 'Biaya Pemeliharaan & Perbaikan',
              'Biaya Pemeliharaan Peralatan Kantor', 'Biaya Pemeliharaan Kendaraan', 'Biaya Pemeliharaan Gedung',
              'Biaya Restribusi & Legalitas', 'Biaya Penyusutan & Amortisasi', 'Biaya Penyusutan Peralatan',
              'Jumlah Beban Operasi', 'PENDAPATAN OPERASI', 'PENDAPATAN DILUAR USAHA', 'Jumlah Pendapatan lain',
              'BIAYA DILUAR USAHA', 'Jumlah Beban lain-lain', 'Jumlah Pendapatan dan Beban Lain',
              'LABA(RUGI) BERSIH (Before Tax)', 'LABA(RUGI) BERSIH (After Tax)'}

def classify(label):
    if label.startswith('Penjualan -') or label.startswith('Pendapatan - Jasa') or label == 'Penjualan Lainnya':
        return 'sales'
    if label.startswith('Potongan Penjualan'):
        return 'discount'
    if label.startswith('Harga Pokok Penjualan -'):
        return 'cogs'
    if label.startswith('Pendapatan '):
        return 'other_income'
    return None

def parse_file(name, col, ncol_bs, ncol_pl, month_key):
    text = open(os.path.join(RAW, name), encoding='utf-8').read()
    # strip report headers
    text = re.sub(r'PT DUTA CENDANA MOBILINDO BODY PAINT (Neraca|Laba/Rugi) \(Multi Periode\)', '', text)
    text = re.sub(r'Period [A-Za-z]+ \d{4} to [A-Za-z]+ \d{4}', '', text)
    text = re.sub(r'Description( [A-Za-z]+ \d{4})+', '', text)
    bs_text, pl_text = text.split('Jumlah Pendapatan', 1)
    pl_text = 'Jumlah Pendapatan ' + pl_text
    bs = {}
    for lab, nums in pairs(bs_text, ncol_bs):
        lab = norm_bs(lab)
        bs[lab] = nums[col] if len(nums) > col else nums[0]
    pl_leaves, pl_all = {}, {}
    for lab, nums in pairs(pl_text, ncol_pl):
        if lab.startswith('Jumlah Pendapatan PENDAPATAN'):
            lab = 'PENDAPATAN'
        if lab.startswith('Beban Operasi '):
            lab = lab[len('Beban Operasi '):]
        if lab.startswith('Pendapatan dan Beban Lain Pendapatan lain '):
            lab = lab[len('Pendapatan dan Beban Lain Pendapatan lain '):]
        if lab.startswith('Pendapatan dan Beban Lain '):
            lab = lab[len('Pendapatan dan Beban Lain '):]
        if lab.startswith('Pendapatan lain '):
            lab = lab[len('Pendapatan lain '):]
        if lab.startswith('Beban lain-lain '):
            lab = lab[len('Beban lain-lain '):]
        if lab.startswith('Jumlah Jumlah'):
            lab = lab[len('Jumlah '):]
        if lab.startswith('Jumlah Beban lain-lain BIAYA') or lab.startswith('Jumlah Pendapatan lain PENDAPATAN'):
            lab = lab.split(' ', 3)[3]
        if lab.startswith('Jumlah ') and lab.split(' ', 1)[1].split(' ')[0].isupper():   # page-break 'Jumlah' column header glued to a group
            lab = lab.split(' ', 1)[1]
        if lab.startswith('Harga Pokok Penjualan Harga Pokok Penjualan'):
            lab = 'Harga Pokok Penjualan'
        v = nums[col] if len(nums) > col else nums[0]
        pl_all[lab] = v
        if lab not in PL_HEADERS:
            pl_leaves[lab] = v
    # ---- build structured record
    sales = {k: v for k, v in pl_leaves.items() if classify(k) == 'sales'}
    disc = {k: -v for k, v in pl_leaves.items() if classify(k) == 'discount'}
    cogs = {k: v for k, v in pl_leaves.items() if classify(k) == 'cogs'}
    other_inc = {k: v for k, v in pl_leaves.items() if classify(k) == 'other_income'}
    other_exp = {k: v for k, v in pl_leaves.items() if k in ('Biaya Bunga Bank', 'Biaya Debit/Kredit Card', 'Biaya Lain-Lain')}
    opex = {k: v for k, v in pl_leaves.items() if classify(k) is None and k not in other_exp}
    for k in opex:
        assert 'Jumlah' not in k and not k.isupper(), f'{month_key}: header leaked into leaves: {k!r}'
    selling_names = {'Biaya Iklan Dan Promosi', 'Biaya Customer Service', 'Biaya Komisi', 'Biaya Representasi & Entertainment',
                     'Biaya Transportasi Material', 'Biaya Bahan Bakar', 'Biaya Accessories'}
    selling = {k: v for k, v in opex.items() if k in selling_names}
    ga = {k: v for k, v in opex.items() if k not in selling_names}
    g = lambda k: pl_all.get(k, 0.0)
    rec = {
        'month': month_key,
        'pl': {
            'sales': {'jasa': sales.get('Pendapatan - Jasa Service', 0.0), 'sparepart': sales.get('Penjualan - Sparepart', 0.0),
                      'lainnya': sales.get('Penjualan Lainnya', 0.0), 'total': g('Penjualan')},
            'discount': {'jasa': disc.get('Potongan Penjualan - Service', 0.0), 'sparepart': disc.get('Potongan Penjualan - Spareparts', 0.0),
                         'lainnya': disc.get('Potongan Penjualan Lainnya', 0.0), 'total': -g('Potongan Penjualan')},
            'net_revenue': g('Jumlah Pendapatan'),
            'cogs': {'jasa': cogs.get('Harga Pokok Penjualan - Service', 0.0), 'sparepart': cogs.get('Harga Pokok Penjualan - Sparepart', 0.0),
                     'lainnya': cogs.get('Harga Pokok Penjualan - Lainnya', 0.0), 'total': g('Jumlah Harga Pokok Penjualan')},
            'gross_profit': g('LABA KOTOR'),
            'selling': g('BEBAN PENJUALAN'), 'ga': g('BIAYA ADMINISTRASI DAN UMUM'), 'opex': g('Jumlah Beban Operasi'),
            'op_profit': g('PENDAPATAN OPERASI'),
            'other_income': g('Jumlah Pendapatan lain'), 'other_expense': g('Jumlah Beban lain-lain'),
            'net_profit': g('LABA(RUGI) BERSIH (Before Tax)'),
        },
        'selling_accounts': selling, 'ga_accounts': ga, 'other_income_accounts': other_inc, 'other_expense_accounts': other_exp,
        'bs': bs,
    }
    # ---- integrity asserts (to the rupiah, tolerance 1)
    P = rec['pl']
    def close(a, b, what):
        assert abs(a - b) < 1.0, f'{month_key}: {what}: {a:,.2f} vs {b:,.2f}'
    close(sum(sales.values()), P['sales']['total'], 'sales leaves vs Penjualan')
    close(sum(disc.values()), P['discount']['total'], 'discount leaves vs Potongan Penjualan')
    close(P['sales']['total'] - P['discount']['total'], P['net_revenue'], 'net revenue')
    close(sum(cogs.values()), P['cogs']['total'], 'COGS leaves')
    close(P['net_revenue'] - P['cogs']['total'], P['gross_profit'], 'gross profit')
    close(sum(selling.values()), P['selling'], 'selling leaves vs BEBAN PENJUALAN')
    close(sum(ga.values()), P['ga'], 'G&A leaves vs BIAYA ADMINISTRASI DAN UMUM')
    close(P['selling'] + P['ga'], P['opex'], 'opex')
    close(P['gross_profit'] - P['opex'], P['op_profit'], 'operating profit')
    close(sum(other_inc.values()), P['other_income'], 'other income leaves')
    close(sum(other_exp.values()), P['other_expense'], 'other expense leaves')
    close(P['op_profit'] + P['other_income'] - P['other_expense'], P['net_profit'], 'net profit')
    close(bs['Jumlah Aktiva'], bs['Jumlah Kewajiban dan Ekuitas'], 'balance sheet balances')
    close(bs['Jumlah Aktiva Lancar'] + bs['Jumlah Aktiva Tetap'], bs['Jumlah Aktiva'], 'total assets')
    close(bs['Jumlah Kewajiban'] + bs['Jumlah Ekuitas'], bs['Jumlah Kewajiban dan Ekuitas'], 'L+E')
    close(bs['Bangunan'] + bs['Peralatan Kantor'] + bs['Peralatan Bengkel'], bs['AKTIVA TETAP'], 'fixed asset cost')
    close(bs['Akumulasi Penyusutan Gedung'] + bs['Akumulasi Penyusutan Peralatan Kantor'] + bs['Akumulasi Penyusutan Peralatan Bengkel'], bs['AKUMULASI PENYUSUTAN'], 'accumulated depreciation')
    close(bs['AKTIVA TETAP'] + bs['AKUMULASI PENYUSUTAN'], bs['Jumlah Aktiva Tetap'], 'net fixed assets')
    dep = ga.get('Biaya Penyusutan Gedung', 0) + ga.get('Biaya Penyusutan Peralatan Kantor', 0) + ga.get('Biaya Penyusutan Peralatan Bengkel', 0)
    close(dep, g('Biaya Penyusutan & Amortisasi'), 'depreciation leaves')
    return rec

SPECIAL = {'2025-09-10.txt': [(0, '2025-09'), (1, '2025-10')]}   # opening-period file: one statement with two month columns
RAW_NAME = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])\.txt$')

def discover(raw_dir):
    """Every data/raw/<yyyy-mm>.txt is one statement for that month (+ the special two-column file), sorted by month."""
    found = []
    for name in sorted(os.listdir(raw_dir)):
        if name in SPECIAL:
            found += [(name, col, key) for col, key in SPECIAL[name]]
        elif RAW_NAME.match(name):
            found.append((name, 0, name[:-4]))
    found.sort(key=lambda t: t[2])
    keys = [k for _, _, k in found]
    assert len(keys) == len(set(keys)), f'duplicate month in raw files: {keys}'
    return found

def consecutive(a, b):
    ya, ma = int(a[:4]), int(a[5:])
    return (ya * 12 + ma) + 1 == int(b[:4]) * 12 + int(b[5:])

def main(argv):
    global RAW
    raw_dir, data_dir = RAW, os.path.join(HERE, 'data')
    args = list(argv)
    while args:
        opt = args.pop(0)
        if opt == '--raw-dir': raw_dir = args.pop(0)
        elif opt == '--data-dir': data_dir = args.pop(0)
        else: sys.exit(f'unknown option {opt}')
    RAW = raw_dir
    os.makedirs(data_dir, exist_ok=True)
    prev = None
    RECON = []
    for f, col, key in discover(raw_dir):
        rec = parse_file(f, col, 1, 2, key)
        json.dump(rec, open(os.path.join(data_dir, f'{key}.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        P = rec['pl']; B = rec['bs']
        # roll-forwards across consecutive months only
        if prev is not None and consecutive(prev['month'], key):
            dep = sum(rec['ga_accounts'].get(k, 0) for k in ('Biaya Penyusutan Gedung', 'Biaya Penyusutan Peralatan Kantor', 'Biaya Penyusutan Peralatan Bengkel'))
            d_acc = prev['bs']['AKUMULASI PENYUSUTAN'] - B['AKUMULASI PENYUSUTAN']
            if abs(d_acc - dep) >= 2:   # a real inconsistency in the books, not a parsing error: record it, do not hide it
                RECON.append({'month': key, 'test': 'akumulasi penyusutan vs beban penyusutan', 'bs_movement': d_acc, 'pl_charge': dep, 'gap': dep - d_acc})
            if key >= '2026-02':   # equity roll-forward is tested from Feb 2026 (the opening year's equity moved for other reasons)
                gap = B['Jumlah Ekuitas'] - (prev['bs']['Jumlah Ekuitas'] + P['net_profit'])
                if abs(gap) >= 10:   # equity moved by more than the month's result: an adjustment posted straight to equity
                    RECON.append({'month': key, 'test': 'mutasi ekuitas (ekuitas awal + laba rugi = ekuitas akhir)', 'expected': prev['bs']['Jumlah Ekuitas'] + P['net_profit'], 'booked': B['Jumlah Ekuitas'], 'gap': gap})
        elif prev is not None:
            print(f"WARNING: {prev['month']} -> {key} are not consecutive months; roll-forward tests skipped for {key}")
        prev = rec
        print(f"{key}  sales {P['sales']['total']/1e6:8.1f}  net rev {P['net_revenue']/1e6:8.1f}  GP {P['gross_profit']/1e6:7.1f}  opex {P['opex']/1e6:7.1f}  net {P['net_profit']/1e6:8.1f}  | FA cost {B['AKTIVA TETAP']/1e6:8.1f}  accdep {B['AKUMULASI PENYUSUTAN']/1e6:8.1f}  equity {B['Jumlah Ekuitas']/1e6:8.1f}  | ga leaves {len(rec['ga_accounts'])} sell {len(rec['selling_accounts'])}")
    json.dump(RECON, open(os.path.join(data_dir, 'recon_exceptions.json'), 'w'), indent=1)
    print('all months parsed and reconciled; exceptions:', RECON)

if __name__ == '__main__':
    main(sys.argv[1:])
