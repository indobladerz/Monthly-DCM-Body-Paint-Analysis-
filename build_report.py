#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Menyusun tinjauan keuangan tiga bulan Body & Paint PT Duta Cendana Mobilindo (PT DCM Body Paint).

Membaca data/<yyyy-mm>.json (hasil parse_dcm.py dari laporan Neraca & Laba Rugi bulanan ACCURATE) dan
data/raw/group_inhouse.json (angka dealer utama PT DCM), lalu menulis out/report.html. Setiap angka dalam
laporan dihitung di sini dari berkas tersebut; tidak ada yang diketik manual. Laporan dalam Bahasa Indonesia,
format angka Indonesia (titik ribuan, koma desimal).
"""
import json, os, base64, html, math

HERE = os.path.dirname(os.path.abspath(__file__))
ALL = ['2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09']
Y26 = [m for m in ALL if m.startswith('2026')]
MONTHS = ['2026-07', '2026-08', '2026-09']
MLABEL = {'2026-07': 'Juli 2026', '2026-08': 'Agustus 2026', '2026-09': 'September 2026'}
MSHORT = {'2025-09': 'Sep 25', '2025-10': 'Okt 25', '2025-11': 'Nov 25', '2025-12': 'Des 25', '2026-01': 'Jan', '2026-02': 'Feb', '2026-03': 'Mar',
          '2026-04': 'Apr', '2026-05': 'Mei', '2026-06': 'Jun', '2026-07': 'Jul', '2026-08': 'Agu', '2026-09': 'Sep'}
D = {m: json.load(open(os.path.join(HERE, 'data', f'{m}.json'), encoding='utf-8')) for m in ALL}
G = json.load(open(os.path.join(HERE, 'data', 'raw', 'group_inhouse.json'), encoding='utf-8'))
RECON = json.load(open(os.path.join(HERE, 'data', 'recon_exceptions.json'), encoding='utf-8'))

# ------------------------------------------------------------------ pembantu format
def idn(v, dec=1):
    s = f'{v:,.{dec}f}'
    return s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')

def rp(x, dec=1):
    """Rupiah dalam juta, negatif dalam kurung."""
    if x is None:
        return 't/a'
    v = x / 1e6
    s = idn(abs(v), dec)
    return f'({s})' if v < 0 else s

def rpbn(x):
    return idn(x / 1e9, 2)

def pct(x, dec=1, sign=True):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return 't/b'
    v = x * 100
    s = idn(abs(v), dec)
    if sign:
        return ('+' if v >= 0 else '-') + s + '%'
    return ('-' if v < 0 else '') + s + '%'

def p0(x): return pct(x, 0, sign=False)
def p1(x): return pct(x, 1, sign=False)

def chg(a, b):
    if a is None or b is None or abs(a) < 1e5:
        return None
    return (b - a) / abs(a)

def esc(s): return html.escape(str(s))

def ga(m, acct): return D[m]['ga_accounts'].get(acct, 0.0)
def sell(m, acct): return D[m]['selling_accounts'].get(acct, 0.0)
def bs(m, k): return D[m]['bs'].get(k, 0.0)

# ------------------------------------------------------------------ metrik per bulan
M = {}
for m in ALL:
    P = D[m]['pl']; r = {}
    r['sales_jasa'] = P['sales']['jasa']; r['sales_parts'] = P['sales']['sparepart'] + P['sales']['lainnya']; r['sales'] = P['sales']['total']
    r['disc_jasa'] = P['discount']['jasa']; r['disc_parts'] = P['discount']['sparepart'] + P['discount']['lainnya']; r['disc'] = P['discount']['total']
    r['net_sales'] = P['net_revenue']; r['net_jasa'] = r['sales_jasa'] - r['disc_jasa']; r['net_parts'] = r['sales_parts'] - r['disc_parts']
    r['cogs_jasa'] = P['cogs']['jasa']; r['cogs_parts'] = P['cogs']['sparepart'] + P['cogs']['lainnya']; r['cogs'] = P['cogs']['total']
    r['gp'] = P['gross_profit']; r['gp_jasa'] = r['net_jasa'] - r['cogs_jasa']; r['gp_parts'] = r['net_parts'] - r['cogs_parts']
    r['gm'] = r['gp'] / r['net_sales'] if r['net_sales'] else float('nan')
    r['gm_jasa'] = r['gp_jasa'] / r['net_jasa'] if r['net_jasa'] else float('nan')
    r['gm_parts'] = r['gp_parts'] / r['net_parts'] if r['net_parts'] else float('nan')
    r['tp_share'] = r['cogs_jasa'] / r['net_jasa'] if r['net_jasa'] else float('nan')      # harga pokok jasa = bagi hasil pihak ketiga
    r['selling'] = P['selling']; r['ga'] = P['ga']; r['opex'] = P['opex']; r['op'] = P['op_profit']
    r['other'] = P['other_income'] - P['other_expense']; r['net'] = P['net_profit']
    r['dep_bldg'] = ga(m, 'Biaya Penyusutan Gedung'); r['dep_office'] = ga(m, 'Biaya Penyusutan Peralatan Kantor'); r['dep_equip'] = ga(m, 'Biaya Penyusutan Peralatan Bengkel')
    r['dep'] = r['dep_bldg'] + r['dep_office'] + r['dep_equip']
    r['cash_opex'] = r['opex'] - r['dep']; r['ebitda'] = r['net'] + r['dep']
    r['disc_rate'] = r['disc'] / r['sales'] if r['sales'] else float('nan')
    r['gaji'] = ga(m, 'Biaya Gaji'); r['insentif'] = ga(m, 'Biaya Insentif')
    r['ar'] = bs(m, 'PIUTANG USAHA'); r['dso'] = r['ar'] / r['sales'] * 30 if r['sales'] else float('nan')
    r['inv_parts'] = bs(m, 'Persediaan Spare Part'); r['inv_bahan'] = bs(m, 'Persediaan Bahan'); r['inv'] = bs(m, 'PERSEDIAAN')
    r['cash'] = bs(m, 'KAS & BANK'); r['hutang_ho'] = bs(m, 'HUTANG AFILIASI'); r['piutang_gr'] = bs(m, 'Piutang Afiliasi')
    r['grir'] = bs(m, 'GR/IR ACCOUNT'); r['grir_parts'] = bs(m, 'GR/IR - Sparepart'); r['grir_bahan'] = bs(m, 'GR/IR - Bahan/OPL')
    r['ho_clearing'] = -bs(m, 'Piutang Transaksi Cabang'); r['equity'] = bs(m, 'Jumlah Ekuitas'); r['assets'] = bs(m, 'Jumlah Aktiva')
    r['uang_muka'] = bs(m, 'UANG MUKA PENJUALAN')
    r['fa_bldg_cost'] = bs(m, 'Bangunan'); r['fa_equip_cost'] = bs(m, 'Peralatan Bengkel'); r['fa_office_cost'] = bs(m, 'Peralatan Kantor'); r['fa_cost'] = bs(m, 'AKTIVA TETAP')
    r['acc_bldg'] = -bs(m, 'Akumulasi Penyusutan Gedung'); r['acc_equip'] = -bs(m, 'Akumulasi Penyusutan Peralatan Bengkel'); r['acc_office'] = -bs(m, 'Akumulasi Penyusutan Peralatan Kantor'); r['acc'] = -bs(m, 'AKUMULASI PENYUSUTAN')
    r['nbv_bldg'] = r['fa_bldg_cost'] - r['acc_bldg']; r['nbv_equip'] = r['fa_equip_cost'] - r['acc_equip']; r['nbv_office'] = r['fa_office_cost'] - r['acc_office']; r['nbv'] = bs(m, 'Jumlah Aktiva Tetap')
    M[m] = r

S, A, J = M['2026-09'], M['2026-08'], M['2026-07']
def tot(key, months): return sum(M[m][key] for m in months)
YTD = {k: tot(k, Y26) for k in ['sales', 'sales_jasa', 'sales_parts', 'disc', 'net_sales', 'cogs', 'gp', 'selling', 'ga', 'opex', 'dep', 'net', 'ebitda', 'cash_opex', 'insentif', 'gaji']}
INC = {k: tot(k, ALL) for k in ['sales', 'net_sales', 'gp', 'opex', 'dep', 'net', 'ebitda']}       # sejak dibuka, Sep 2025
H1 = {k: tot(k, Y26[:6]) for k in ['sales', 'net', 'cash_opex', 'ebitda', 'net_sales', 'gp']}
Q3 = {k: tot(k, MONTHS) for k in ['sales', 'net', 'opex', 'dep', 'ebitda', 'cash_opex', 'net_sales', 'gp', 'disc', 'selling', 'ga']}
assert abs(YTD['net'] - bs('2026-09', 'Laba tahun ini')) < 10, 'laba tahun berjalan tidak cocok dengan neraca'
nov_gap0 = next((x['gap'] for x in RECON if x['month'] == '2025-11'), 0.0)
inc_gap = S['equity'] - INC['net']           # ≈ Rp 1,04 juta: koreksi penyusutan Nov 2025 dibukukan ke neraca tanpa laporan laba rugi bulanan diterbitkan ulang
assert abs(inc_gap - nov_gap0) < 100, 'akumulasi rugi sejak dibuka tidak cocok dengan ekuitas'
INC['net_sum_pl'] = INC['net']; INC['net'] = S['equity']   # angka resmi sejak dibuka = ekuitas (rugi ditahan 2025 + laba tahun berjalan)

# ------------------------------------------------------------------ aset tetap & penyusutan
bldg_rate = S['dep_bldg'] * 12 / S['fa_bldg_cost']; bldg_life_y = 1 / bldg_rate
equip_rate = S['dep_equip'] * 12 / S['fa_equip_cost']; equip_life_y = 1 / equip_rate
office_rate = S['dep_office'] * 12 / S['fa_office_cost']
bldg_pct = S['acc_bldg'] / S['fa_bldg_cost']; equip_pct = S['acc_equip'] / S['fa_equip_cost']; office_pct = S['acc_office'] / S['fa_office_cost']
bldg_months_left = S['nbv_bldg'] / S['dep_bldg']; equip_months_left = S['nbv_equip'] / S['dep_equip']; office_months_left = S['nbv_office'] / S['dep_office']
equip_share_dep = S['dep_equip'] / S['dep']
dep_equip_8y = S['fa_equip_cost'] / 96.0                      # bila umur ekonomis oven/booth 8 tahun
dep_saving_8y = S['dep_equip'] - dep_equip_8y
asset_turnover = S['sales'] * 12 / S['fa_cost']
bldg_add_sep = S['fa_bldg_cost'] - A['fa_bldg_cost']
# alokasi kelompok: tanah & gedung vs peralatan
dep_land_bldg = S['dep_bldg']; dep_equipment = S['dep_equip'] + S['dep_office']
HO_LAND = 3616000000.0; HO_INV_LAND_BLDG = 28572803000.0        # neraca inhouse PT DCM, September 2026

def month_add(y, mo, k):
    mo += k
    y += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    return y, mo
ID_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
ID_MONL = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
ey, em = month_add(2026, 9, math.ceil(equip_months_left)); equip_end = f'{ID_MONL[em-1]} {ey}'
by, bm = month_add(2026, 9, math.ceil(bldg_months_left)); bldg_end = f'{by}'

# proyeksi beban penyusutan per tahun pada kebijakan saat ini (berdasarkan tarif September 2026, tanpa penambahan aset)
def dep_by_year():
    out = {}
    out[2025] = [sum(M[m]['dep_equip'] for m in ALL[:4]), sum(M[m]['dep_bldg'] for m in ALL[:4]), sum(M[m]['dep_office'] for m in ALL[:4])]
    eq_nbv, of_nbv = S['nbv_equip'], S['nbv_office']
    ytd = [YTD['dep'] - sum(M[m]['dep_bldg'] + M[m]['dep_office'] for m in Y26), sum(M[m]['dep_bldg'] for m in Y26), sum(M[m]['dep_office'] for m in Y26)]
    for y in range(2026, 2031):
        start = 10 if y == 2026 else 1
        eq = bl = of = 0.0
        if y == 2026:
            eq, bl, of = ytd
        for mo in range(start, 13):
            e = min(S['dep_equip'], max(eq_nbv, 0)); eq_nbv -= e; eq += e
            o = min(S['dep_office'], max(of_nbv, 0)); of_nbv -= o; of += o
            bl += S['dep_bldg']
        out[y] = [eq, bl, of]
    return out
DEP_YEARS = dep_by_year()

# ------------------------------------------------------------------ titik impas & skenario (bulanan, Rupiah)
gm_sep, gm_aug, gm_jul = S['gm'], A['gm'], J['gm']
be_net_now = S['opex'] / gm_sep
be_gross_now = be_net_now / (1 - S['disc_rate'])
cash_be_gross = (S['cash_opex'] / gm_sep) / (1 - S['disc_rate'])
opex_8y = S['opex'] - dep_saving_8y
be_gross_8y = (opex_8y / gm_sep) / (1 - S['disc_rate'])
cash_opex_h1 = H1['cash_opex'] / 6

def scenario(gross, gm, opex):
    return gross * (1 - S['disc_rate']) * gm - opex + S['other']

SCEN = [
    ('A', 'September 2026 sesuai laporan', S['sales'], gm_sep, S['opex'], 'Aktual'),
    ('B', 'Volume sama, margin kotor kembali ke level Agustus', S['sales'], gm_aug, S['opex'], f'Margin kotor {p1(gm_aug)} alih-alih {p1(gm_sep)}'),
    ('C', 'Volume +25% dari rujukan dealer, margin & opex September', S['sales'] * 1.25, gm_sep, S['opex'], f'Penjualan bruto Rp {rp(S["sales"]*1.25,0)} juta'),
    ('D', 'Target Rp 400 juta/bulan, margin Agustus, opex tunai +10%', 400e6, gm_aug, S['opex'] + S['cash_opex'] * 0.10, f'Volume +{idn((400e6/S["sales"]-1)*100,0)}% vs Sep'),
    ('E', 'Skenario D + umur oven/booth 8 tahun', 400e6, gm_aug, S['opex'] + S['cash_opex'] * 0.10 - dep_saving_8y, f'Penyusutan peralatan turun Rp {rp(dep_saving_8y)} juta'),
]
SCEN_RES = [(c, n, g, gm, ox, scenario(g, gm, ox), note) for c, n, g, gm, ox, note in SCEN]

# ------------------------------------------------------------------ buku besar akun per akun
ACCTS = []
for m in Y26:
    for a in D[m]['ga_accounts']:
        if a not in ACCTS: ACCTS.append(a)
SELL_ACCTS = []
for m in Y26:
    for a in D[m]['selling_accounts']:
        if a not in SELL_ACCTS: SELL_ACCTS.append(a)
ledger = []
for a in ACCTS:
    vals = [ga(m, a) for m in MONTHS]; ytd = sum(ga(m, a) for m in Y26)
    if any(vals) or ytd:
        ledger.append({'acct': a, 'type': 'Umum & Adm', 'jul': vals[0], 'aug': vals[1], 'sep': vals[2], 'ytd': ytd})
for a in SELL_ACCTS:
    vals = [sell(m, a) for m in MONTHS]; ytd = sum(sell(m, a) for m in Y26)
    if any(vals) or ytd:
        ledger.append({'acct': a, 'type': 'Penjualan', 'jul': vals[0], 'aug': vals[1], 'sep': vals[2], 'ytd': ytd})
for r in ledger:
    r['q3'] = r['jul'] + r['aug'] + r['sep']; r['share_sep'] = r['sep'] / S['opex']; r['share_q3'] = r['q3'] / Q3['opex']
    r['mom'] = chg(r['aug'], r['sep']); r['q'] = chg(r['jul'], r['sep'])
ledger.sort(key=lambda r: (-r['sep'], -r['q3']))
assert abs(sum(r['sep'] for r in ledger) - S['opex']) < 1, 'buku besar September tidak cocok dengan opex'
assert abs(sum(r['q3'] for r in ledger) - Q3['opex']) < 1, 'buku besar Kw III tidak cocok dengan opex'
assert abs(sum(r['ytd'] for r in ledger) - YTD['opex']) < 1, 'buku besar s.d. September tidak cocok dengan opex'

DESC = {
    'Biaya Penyusutan Peralatan Bengkel': 'Penyusutan peralatan bengkel',
    'Biaya Penyusutan Gedung': 'Penyusutan gedung bengkel',
    'Biaya Penyusutan Peralatan Kantor': 'Penyusutan peralatan kantor',
    'Biaya Gaji': 'Gaji pokok karyawan', 'Biaya Insentif': 'Insentif karyawan', 'Biaya Bonus/THR': 'Bonus / tunjangan hari raya',
    'Biaya BPJS Ketenagakerjaan': 'BPJS Ketenagakerjaan', 'Biaya BPJS Kesehatan': 'BPJS Kesehatan', 'Medical Expenses': 'Pengobatan karyawan',
    'Biaya makan dan Minum Karyawan': 'Makan dan minum karyawan', 'Biaya Mess Karyawan': 'Mess karyawan',
    'Biaya Listrik': 'Listrik', 'Biaya Telpon': 'Telepon', 'Biaya Internet': 'Internet',
    'Biaya Jasa Expedisi': 'Jasa ekspedisi', 'Biaya Materai': 'Materai', 'Biaya Asuransi Gedung': 'Asuransi gedung',
    'Biaya Training & Recruitment Material': 'Pelatihan dan rekrutmen', 'Biaya Keperluan Kantor Material': 'Keperluan kantor dan bengkel',
    'Biaya Alat Tulis Kantor Stationary': 'Alat tulis kantor', 'Biaya Print Material': 'Cetakan', 'Biaya Meeting dan Tamu': 'Rapat dan tamu',
    'Biaya Sumbangan': 'Sumbangan', 'Biaya Administrasi Bank': 'Administrasi bank',
    'Biaya Pemeliharaan Peralatan Kantor Matrial': 'Pemeliharaan peralatan (sekali, Agu)',
    'Biaya Pemeliharaan Kendaraan Material': 'Pemeliharaan kendaraan',
    'Biaya Iklan Dan Promosi': 'Iklan dan promosi', 'Biaya Customer Service': 'Layanan pelanggan', 'Biaya Komisi': 'Komisi penjualan',
    'Biaya Transportasi Material': 'Transportasi', 'Biaya Bahan Bakar': 'Bahan bakar', 'Biaya Accessories': 'Aksesori',
}
def desc(a): return DESC.get(a, a)
SDM = {'Biaya Gaji', 'Biaya Insentif', 'Biaya Bonus/THR', 'Biaya BPJS Ketenagakerjaan', 'Biaya BPJS Kesehatan', 'Medical Expenses',
       'Biaya makan dan Minum Karyawan', 'Biaya Mess Karyawan', 'Biaya Training & Recruitment Material'}
def cat(a):
    if a.startswith('Biaya Penyusutan'): return 'Penyusutan'
    if a in SDM: return 'SDM'
    if a in SELL_ACCTS: return 'Penjualan & promosi'
    return 'Fasilitas & administrasi'
CAT_COLOR = {'Penyusutan': 'var(--s1)', 'SDM': 'var(--s2)', 'Penjualan & promosi': 'var(--s3)', 'Fasilitas & administrasi': 'var(--s4)'}
cat_tot = {k: [0.0, 0.0, 0.0] for k in CAT_COLOR}
for r in ledger:
    for i, m in enumerate(['jul', 'aug', 'sep']):
        cat_tot[cat(r['acct'])][i] += r[m]

# ------------------------------------------------------------------ grafik SVG
def svg_open(w, h, cls='chart'):
    return f'<svg class="{cls}" viewBox="0 0 {w} {h}" width="100%" role="img" xmlns="http://www.w3.org/2000/svg" font-family="Inter, system-ui, sans-serif">'

def nice_max(v):
    if v <= 0: return 1
    e = 10 ** math.floor(math.log10(v))
    for k in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if k * e >= v: return k * e
    return 10 * e

def stacked_columns(series, cats, w=560, h=260, unit='juta', scale=1e6, dec=1):
    padl, padr, padt, padb = 48, 16, 14, 34
    tops = [sum(s[2][i] for s in series) for i in range(len(cats))]
    ymax = nice_max(max(tops) / scale)
    pw, ph = w - padl - padr, h - padt - padb
    out = [svg_open(w, h)]
    for k in range(5):
        y = padt + ph - ph * k / 4; val = ymax * k / 4
        out.append(f'<line x1="{padl}" y1="{y:.1f}" x2="{w-padr}" y2="{y:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        out.append(f'<text x="{padl-6}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{idn(val,0)}</text>')
    band = pw / len(cats); bw = min(52, band * 0.5)
    for i, c in enumerate(cats):
        x = padl + band * i + (band - bw) / 2; y0 = padt + ph
        for si, (name, color, vals) in enumerate(series):
            v = vals[i] / scale; hh = ph * v / ymax; top = y0 - hh
            gap = 2 if si < len(series) - 1 else 0; r = 4 if si == len(series) - 1 else 0
            if hh > 0:
                if r:
                    out.append(f'<path d="M{x},{y0} V{top+r} a{r},{r} 0 0 1 {r},-{r} H{x+bw-r} a{r},{r} 0 0 1 {r},{r} V{y0} Z" fill="{color}"><title>{esc(name)} {c}: Rp {idn(v,dec)} {unit}</title></path>')
                else:
                    out.append(f'<rect x="{x}" y="{top}" width="{bw}" height="{max(hh-gap,0):.1f}" fill="{color}"><title>{esc(name)} {c}: Rp {idn(v,dec)} {unit}</title></rect>')
                if hh > 16 and bw > 40:
                    out.append(f'<text x="{x+bw/2}" y="{top+(hh-gap)/2+4}" text-anchor="middle" font-size="11" fill="#fff" font-weight="600">{idn(v,0)}</text>')
            y0 = top
        out.append(f'<text x="{x+bw/2}" y="{y0-6}" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)">{idn(tops[i]/scale,dec)}</text>')
        out.append(f'<text x="{x+bw/2}" y="{h-12}" text-anchor="middle" font-size="12" fill="var(--ink2)">{c}</text>')
    out.append(f'<line x1="{padl}" y1="{padt+ph}" x2="{w-padr}" y2="{padt+ph}" stroke="var(--axis)" stroke-width="1"/>')
    out.append('</svg>')
    return ''.join(out)

def trend_chart(w=1000, h=300):
    """Pendapatan neto (batang) dengan laba bersih dan EBITDA (garis), Januari–September 2026."""
    padl, padr, padt, padb = 48, 16, 18, 34
    cats = Y26
    bars = [M[m]['net_sales'] for m in cats]; net = [M[m]['net'] for m in cats]; eb = [M[m]['ebitda'] for m in cats]
    hi = max(max(bars), max(eb)) / 1e6; lo = min(min(net), 0) / 1e6
    ymax = nice_max(hi); ymin = -nice_max(-lo) if lo < 0 else 0
    pw, ph = w - padl - padr, h - padt - padb
    def Y(v): return padt + ph * (ymax - v / 1e6) / (ymax - ymin)
    out = [svg_open(w, h)]
    for k in range(5):
        v = (ymin + (ymax - ymin) * k / 4) * 1e6
        out.append(f'<line x1="{padl}" y1="{Y(v):.1f}" x2="{w-padr}" y2="{Y(v):.1f}" stroke="var(--grid)"/>')
        out.append(f'<text x="{padl-6}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{idn(v/1e6,0)}</text>')
    band = pw / len(cats); bw = min(46, band * 0.55)
    for i, m in enumerate(cats):
        x = padl + band * i + (band - bw) / 2
        out.append(f'<path d="M{x},{Y(0)} V{Y(bars[i])+4} a4,4 0 0 1 4,-4 H{x+bw-4} a4,4 0 0 1 4,4 V{Y(0)} Z" fill="var(--s2)" opacity=".85"><title>Pendapatan neto {MSHORT[m]}: Rp {idn(bars[i]/1e6)} juta</title></path>')
        out.append(f'<text x="{x+bw/2}" y="{Y(bars[i])-5:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--ink)">{idn(bars[i]/1e6,0)}</text>')
        out.append(f'<text x="{x+bw/2}" y="{h-12}" text-anchor="middle" font-size="12" fill="var(--ink2)">{MSHORT[m]}</text>')
    for vals, color, name in ((eb, 'var(--s1)', 'EBITDA'), (net, 'var(--neg)', 'Laba (rugi) bersih')):
        pts = [(padl + band * i + band / 2, Y(v)) for i, v in enumerate(vals)]
        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>')
        for (x, y), v, m in zip(pts, vals, cats):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="var(--surface)" stroke-width="2"><title>{name} {MSHORT[m]}: Rp {idn(v/1e6)} juta</title></circle>')
            if name != 'EBITDA':
                out.append(f'<text x="{x:.1f}" y="{y+16:.1f}" text-anchor="middle" font-size="10.5" font-weight="600" fill="{color}">{idn(v/1e6,0)}</text>')
    out.append(f'<line x1="{padl}" y1="{Y(0):.1f}" x2="{w-padr}" y2="{Y(0):.1f}" stroke="var(--axis)" stroke-width="1.2"/>')
    out.append('</svg>')
    return ''.join(out)

def hbar_ranked(rows, w=1000, h=None, maxn=12):
    rows = rows[:maxn]; rh = 34; padl, padr, padt = 320, 150, 6
    h = h or padt + rh * len(rows) + 10
    vmax = max(r[2] for r in rows) / 1e6; pw = w - padl - padr
    out = [svg_open(w, h)]
    for i, (label, sub, v, color, share) in enumerate(rows):
        y = padt + rh * i; bw = pw * (v / 1e6) / vmax
        out.append(f'<text x="{padl-12}" y="{y+14}" text-anchor="end" font-size="13" fill="var(--ink)" font-weight="600">{esc(label)}</text>')
        out.append(f'<text x="{padl-12}" y="{y+27}" text-anchor="end" font-size="10.5" fill="var(--muted)">{esc(sub)}</text>')
        out.append(f'<path d="M{padl},{y+6} H{padl+bw-4} a4,4 0 0 1 4,4 V{y+20} a4,4 0 0 1 -4,4 H{padl} Z" fill="{color}"><title>{esc(label)}: Rp {idn(v/1e6)} juta ({p1(share)} dari opex)</title></path>')
        out.append(f'<text x="{padl+bw+10}" y="{y+19}" font-size="13" fill="var(--ink)" font-weight="700">{idn(v/1e6)}</text>')
        out.append(f'<text x="{padl+bw+10+50}" y="{y+19}" font-size="11.5" fill="var(--muted)">{p1(share)} dari opex</text>')
    out.append('</svg>')
    return ''.join(out)

def waterfall(steps, w=620, h=280):
    padl, padr, padt, padb = 44, 14, 16, 44
    run = 0; levels = []
    for lab, v, kind in steps:
        if kind == 'start': run = v; levels.append((0, v))
        elif kind == 'delta': levels.append((run, run + v)); run += v
        else: levels.append((0, v)); run = v
    lo = min(min(a, b) for a, b in levels + [(0, 0)]); hi = max(max(a, b) for a, b in levels)
    ymax = nice_max(hi / 1e6) * 1e6; ymin = -nice_max(-lo / 1e6) * 1e6 if lo < 0 else 0
    pw, ph = w - padl - padr, h - padt - padb
    def Y(v): return padt + ph * (ymax - v) / (ymax - ymin)
    out = [svg_open(w, h)]
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        out.append(f'<line x1="{padl}" y1="{Y(v):.1f}" x2="{w-padr}" y2="{Y(v):.1f}" stroke="var(--grid)"/>')
        out.append(f'<text x="{padl-6}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{idn(v/1e6,0)}</text>')
    band = pw / len(steps); bw = min(44, band * 0.6); prev_end = None
    for i, ((lab, v, kind), (a, b)) in enumerate(zip(steps, levels)):
        x = padl + band * i + (band - bw) / 2; top, bot = Y(max(a, b)), Y(min(a, b))
        color = ('var(--pos)' if v >= 0 else 'var(--neg)') if kind == 'delta' else ('var(--s1)' if b >= 0 else 'var(--neg)')
        out.append(f'<rect x="{x}" y="{top}" width="{bw}" height="{max(bot-top,1):.1f}" rx="3" fill="{color}"><title>{esc(lab)}: Rp {idn(v/1e6)} juta</title></rect>')
        if prev_end is not None:
            out.append(f'<line x1="{x-(band-bw)}" y1="{Y(a):.1f}" x2="{x}" y2="{Y(a):.1f}" stroke="var(--axis)"/>')
        lab_y = top - 6 if (kind != 'delta' and b >= 0) or (kind == 'delta' and v >= 0) else bot + 14
        txt = (('+' if v >= 0 else '-') + idn(abs(v)/1e6)) if kind == 'delta' else (('-' if v < 0 else '') + idn(abs(v)/1e6))
        out.append(f'<text x="{x+bw/2}" y="{lab_y:.1f}" text-anchor="middle" font-size="11.5" font-weight="600" fill="var(--ink)">{txt}</text>')
        for li, part in enumerate(lab.split('\n')):
            out.append(f'<text x="{x+bw/2}" y="{h-padb+16+li*12}" text-anchor="middle" font-size="10.5" fill="var(--ink2)">{esc(part)}</text>')
        prev_end = b
    out.append(f'<line x1="{padl}" y1="{Y(0):.1f}" x2="{w-padr}" y2="{Y(0):.1f}" stroke="var(--axis)" stroke-width="1.2"/>')
    out.append('</svg>')
    return ''.join(out)

def dep_year_chart(w=620, h=250):
    labels = ['2025*', '2026', '2027', '2028', '2029', '2030']
    eq = [DEP_YEARS[y][0] for y in range(2025, 2031)]; bl = [DEP_YEARS[y][1] for y in range(2025, 2031)]; of = [DEP_YEARS[y][2] for y in range(2025, 2031)]
    return stacked_columns([('Peralatan bengkel', 'var(--s1)', eq), ('Gedung', 'var(--s2)', bl), ('Peralatan kantor', 'var(--s3)', of)], labels, w=w, h=h, dec=0)

def segbar(parts, w=620, h=28):
    tot_ = sum(p[1] for p in parts); out = [svg_open(w, h)]; x = 0
    for lab, v, color in parts:
        if v <= 0: continue
        bw = w * v / tot_
        out.append(f'<rect x="{x:.1f}" y="0" width="{max(bw-2,0):.1f}" height="{h}" rx="4" fill="{color}"><title>{esc(lab)}: Rp {idn(v/1e6)} juta ({p1(v/tot_)})</title></rect>')
        if bw > 60:
            out.append(f'<text x="{x+8:.1f}" y="{h/2+4}" font-size="11.5" font-weight="600" fill="#fff">{p0(v/tot_)}</text>')
        x += bw
    out.append('</svg>')
    return ''.join(out)

def spark(vals, w=56, h=18, color='var(--s1)'):
    vmin, vmax = min(vals), max(vals); rng = (vmax - vmin) or 1; pts = []
    for i, v in enumerate(vals):
        x = 4 + (w - 8) * i / (len(vals) - 1); y = h - 4 - (h - 8) * (v - vmin) / rng; pts.append((x, y))
    d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(pts)); last = pts[-1]
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" class="spark"><path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="3.5" fill="{color}" stroke="var(--surface)" stroke-width="2"/></svg>')

def scen_chart(w=620, h=250):
    padl, padr, padt, padb = 44, 14, 16, 60
    vals = [r[5] for r in SCEN_RES]; hi = max(max(vals), 0); lo = min(min(vals), 0)
    ymax = nice_max(hi / 1e6) * 1e6 if hi > 0 else 0; ymin = -nice_max(-lo / 1e6) * 1e6 if lo < 0 else 0
    pw, ph = w - padl - padr, h - padt - padb
    def Y(v): return padt + ph * (ymax - v) / (ymax - ymin)
    out = [svg_open(w, h)]
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        out.append(f'<line x1="{padl}" y1="{Y(v):.1f}" x2="{w-padr}" y2="{Y(v):.1f}" stroke="var(--grid)"/>')
        out.append(f'<text x="{padl-6}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{idn(v/1e6,0)}</text>')
    band = pw / len(vals); bw = min(48, band * 0.5)
    for i, (code, name, g, gm, ox, net, note) in enumerate(SCEN_RES):
        x = padl + band * i + (band - bw) / 2; top, bot = Y(max(net, 0)), Y(min(net, 0))
        color = 'var(--pos)' if net >= 0 else 'var(--neg)'
        out.append(f'<rect x="{x}" y="{top:.1f}" width="{bw}" height="{max(bot-top,1):.1f}" rx="4" fill="{color}"><title>{esc(name)}: Rp {idn(net/1e6)} juta</title></rect>')
        ly = top - 6 if net >= 0 else bot + 14
        out.append(f'<text x="{x+bw/2}" y="{ly:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">{("+" if net >= 0 else "-") + idn(abs(net)/1e6)}</text>')
        out.append(f'<text x="{x+bw/2}" y="{h-padb+18}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">{code}</text>')
        out.append(f'<text x="{x+bw/2}" y="{h-padb+32}" text-anchor="middle" font-size="10" fill="var(--ink2)">Rp {idn(g/1e6,0)} jt · MK {p0(gm)}</text>')
        out.append(f'<text x="{x+bw/2}" y="{h-padb+44}" text-anchor="middle" font-size="10" fill="var(--muted)">opex {idn(ox/1e6,0)} jt</text>')
    out.append(f'<line x1="{padl}" y1="{Y(0):.1f}" x2="{w-padr}" y2="{Y(0):.1f}" stroke="var(--axis)" stroke-width="1.2"/>')
    out.append('</svg>')
    return ''.join(out)

def legend(items):
    return '<div class="legend">' + ''.join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in items) + '</div>'

# ------------------------------------------------------------------ angka pendukung temuan
ho_recv_bp = G['sep']['piutang_dcm_body_paint']; ic_gap = ho_recv_bp - S['hutang_ho']
clearing_gap = S['ho_clearing'] - G['sep']['pembukuan_pusat_cabang_bp']
ho_funding = S['ho_clearing'] + S['hutang_ho']
grir_months_cogs = S['grir'] / S['cogs']
cash_q3_change = S['cash'] - M['2026-06']['cash']; hutang_ho_q3_change = S['hutang_ho'] - M['2026-06']['hutang_ho']
idle_cash_income = S['cash'] * 0.05 / 12
bank_interest_sep = D['2026-09']['other_income_accounts'].get('Pendapatan Bunga Bank', 0.0)
maint_aug = ga('2026-08', 'Biaya Pemeliharaan Peralatan Kantor Matrial')
ins_rate = {m: M[m]['insentif'] / M[m]['sales'] for m in MONTHS}
disc_svc_rate = {m: M[m]['disc_jasa'] / M[m]['sales_jasa'] for m in MONTHS}
disc_parts_rate = {m: M[m]['disc_parts'] / M[m]['sales_parts'] for m in MONTHS}
best_net_month = max(Y26, key=lambda m: M[m]['net']); best_sales_month = max(ALL, key=lambda m: M[m]['sales'])
group_sales_sep = G['sep']['sales_gross']; bp_share = S['sales'] / (group_sales_sep + S['sales'])
aftersales_ho_sep = G['sep']['sales_sparepart'] + G['sep']['sales_service']
tp_to_40 = (S['tp_share'] - 0.40) * S['net_jasa']
ins_to_8pct = S['insentif'] - 0.08 * S['sales']
parts_to_aug = (A['gm_parts'] - S['gm_parts']) * S['net_parts']
vol_100 = 100e6 * (1 - S['disc_rate']) * gm_sep
reclass_jun = M['2026-05']['fa_office_cost'] - M['2026-06']['fa_office_cost']
nov_dep_gap = next((x['gap'] for x in RECON if x['month'] == '2025-11'), 0.0)
eq_adj = [x for x in RECON if x['test'].startswith('mutasi ekuitas')]

# ------------------------------------------------------------------ temuan
FINDINGS = []
def F(sev, area, title, body, evidence):
    FINDINGS.append(dict(sev=sev, area=area, title=title, body=body, evidence=evidence))

F('TINGGI', 'Profitabilitas',
  f'Rugi di setiap bulan sejak dibuka: Rp {rp(-J["net"])} juta di Juli, Rp {rp(-A["net"])} juta di Agustus, Rp {rp(-S["net"])} juta di September',
  f'Kuartal III merugi Rp {rp(-Q3["net"])} juta atas penjualan bruto Rp {rp(Q3["sales"])} juta. Sejak awal tahun rugi Rp {rp(-YTD["net"])} juta; sejak dibuka September 2025 rugi kumulatif Rp {rpbn(-INC["net"])} miliar, '
  f'sehingga ekuitas unit berada di Rp ({rpbn(-S["equity"])}) miliar tanpa modal disetor. September adalah bulan dengan rugi terkecil kedua tahun ini (terkecil: {ID_MONL[int(best_net_month[5:])-1]}, Rp {rp(-M[best_net_month]["net"])} juta), '
  f'dan pendapatan jasa September Rp {rp(S["sales_jasa"])} juta adalah yang tertinggi sejak dibuka.',
  'Laba Rugi PT DCM Body Paint, Sep 2025 – Sep 2026; Neraca September 2026, Ekuitas.')
F('TINGGI', 'Struktur biaya',
  f'Penyusutan mencapai {p0(S["dep"]/S["opex"])} dari beban operasional dan {p0(S["dep"]/S["net_sales"])} dari pendapatan neto',
  f'Rp {rp(S["dep"])} juta dari opex September Rp {rp(S["opex"])} juta adalah penyusutan: peralatan bengkel Rp {rp(S["dep_equip"])} juta, gedung Rp {rp(S["dep_bldg"])} juta, peralatan kantor Rp {rp(S["dep_office"])} juta. '
  f'Di luar penyusutan, unit menutup biayanya: EBITDA September Rp {rp(S["ebitda"])} juta setelah Juli Rp {rp(J["ebitda"])} juta dan Agustus Rp {rp(A["ebitda"])} juta (Agustus memuat biaya pemeliharaan satu kali Rp {rp(maint_aug)} juta). '
  f'Titik impas penuh memerlukan penjualan bruto Rp {rp(be_gross_now,0)} juta per bulan, {idn((be_gross_now/S["sales"]-1)*100,0)}% di atas September.',
  'Buku besar Beban Umum dan Administrasi; Neraca, Aktiva Tetap dan Akumulasi Penyusutan.')
F('TINGGI', 'Aset tetap',
  f'Basis aset Rp {rpbn(S["fa_cost"])} miliar berputar hanya {idn(asset_turnover,2)} kali setahun; oven dan booth disusutkan 4 tahun',
  f'Peralatan bengkel Rp {rpbn(S["fa_equip_cost"])} miliar dibebankan {p0(equip_rate)} per tahun (umur {idn(equip_life_y,0)} tahun), gedung Rp {rpbn(S["fa_bldg_cost"])} miliar {p0(bldg_rate)} per tahun (umur {idn(bldg_life_y,0)} tahun). '
  f'Untuk booth cat dan oven, umur ekonomis 8 tahun lazim dipakai; pada umur itu beban peralatan turun dari Rp {rp(S["dep_equip"])} juta menjadi Rp {rp(dep_equip_8y)} juta per bulan dan titik impas turun ke Rp {rp(be_gross_8y,0)} juta penjualan bruto. '
  f'Ini perubahan estimasi non-kas yang memerlukan bukti teknis serta pandangan auditor dan konsultan pajak, bukan alat untuk mengecilkan rugi. Tanah tidak tercatat di pembukuan unit (lihat §4).',
  'Neraca, Nilai histori dan Akumulasi Penyusutan; Laba Rugi, Biaya Penyusutan.')
F('TINGGI', 'Integritas pembukuan',
  f'Saldo antar perusahaan tidak cocok: selisih Rp {rp(ic_gap)} juta pada hutang HO dan Rp {rp(clearing_gap)} juta pada rekening pembukuan pusat',
  f'Unit mencatat Hutang HO Rp {rp(S["hutang_ho"])} juta, sedangkan dealer utama mencatat Piutang PT DCM Body Paint Rp {rp(ho_recv_bp)} juta. Keduanya cocok di Juli (Rp {rp(J["hutang_ho"])} juta); selisih Rp {rp(ic_gap)} juta muncul di Agustus ketika piutang Rp {rp(J["piutang_gr"])} juta kepada PT DCM GR hilang dari neraca unit. '
  f'Rekening Pembukuan Pusat HO di unit Rp {rpbn(S["ho_clearing"])} miliar, di dealer utama Rp {rpbn(G["sep"]["pembukuan_pusat_cabang_bp"])} miliar dan tidak bergerak sejak Januari. Akun kliring GR/IR Rp {rp(S["grir"])} juta setara {idn(grir_months_cogs)} bulan harga pokok dan terus naik; persediaan suku cadang bersaldo negatif Rp ({rp(-S["inv_parts"])}) juta.',
  'Neraca PT DCM Body Paint dan Neraca Inhouse PT DCM, Jul–Sep 2026.')
F('SEDANG', 'Pendapatan',
  f'Jasa tumbuh, suku cadang berayun: Rp {rp(J["sales_parts"])} → {rp(A["sales_parts"])} → {rp(S["sales_parts"])} juta dengan margin {p0(J["gm_parts"])}–{p0(A["gm_parts"])}',
  f'Pendapatan jasa naik {pct(chg(J["sales_jasa"], S["sales_jasa"]))} dalam kuartal ke Rp {rp(S["sales_jasa"])} juta dengan margin stabil {p1(S["gm_jasa"])}. Suku cadang turun {pct(chg(J["sales_parts"], S["sales_parts"]))} dan marginnya {p1(J["gm_parts"])} → {p1(A["gm_parts"])} → {p1(S["gm_parts"])}, '
  f'sementara harga pokok jasa tetap {p1(J["tp_share"])}–{p1(S["tp_share"])} dari pendapatan jasa neto di setiap bulan: pola bagi hasil tetap kepada tim pengerjaan pihak ketiga, bukan biaya yang mengikuti efisiensi.',
  'Laba Rugi, Penjualan dan Harga Pokok Penjualan per sumber.')
F('SEDANG', 'Kas dan pendanaan',
  f'Kas Rp {rpbn(S["cash"])} miliar menganggur (bunga bank September Rp {idn(bank_interest_sep,0)}) sementara Hutang HO naik Rp {rp(hutang_ho_q3_change)} juta dalam kuartal',
  f'Kas dan bank melonjak dari Rp {rp(M["2026-06"]["cash"])} juta (Juni) menjadi Rp {rp(S["cash"])} juta (September), sebagian dari penyelesaian piutang afiliasi Rp {rp(J["piutang_gr"])} juta dan sebagian dari dana HO. Dana ini tidak menghasilkan apa pun, sedangkan dealer utama memegang deposito Rp {idn(G["sep"]["deposito"]/1e9,0)} miliar. '
  f'Pada bunga ilustratif 5% per tahun, kas unit bernilai Rp {rp(idle_cash_income)} juta per bulan. Seluruh pendanaan HO (Rp {rpbn(ho_funding)} miliar) disajikan sebagai kliring, bukan pinjaman atau modal, sehingga biaya modal unit tidak pernah terlihat.',
  'Neraca, Kas dan Bank, Hutang Afiliasi, Piutang Transaksi Cabang; Neraca Inhouse PT DCM.')
F('SEDANG', 'Modal kerja',
  f'Piutang jasa naik {pct(chg(J["ar"], S["ar"]))} dalam tiga bulan menjadi Rp {rp(S["ar"])} juta ({idn(S["dso"],0)} hari penjualan)',
  f'Piutang bergerak Rp {rp(J["ar"])} → {rp(A["ar"])} → {rp(S["ar"])} juta, lebih cepat dari penjualan. Laporan tidak menyajikan umur piutang maupun rincian per perusahaan asuransi. Uang muka pelanggan turun dari Rp {rp(J["uang_muka"])} juta menjadi Rp {rp(S["uang_muka"])} juta, sehingga pekerjaan makin banyak dikerjakan sebelum dibayar.',
  'Neraca, Piutang Usaha dan Uang Muka Penjualan.')
F('SEDANG', 'Beban SDM dan sekali pakai',
  f'Insentif Rp {rp(S["insentif"])} juta hampir setara gaji pokok Rp {rp(S["gaji"])} juta pada unit yang merugi; Agustus memuat pemeliharaan Rp {rp(maint_aug)} juta',
  f'Insentif berjalan {p1(ins_rate["2026-07"])}, {p1(ins_rate["2026-08"])} dan {p1(ins_rate["2026-09"])} dari penjualan bruto di Juli, Agustus dan September, tidak terkait laba. '
  f'"Biaya Pemeliharaan Peralatan Kantor" Rp {rp(maint_aug)} juta di Agustus menyamai {p0(maint_aug/A["cash_opex"])} dari opex tunai bulan itu; untuk bengkel body & paint, pos sebesar ini kemungkinan perbaikan peralatan bengkel yang perlu ditinjau apakah layak dikapitalisasi atau direklasifikasi. '
  f'Juli juga memuat pelatihan Rp {rp(ga("2026-07","Biaya Training & Recruitment Material"))} juta dan rapat/tamu Rp {rp(ga("2026-07","Biaya Meeting dan Tamu"))} juta.',
  'Buku besar Beban Umum dan Administrasi, Jul–Sep 2026.')
F('RENDAH', 'Diskon',
  f'Diskon jasa {p1(disc_svc_rate["2026-09"])} dari penjualan jasa bruto di September, tertinggi dalam kuartal',
  f'Diskon total Rp {rp(S["disc"])} juta ({p1(S["disc_rate"])} dari penjualan bruto): jasa {p1(disc_svc_rate["2026-07"])} → {p1(disc_svc_rate["2026-08"])} → {p1(disc_svc_rate["2026-09"])}, suku cadang {p1(disc_parts_rate["2026-07"])} → {p1(disc_parts_rate["2026-08"])} → {p1(disc_parts_rate["2026-09"])}. '
  f'Diskon kuartal Rp {rp(Q3["disc"])} juta setara {p0(Q3["disc"]/-Q3["net"])} dari rugi kuartal. Tidak ada matriks persetujuan diskon per jenis pelanggan dalam laporan.',
  'Laba Rugi, Potongan Penjualan.')
F('RENDAH', 'Penyajian',
  'Empat pos penyajian yang perlu dirapikan dalam daftar aktiva dan ekuitas',
  f'(1) Rp {rp(reclass_jun)} juta dipindahkan dari Peralatan Kantor ke Bangunan pada Juni 2026 setelah dicatat sebagai peralatan kantor di April–Mei, padahal sudah disusutkan sebagai gedung sejak April. (2) Bangunan bertambah Rp {rp(bldg_add_sep)} juta di September 2026; fasilitas masih dilengkapi setahun setelah dibuka. '
  f'(3) November 2025: beban penyusutan pada laporan laba rugi Rp {rp(nov_dep_gap)} juta lebih besar dari mutasi akumulasi penyusutan, dan ekuitas memakai angka neraca; jumlah laba rugi bulanan yang diterbitkan melebihi rugi ditahan sebesar nilai yang sama. (4) Juli dan Agustus 2026: ekuitas bergerak Rp {idn(abs(eq_adj[0]["gap"]),0)} di luar laba rugi (dibalik bulan berikutnya). Tidak ada tanah di neraca unit.',
  'Neraca, Nilai histori, Akumulasi Penyusutan dan Ekuitas, Nov 2025 – Sep 2026.')

INTEGRITY = [
    ('Neraca seimbang (Aktiva = Kewajiban + Ekuitas)', True, 'Ketiga belas bulan cocok sampai ke rupiah.'),
    ('Mutasi ekuitas (ekuitas awal + laba rugi bulan = ekuitas akhir)', False, f'Juli {("+" if eq_adj[0]["gap"]>0 else "-")}Rp {idn(abs(eq_adj[0]["gap"]),0)} dan Agustus {("+" if eq_adj[1]["gap"]>0 else "-")}Rp {idn(abs(eq_adj[1]["gap"]),0)} di luar laba rugi (saling membalik, tanpa jurnal penjelas). September cocok.'),
    ('Akun rincian berjumlah sama dengan subtotal laba rugi', True, f'Penjualan, diskon, harga pokok, beban penjualan Rp {rp(S["selling"])} juta dan umum &amp; administrasi Rp {rp(S["ga"])} juta terbentuk kembali dari rincian akun pada setiap bulan.'),
    ('Mutasi akumulasi penyusutan = beban penyusutan yang dibukukan', True, f'Jul–Sep cocok (Rp {rp(S["dep"])} juta per bulan). Satu pengecualian historis: November 2025 selisih Rp {rp(nov_dep_gap)} juta.'),
    ('Tarif penyusutan konsisten per kelompok aset', True, f'Gedung {p1(bldg_rate)} per tahun, peralatan bengkel {p1(equip_rate)}, peralatan kantor {p1(office_rate)}; beban mengikuti penambahan aset (Apr dan Sep 2026).'),
    ('Saldo antar perusahaan cocok dengan dealer utama', False, f'Hutang HO Rp {rp(S["hutang_ho"])} juta vs Piutang PT DCM Body Paint Rp {rp(ho_recv_bp)} juta (selisih Rp {rp(ic_gap)} juta); pembukuan pusat selisih Rp {rp(clearing_gap)} juta.'),
    ('Akun kliring bersaldo wajar dan persediaan tidak negatif', False, f'GR/IR Rp {rp(S["grir"])} juta ({idn(grir_months_cogs)} bulan harga pokok) naik dari Rp {rp(J["grir"])} juta; persediaan suku cadang Rp ({rp(-S["inv_parts"])}) juta.'),
]

# ------------------------------------------------------------------ HTML
logo_b64 = base64.b64encode(open(os.path.join(HERE, 'dcm_logo.png'), 'rb').read()).decode()
today = '9 November 2026'

def kpi(label, value, sub, delta=None, good_up=True, cls=''):
    dl = ''
    if delta is not None:
        up = delta >= 0; good = up == good_up
        dl = f'<div class="delta {"good" if good else "bad"}">{"▲" if up else "▼"} {p1(abs(delta))} vs Agu</div>'
    return f'<div class="kpi {cls}"><div class="kl">{label}</div><div class="kv">{value}</div>{dl}<div class="ks">{sub}</div></div>'

def tr_money(label, vals, bold=False, cls='', fmt=rp):
    cells = ''.join(f'<td class="num">{fmt(v) if not isinstance(v, str) else v}</td>' for v in vals)
    return f'<tr class="{cls}{" bold" if bold else ""}"><td>{label}</td>{cells}</tr>'

def plr(label, key, bold=False, neg=False, cls=''):
    vals = [M[m][key] * (-1 if neg else 1) for m in MONTHS]; q = sum(vals); y = YTD[key] * (-1 if neg else 1)
    cells = ''.join(f'<td class="num">{rp(v)}</td>' for v in vals)
    return f'<tr class="{cls}{" bold" if bold else ""}"><td>{label}</td>{cells}<td class="num">{rp(q)}</td><td class="num">{rp(y)}</td><td class="num">{pct(chg(vals[1], vals[2]))}</td><td class="num">{pct(chg(vals[0], vals[2]))}</td></tr>'

YTD['other'] = tot('other', Y26); YTD['op'] = tot('op', Y26); YTD['gp_jasa'] = tot('gp_jasa', Y26); YTD['gp_parts'] = tot('gp_parts', Y26)
YTD['cogs_jasa'] = tot('cogs_jasa', Y26); YTD['cogs_parts'] = tot('cogs_parts', Y26)
pl_table = ''.join([
    plr('Pendapatan jasa (tenaga kerja &amp; cat)', 'sales_jasa'),
    plr('Penjualan suku cadang', 'sales_parts'),
    plr('Penjualan bruto', 'sales', bold=True, cls='sub'),
    plr('Potongan penjualan', 'disc', neg=True),
    plr('Pendapatan neto', 'net_sales', bold=True, cls='sub'),
    plr('Harga pokok jasa (bagi hasil tim pengerjaan)', 'cogs_jasa', neg=True),
    plr('Harga pokok suku cadang', 'cogs_parts', neg=True),
    plr('Laba kotor', 'gp', bold=True, cls='sub'),
    plr('Beban penjualan', 'selling', neg=True),
    plr('Beban umum &amp; administrasi', 'ga', neg=True),
    plr('Laba (rugi) operasi', 'op', bold=True, cls='sub'),
    plr('Pendapatan (beban) lain-lain, neto', 'other'),
    plr('Laba (rugi) bersih sebelum pajak', 'net', bold=True, cls='total'),
])
def memo_row(label, vals, fmt):
    return f'<tr class="memo"><td>{label}</td>' + ''.join(f'<td class="num">{fmt(v)}</td>' for v in vals) + '<td></td><td></td><td></td><td></td></tr>'
memo = ''.join([
    memo_row('Tingkat diskon atas penjualan bruto', [M[m]['disc_rate'] for m in MONTHS], p1),
    memo_row('Margin kotor jasa (atas neto)', [M[m]['gm_jasa'] for m in MONTHS], p1),
    memo_row('Margin kotor suku cadang (atas neto)', [M[m]['gm_parts'] for m in MONTHS], p1),
    memo_row('Margin kotor gabungan (atas neto)', [M[m]['gm'] for m in MONTHS], p1),
    memo_row('Harga pokok jasa, % pendapatan jasa neto', [M[m]['tp_share'] for m in MONTHS], p1),
    memo_row('EBITDA (Rp juta)', [M[m]['ebitda'] for m in MONTHS], rp),
])

def ledger_rows(rows):
    out = []
    for i, r in enumerate(rows):
        vals = [r['jul'], r['aug'], r['sep']]
        out.append(
            f'<tr><td class="rank">{i+1}</td><td><span class="dot" style="background:{CAT_COLOR[cat(r["acct"])]}"></span>{esc(r["acct"])}<div class="gloss">{esc(desc(r["acct"]))} · {r["type"]}</div></td>'
            f'<td class="num">{rp(r["jul"])}</td><td class="num">{rp(r["aug"])}</td><td class="num"><b>{rp(r["sep"])}</b></td>'
            f'<td class="num">{pct(r["mom"])}</td><td class="num">{pct(r["q"])}</td><td class="num">{rp(r["q3"])}</td><td class="num">{p1(r["share_q3"])}</td><td class="num">{rp(r["ytd"])}</td><td>{spark(vals)}</td></tr>')
    return ''.join(out)

ranked_rows = [(desc(r['acct']), r['acct'], r['sep'], CAT_COLOR[cat(r['acct'])], r['share_sep']) for r in ledger if r['sep'] > 0]
top3_share = sum(r['sep'] for r in ledger[:3]) / S['opex']
gaji = [M[m]['gaji'] for m in MONTHS]

rev_chart = stacked_columns([('Jasa (tenaga kerja & cat)', 'var(--s1)', [M[m]['sales_jasa'] for m in MONTHS]), ('Suku cadang', 'var(--s2)', [M[m]['sales_parts'] for m in MONTHS])], [MSHORT[m] for m in MONTHS], w=420, h=250)
gp_chart = stacked_columns([('Laba kotor jasa', 'var(--s1)', [M[m]['gp_jasa'] for m in MONTHS]), ('Laba kotor suku cadang', 'var(--s2)', [M[m]['gp_parts'] for m in MONTHS])], [MSHORT[m] for m in MONTHS], w=420, h=250)
opex_chart = stacked_columns([(k, CAT_COLOR[k], v) for k, v in sorted(cat_tot.items(), key=lambda kv: -kv[1][2])], [MSHORT[m] for m in MONTHS], w=420, h=250)
wf = waterfall([
    ('Laba\nkotor', S['gp'], 'start'), ('Beban\npenjualan', -S['selling'], 'delta'), ('U&A\ntunai', -(S['ga'] - S['dep']), 'delta'),
    ('EBITDA', S['ebitda'] - S['other'], 'total'), ('Peny.\nperalatan', -S['dep_equip'], 'delta'), ('Peny.\ngedung', -S['dep_bldg'], 'delta'),
    ('Peny. perl.\nkantor', -S['dep_office'], 'delta'), ('Lain-lain\nneto', S['other'], 'delta'), ('Laba (rugi)\nbersih', S['net'], 'total'),
], w=640, h=215)

fund_parts = [('Pembukuan Pusat HO (belanja modal)', S['ho_clearing'], 'var(--s1)'), ('Hutang HO (operasional)', S['hutang_ho'], 'var(--s2)'), ('GR/IR dan kewajiban lain', S['grir'] + bs('2026-09', 'HUTANG') - S['hutang_ho'] - S['grir'], 'var(--s4)')]

sev_cls = {'TINGGI': 'high', 'SEDANG': 'med', 'RENDAH': 'low'}
findings_html = ''.join(
    f'<div class="finding {sev_cls[f["sev"]]}"><div class="fh"><span class="sev">{f["sev"]}</span><span class="area">{esc(f["area"])}</span><span class="fn">Temuan {i+1}</span></div>'
    f'<h4>{esc(f["title"])}</h4><p>{esc(f["body"])}</p><div class="ev">Sumber: {esc(f["evidence"])}</div></div>' for i, f in enumerate(FINDINGS))
integrity_html = ''.join(f'<tr><td>{esc(n)}</td><td class="{"pass" if ok else "fail"}">{"LOLOS" if ok else "PERHATIAN"}</td><td>{note}</td></tr>' for n, ok, note in INTEGRITY)
scen_rows = ''.join(
    f'<tr><td class="rank">{c}</td><td>{esc(n)}<div class="gloss">{esc(note)}</div></td><td class="num">{rp(g)}</td><td class="num">{p1(gm)}</td><td class="num">{rp(ox)}</td><td class="num {"good" if net >= 0 else "bad"}"><b>{rp(net)}</b></td></tr>'
    for c, n, g, gm, ox, net, note in SCEN_RES)

RECS = [
    ('1', 'Isi kapasitas dari jaringan Toyota DCM sendiri, bukan dari belanja pemasaran',
     f'Dealer utama menjual unit Rp {idn(G["sep"]["sales_unit"]/1e9,1)} miliar dan jasa serta suku cadang Rp {rp(aftersales_ho_sep,0)} juta di September; body &amp; paint hanya Rp {rp(S["sales"])} juta, {p1(bp_share)} dari penjualan grup. '
     f'Jadikan setiap unit yang diserahkan sebagai pelanggan bengkel: rujukan rekanan asuransi saat serah terima, voucer perbaikan tahun pertama, booking silang oleh service advisor bengkel umum, dan akun armada. '
     f'Titik impas penuh pada basis biaya saat ini adalah penjualan bruto Rp {rp(be_gross_now,0)} juta per bulan (+{idn((be_gross_now/S["sales"]-1)*100,0)}%); setiap tambahan Rp 100 juta penjualan bruto menambah laba sekitar Rp {rp(vol_100)} juta karena biaya tunai hampir seluruhnya tetap.',
     f'Target: Rp 400 juta per bulan pada kuartal II 2027 (skenario D: rugi menyempit ke Rp {rp(SCEN_RES[3][5])} juta), Rp {rp(be_gross_now,0)} juta pada akhir 2027.'),
    ('2', 'Tinjau umur ekonomis oven dan booth bersama auditor dan konsultan pajak',
     f'Seluruh peralatan bengkel Rp {rpbn(S["fa_equip_cost"])} miliar disusutkan {idn(equip_life_y,0)} tahun ({p0(equip_rate)} per tahun). Bila oven, booth dan peralatan berat dipisahkan dan disusutkan 8 tahun sesuai umur teknisnya, beban turun Rp {rp(dep_saving_8y)} juta per bulan dan titik impas turun ke Rp {rp(be_gross_8y,0)} juta. '
     f'Perubahan ini non-kas, memerlukan dasar teknis (spesifikasi pabrikan, jadwal pemeliharaan) dan konsistensi dengan kebijakan grup; jangan dipakai hanya untuk memperkecil rugi.',
     f'Dampak: ≈ Rp {rp(dep_saving_8y)} juta per bulan pada laba pembukuan, nol pada kas (skenario E: Rp {rp(SCEN_RES[4][5])} juta).'),
    ('3', 'Ubah skema bagi hasil pihak ketiga dan insentif agar mengikuti laba, bukan penjualan',
     f'Harga pokok jasa tetap {p1(S["tp_share"])} dari pendapatan jasa neto, sementara insentif berjalan {p1(ins_rate["2026-09"])} dari penjualan bruto. Keduanya dibayar penuh pada bulan rugi. '
     f'Terapkan tingkatan bagi hasil berbasis volume (40% hingga Rp 150 juta jasa per bulan, 45% di atasnya), biaya pemakaian booth/oven yang dipotong dari bagi hasil, klausul pengerjaan ulang, dan insentif yang dibayar dari EBITDA positif dengan batas 8% dari penjualan bruto.',
     f'Dampak: ≈ Rp {rp(tp_to_40)} juta (bagi hasil ke 40%) + Rp {rp(ins_to_8pct)} juta (insentif ke 8%) per bulan pada volume September.'),
    ('4', 'Perbaiki penetapan harga pokok suku cadang dan tetapkan margin dasar',
     f'Margin suku cadang berayun {p1(S["gm_parts"])}–{p1(A["gm_parts"])} dalam tiga bulan, persediaan suku cadang negatif Rp ({rp(-S["inv_parts"])}) juta dan GR/IR suku cadang Rp {rp(S["grir_parts"])} juta menunjukkan barang dijual sebelum penerimaan dan tagihannya dicatat. '
     f'Cocokkan GR/IR dengan faktur dealer utama setiap bulan, pakai harga transfer yang disepakati, dan tetapkan margin dasar suku cadang {p0(A["gm_parts"])} per pekerjaan dengan matriks diskon (batas gabungan 7% dari penjualan bruto).',
     f'Dampak: ≈ Rp {rp(parts_to_aug)} juta per bulan (margin suku cadang kembali ke level Agustus) + Rp {rp((S["disc_rate"]-0.07)*S["sales"])} juta dari disiplin diskon.'),
    ('5', 'Rapikan pendanaan HO dan kas menganggur, lalu rekonsiliasi saldo antar perusahaan',
     f'Pindahkan kas yang tidak dibutuhkan (menyisakan sekitar satu bulan opex tunai, Rp {rp(S["cash_opex"],0)} juta) ke kantor pusat untuk melunasi Hutang HO Rp {rp(S["hutang_ho"])} juta, atau tempatkan dalam deposito. Catat pendanaan belanja modal Rp {rpbn(S["ho_clearing"])} miliar sebagai pinjaman antar perusahaan atau penyertaan modal dengan biaya bunga internal, agar manajer unit dinilai atas modal yang dipakainya. '
     f'Rekonsiliasi dan selesaikan selisih Rp {rp(ic_gap)} juta (Hutang HO vs piutang di dealer utama) dan Rp {rp(clearing_gap)} juta (pembukuan pusat) sebelum tutup buku 2026.',
     f'Dampak: ≈ Rp {rp(idle_cash_income)} juta per bulan pendapatan bunga pada tingkat grup; neraca unit yang dapat dipercaya.'),
    ('6', 'Tahan opex tunai di level semester I dan kendalikan pos sekali pakai',
     f'Opex tunai semester I rata-rata Rp {rp(cash_opex_h1)} juta per bulan; Juli Rp {rp(J["cash_opex"])} juta dan Agustus Rp {rp(A["cash_opex"])} juta karena pelatihan, rapat, keperluan kantor dan pemeliharaan Rp {rp(maint_aug)} juta. September kembali ke Rp {rp(S["cash_opex"])} juta. '
     f'Tetapkan plafon Rp {rp(cash_opex_h1,0)} juta per bulan, wajibkan persetujuan tertulis untuk pos di atas Rp 5 juta, dan tinjau pos pemeliharaan Agustus: bila perbaikan peralatan bengkel, kapitalisasi atau catat pada akun yang benar.',
     f'Dampak: menjaga EBITDA tetap positif; Rp {rp(Q3["cash_opex"]/3 - cash_opex_h1)} juta per bulan dibanding rata-rata kuartal III.'),
]
recs_html = ''.join(f'<div class="rec"><div class="rn">{n}</div><div><h4>{t}</h4><p>{b}</p><div class="impact">{esc(i)}</div></div></div>' for n, t, b, i in RECS)

path_rows = [
    ('Laba (rugi) bersih September 2026', S['net']),
    ('+ bagi hasil pihak ketiga ke 40% dari jasa neto', tp_to_40),
    ('+ insentif dibatasi 8% dari penjualan bruto', ins_to_8pct),
    ('+ margin suku cadang kembali ke level Agustus', parts_to_aug),
    ('+ bunga atas kas menganggur (5% p.a., tingkat grup)', idle_cash_income),
    ('+ volume +Rp 100 juta bruto pada margin September', vol_100),
    ('+ umur oven/booth 8 tahun (non-kas)', dep_saving_8y),
]
run = 0; path_html = ''
for i, (lab, v) in enumerate(path_rows):
    run = v if i == 0 else run + v
    path_html += f'<tr><td>{esc(lab)}</td><td class="num">{rp(v)}</td><td class="num {"good" if run >= 0 else "bad"}"><b>{rp(run)}</b></td></tr>'
dca_cmp = {'sales': 198458222.0, 'net': -39978530.43, 'dep': 59200000.0, 'gm': 0.387, 'ebitda': 19300000.0}

CSS = """
:root{--paper:#f6f5f1;--surface:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--navy:#1f1a5e;--navy2:#2a2379;--red:#d12a1e;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;
--pos:#1baf7a;--neg:#e34948;--good:#006300;--bad:#b42318;--warn:#fab219;--serious:#ec835a;--critical:#d03b3b;--ring:rgba(11,11,11,.10)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;font-size:13px;line-height:1.45}
.page{max-width:1080px;margin:0 auto;padding:28px 32px}
.cover{background:linear-gradient(135deg,#7a0d0d 0%,#a8191a 55%,#c9302c 100%);color:#fff;border-radius:18px;padding:36px 40px;position:relative;overflow:hidden}
.cover:after{content:"";position:absolute;right:-80px;top:-80px;width:360px;height:360px;border-radius:50%;background:rgba(255,255,255,.07)}
.cover .brand{display:flex;align-items:center;gap:16px;margin-bottom:26px}
.cover .brand img{height:44px;background:#fff;border-radius:8px;padding:4px 8px}
.cover .brand span{font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85}
.cover h1{font-size:34px;line-height:1.1;margin:0 0 10px;font-weight:800;letter-spacing:-.01em}
.cover h2{font-size:16px;font-weight:500;margin:0 0 22px;opacity:.9}
.cover .meta{display:flex;gap:28px;flex-wrap:wrap;font-size:12px;opacity:.9}
.cover .meta b{display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;opacity:.7;margin-bottom:2px;font-weight:600}
.pill{display:inline-block;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:3px 10px;font-size:11px;margin-right:6px}
h2.sec{font-size:20px;margin:34px 0 6px;font-weight:800;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
h2.sec .n{display:inline-flex;width:28px;height:28px;border-radius:8px;background:var(--navy);color:#fff;align-items:center;justify-content:center;font-size:13px}
p.lead{color:var(--ink2);margin:0 0 14px;max-width:860px}
.grid{display:grid;gap:14px}
.g4{grid-template-columns:repeat(4,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.g2{grid-template-columns:repeat(2,1fr)}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:16px 18px;break-inside:avoid}
.card.flow{break-inside:auto}
thead{display:table-header-group}
tr{break-inside:avoid}
table.ledger{font-size:11px;table-layout:fixed}
table.ledger td{padding:4px 6px}
table.ledger .gloss{font-size:10px}
table.ledger th:nth-child(1){width:3%}table.ledger th:nth-child(2){width:28%}table.ledger th:nth-child(11){width:8%}
table.ledger th.num{white-space:normal;line-height:1.2}
.card h3{margin:0 0 4px;font-size:14px;font-weight:700}
.card .sub{color:var(--muted);font-size:11.5px;margin-bottom:10px}
.kpi{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:14px 16px;break-inside:avoid}
.kpi .kl{font-size:11.5px;color:var(--ink2);margin-bottom:4px}
.kpi .kv{font-size:26px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.kpi .ks{font-size:11px;color:var(--muted);margin-top:4px}
.kpi .delta{font-size:11.5px;font-weight:600;margin-top:4px}
.kpi.hero{background:var(--navy);color:#fff;border:none}
.kpi.hero .kl,.kpi.hero .ks{color:rgba(255,255,255,.75)}
.kpi.hero .kv{font-size:40px}
.good{color:var(--good)}.bad{color:var(--bad)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--ink2);margin:6px 0 0}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
table{width:100%;border-collapse:collapse;font-size:12px;background:var(--surface);border-radius:12px;overflow:hidden}
th{background:#eeedf6;color:var(--navy);text-align:left;padding:8px 10px;font-size:11px;letter-spacing:.04em;text-transform:uppercase;font-weight:700;border-bottom:1px solid var(--grid)}
td{padding:7px 10px;border-bottom:1px solid var(--grid);vertical-align:middle}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.sub td{background:#fafaf7;font-weight:700}
tr.total td{background:#eeedf6;font-weight:800;border-top:2px solid var(--navy)}
tr.bold td{font-weight:700}
tr.memo td{color:var(--ink2);font-style:italic;background:#fcfcfa}
td.rank{color:var(--muted);width:28px;font-weight:700}
.gloss{color:var(--muted);font-size:10.5px}
.dot{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:7px;vertical-align:0}
td.pass{color:var(--good);font-weight:800}td.fail{color:var(--bad);font-weight:800}
.finding{background:var(--surface);border:1px solid var(--ring);border-left:6px solid var(--muted);border-radius:12px;padding:14px 16px;break-inside:avoid}
.finding.high{border-left-color:var(--critical)}.finding.med{border-left-color:var(--serious)}.finding.low{border-left-color:var(--warn)}
.finding .fh{display:flex;gap:10px;align-items:center;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.finding .sev{font-weight:800;padding:2px 8px;border-radius:999px;color:#fff;background:var(--muted)}
.finding.high .sev{background:var(--critical)}.finding.med .sev{background:var(--serious)}.finding.low .sev{background:var(--warn);color:#0b0b0b}
.finding .fn{margin-left:auto}
.finding h4{margin:0 0 6px;font-size:13.5px;line-height:1.3}
.finding p{margin:0 0 6px;color:var(--ink2)}
.finding .ev{font-size:10.5px;color:var(--muted)}
.rec{display:grid;grid-template-columns:44px 1fr;gap:14px;background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:16px 18px;break-inside:avoid}
.rec .rn{width:36px;height:36px;border-radius:10px;background:var(--red);color:#fff;font-weight:800;font-size:16px;display:flex;align-items:center;justify-content:center}
.rec h4{margin:0 0 6px;font-size:14px}
.rec p{margin:0 0 8px;color:var(--ink2)}
.rec .impact{font-size:12px;font-weight:700;color:var(--navy);background:#eeedf6;border-radius:8px;padding:6px 10px;display:inline-block}
.callout{background:#fff7f6;border:1px solid #f3c9c5;border-radius:14px;padding:14px 18px;color:#5b1a14}
.callout b{color:var(--red)}
.callout.blue{background:#eef4fd;border-color:#c5d8f5;color:#143a6b}.callout.blue b{color:#1c5cab}
.note{font-size:11px;color:var(--muted)}
.spark{vertical-align:middle}
.depbox{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.depbox .big{font-size:28px;font-weight:800;letter-spacing:-.02em}
.depbox ul{margin:8px 0 0;padding-left:18px;color:var(--ink2)}
.depbox li{margin:3px 0}
.meter{height:10px;border-radius:999px;background:#cde2fb;overflow:hidden;margin:8px 0 4px}
.meter i{display:block;height:100%;background:var(--s1);border-radius:999px}
footer{margin:40px 0 10px;font-size:11px;color:var(--muted);border-top:1px solid var(--grid);padding-top:12px}
@media print{
 @page{size:A4;margin:12mm 10mm}
 body{background:#fff;font-size:11.5px}
 .page{max-width:none;padding:0}
 .cover{border-radius:10px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
 .card,.kpi,.finding,.rec,table{box-shadow:none}
 h2.sec{break-after:avoid}
 .pb{break-before:page}
 .kpi .kv{font-size:22px}.kpi.hero .kv{font-size:34px}
 .cover{padding:20px 28px}.cover h1{font-size:26px}.cover h2{font-size:13px;margin-bottom:10px}.cover .brand{margin-bottom:12px}
 .callout{font-size:10.5px;padding:9px 13px;line-height:1.4}.kpi{padding:9px 13px}.kpi .ks{font-size:10px}
 h2.sec{margin-top:22px}p.lead{margin-bottom:10px}
}
"""

HTML = f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT DCM Body Paint — Tinjauan Keuangan, September 2026</title>
<style>{CSS}</style></head>
<body><div class="page">

<section class="cover">
 <div class="brand"><img src="data:image/png;base64,{logo_b64}" alt="DCM"><span>PT Duta Cendana Mobilindo · Dealer Toyota</span></div>
 <h1>Tinjauan bisnis Body &amp; Paint<br>PT DCM Body Paint, September 2026</h1>
 <h2>Ringkasan keuangan tiga bulan (Juli – September 2026), analisis sub-buku besar akun per akun, penyusutan gedung dan peralatan, dan jalan menuju laba</h2>
 <div class="meta">
  <div><b>Disusun untuk</b>Manajemen PT DCM</div>
  <div><b>Disusun oleh</b>Financial Controller (tinjauan analitis)</div>
  <div><b>Sumber</b>Laporan Neraca &amp; Rugi Laba PT DCM Body Paint, Juli / Agustus / September 2026 (ACCURATE)</div>
  <div><b>Diterbitkan</b>{today}</div>
 </div>
 <div style="margin-top:18px"><span class="pill">Semua angka dalam juta Rupiah kecuali disebutkan lain</span><span class="pill">Perbandingan bulan ke bulan, Juli → September</span><span class="pill">Bukan audit — tinjauan analitis atas laporan manajemen</span></div>
</section>

<h2 class="sec"><span class="n">1</span>Ringkasan eksekutif</h2>
<p class="lead">PT DCM Body Paint adalah bengkel body &amp; paint Toyota milik DCM yang dibuka September 2025 dengan belanja modal Rp {rpbn(S['fa_cost'])} miliar. September 2026: penjualan bruto Rp {rp(S['sales'])} juta, rugi Rp {rp(-S['net'])} juta. Volume tumbuh pesat, tetapi unit masih merugi setiap bulan karena penyusutan Rp {rp(S['dep'])} juta per bulan atas gedung dan peralatan untuk fasilitas yang baru terisi separuh dari yang diperlukan untuk impas.</p>
<div class="grid g4">
 {kpi('Laba (rugi) bersih, September', f'<span style="color:#ffb4ad">({rp(-S["net"])})</span>', f'Jul ({rp(-J["net"])}) · Agu ({rp(-A["net"])}) · s.d. Sep ({rp(-YTD["net"])})', cls='hero')}
 {kpi('Penjualan bruto', rp(S['sales']), f'Jul {rp(J["sales"])} · Agu {rp(A["sales"])} · {pct(chg(J["sales"], S["sales"]))} sepanjang kuartal', chg(A['sales'], S['sales']))}
 {kpi('Laba kotor', rp(S['gp']), f'Margin gabungan {p1(S["gm"])} dari pendapatan neto (Jul {p1(J["gm"])}, Agu {p1(A["gm"])})', chg(A['gp'], S['gp']))}
 {kpi('Beban operasional', rp(S['opex']), f'termasuk penyusutan {rp(S["dep"])} ({p0(S["dep"]/S["opex"])})', chg(A['opex'], S['opex']), good_up=False)}
</div>
<div class="grid g4" style="margin-top:14px">
 {kpi('EBITDA (hasil kas)', rp(S['ebitda']), f'Jul {rp(J["ebitda"])} · Agu {rp(A["ebitda"])} · kembali positif di September', chg(A['ebitda'], S['ebitda']) if abs(A['ebitda']) > 1e5 else None)}
 {kpi('Piutang jasa', rp(S['ar']), f'{idn(S["dso"],0)} hari penjualan · naik {pct(chg(J["ar"], S["ar"]))} dalam kuartal', chg(A['ar'], S['ar']), good_up=False)}
 {kpi('Ekuitas unit', f'<span class="bad">({rpbn(-S["equity"])}) miliar</span>', f'Akumulasi rugi sejak dibuka, tanpa modal disetor · dibiayai HO Rp {rpbn(ho_funding)} miliar')}
 {kpi('Kas dan bank', rpbn(S['cash']) + ' miliar', f'naik Rp {rp(cash_q3_change)} juta dalam kuartal · bunga bank September Rp {idn(bank_interest_sep,0)}')}
</div>
<div class="grid g2" style="margin-top:14px">
 <div class="callout"><b>Apa yang salah.</b> Fasilitas Rp {rpbn(S['fa_cost'])} miliar hanya menghasilkan Rp {rp(S['sales'])} juta per bulan ({idn(asset_turnover,2)} kali perputaran aset setahun), sehingga penyusutan Rp {rp(S['dep'])} juta memakan {p0(S['dep']/S['net_sales'])} dari pendapatan neto; peralatan bengkel disusutkan {idn(equip_life_y,0)} tahun, Rp {rp(S['dep_equip'])} juta per bulan sampai {equip_end}. Di atasnya, bagi hasil {p0(S['tp_share'])} kepada tim pihak ketiga dan insentif {p1(ins_rate['2026-09'])} dari penjualan dibayar penuh pada bulan rugi, dan saldo antar perusahaan berselisih Rp {rp(ic_gap)} juta.</div>
 <div class="callout blue"><b>Mengapa dapat diperbaiki.</b> Secara kas unit sudah menutup biayanya (EBITDA September Rp {rp(S['ebitda'])} juta) dan tumbuh: penjualan bruto naik dari Rp {rp(M['2026-01']['sales'])} juta (Januari) ke Rp {rp(S['sales'])} juta, pendapatan jasa September tertinggi sejak dibuka. Setiap tambahan Rp 100 juta penjualan bruto menambah laba sekitar Rp {rp(vol_100)} juta. Titik impas penuh Rp {rp(be_gross_now,0)} juta per bulan, atau Rp {rp(be_gross_8y,0)} juta bila umur oven dan booth ditinjau menjadi 8 tahun. Dealer utama menjual unit Rp {idn(G['sep']['sales_unit']/1e9,1)} miliar sebulan: sumber volume yang belum digarap (§7).</div>
</div>

<h2 class="sec pb"><span class="n">2</span>Analisis pendapatan, Juli sampai September 2026</h2>
<p class="lead">Dua sumber pendapatan: jasa (tenaga kerja dan cat, dikerjakan oleh tim pihak ketiga dengan bagi hasil) serta suku cadang yang dipasang pada pekerjaan perbaikan. Jasa tumbuh dan marginnya stabil; suku cadang berayun dan marginnya tipis. Diskon menyerap {p1(S['disc_rate'])} dari penjualan bruto di September. Seluruh unit ini baru {pct(bp_share, 2, sign=False)} dari penjualan grup DCM (dealer utama + unit).</p>
<div class="grid g3">
 <div class="card"><h3>Penjualan bruto per sumber</h3><div class="sub">Rp juta · bruto, sebelum diskon</div>{rev_chart}{legend([('Jasa (tenaga kerja & cat)', 'var(--s1)'), ('Suku cadang', 'var(--s2)')])}</div>
 <div class="card"><h3>Laba kotor per sumber</h3><div class="sub">Rp juta · setelah diskon dan harga pokok penjualan</div>{gp_chart}{legend([('Laba kotor jasa', 'var(--s1)'), ('Laba kotor suku cadang', 'var(--s2)')])}</div>
 <div class="card"><h3>Apa yang ditunjukkan kuartal ini</h3><div class="sub">Membaca kedua grafik bersama-sama</div>
  <ul style="margin:0;padding-left:18px;color:var(--ink2)">
   <li><b>Jasa adalah mesin pertumbuhan</b>: Rp {rp(J['sales_jasa'])} → {rp(A['sales_jasa'])} → {rp(S['sales_jasa'])} juta ({pct(chg(J['sales_jasa'], S['sales_jasa']))}); margin stabil {p1(S['gm_jasa'])} karena harga pokok jasa selalu {p1(S['tp_share'])} dari jasa neto (bagi hasil tetap).</li>
   <li><b>Suku cadang berayun</b>: Rp {rp(J['sales_parts'])} → {rp(A['sales_parts'])} → {rp(S['sales_parts'])} juta ({pct(chg(J['sales_parts'], S['sales_parts']))}); margin {p1(J['gm_parts'])} → {p1(A['gm_parts'])} → {p1(S['gm_parts'])}. Suku cadang {p0(S['sales_parts']/S['sales'])} dari penjualan tetapi hanya {p0(S['gp_parts']/S['gp'])} dari laba kotor.</li>
   <li><b>Agustus lemah di antara dua bulan terbaik</b>: penjualan bruto {pct(chg(J['sales'], A['sales']))} lalu {pct(chg(A['sales'], S['sales']))}; margin gabungan justru tertinggi di Agustus ({p1(A['gm'])}) karena bauran suku cadang kecil.</li>
   <li><b>Laju berjalan naik</b>: semester I rata-rata Rp {rp(H1['sales']/6)} juta per bulan, kuartal III Rp {rp(Q3['sales']/3)} juta (+{idn((Q3['sales']/3/(H1['sales']/6)-1)*100,0)}%).</li>
   <li><b>Diskon</b> Rp {rp(S['disc'])} juta di September (jasa {p1(disc_svc_rate['2026-09'])}, suku cadang {p1(disc_parts_rate['2026-09'])}), {p0(S['disc']/S['gp'])} dari laba kotor.</li>
  </ul></div>
</div>
<div class="card" style="margin-top:14px"><h3>Pendapatan neto, EBITDA dan laba (rugi) bersih per bulan, Januari–September 2026</h3><div class="sub">Rp juta · batang = pendapatan neto setelah diskon · garis biru = EBITDA (laba sebelum penyusutan) · garis merah = laba (rugi) bersih</div>{trend_chart(h=240)}{legend([('Pendapatan neto', 'var(--s2)'), ('EBITDA', 'var(--s1)'), ('Laba (rugi) bersih', 'var(--neg)')])}<p class="note" style="margin:6px 0 0">Jarak garis biru ke garis merah adalah penyusutan, Rp {rp(M['2026-01']['dep'])}–{rp(S['dep'])} juta per bulan.</p></div>
<div class="card" style="margin-top:14px"><h3>Laporan laba rugi unit, tiga bulan</h3><div class="sub">Rp juta · Laba/Rugi PT DCM Body Paint · beban disajikan sebagai angka negatif · s.d. Sep = Januari–September 2026</div>
<table><thead><tr><th>Pos</th><th class="num">Jul</th><th class="num">Agu</th><th class="num">Sep</th><th class="num">Total Kw III</th><th class="num">s.d. Sep</th><th class="num">Sep vs Agu</th><th class="num">Sep vs Jul</th></tr></thead>
<tbody>{pl_table}{memo}</tbody></table></div>

<h2 class="sec pb"><span class="n">3</span>Analisis sub-buku besar, akun per akun</h2>
<p class="lead">Seluruh akun beban operasional pada Beban Umum dan Administrasi serta Beban Penjualan, diperingkat menurut beban September. Rincian akun ini cocok sampai ke rupiah dengan baris beban di Laba Rugi pada ketiga bulan. Tiga akun, dua di antaranya penyusutan, membentuk {p0(top3_share)} dari opex September.</p>
<div class="card"><h3>Beban terbesar, September 2026</h3><div class="sub">Rp juta dan porsi dari total opex Rp {rp(S['opex'])} juta · 12 teratas dari {len(ranked_rows)} akun yang berbeban · warna = kategori biaya</div>{hbar_ranked(ranked_rows, w=1000)}{legend([(k, v) for k, v in CAT_COLOR.items()])}</div>
<div class="grid g2" style="margin-top:14px">
 <div class="card"><h3>Opex per kategori biaya, tiga bulan</h3><div class="sub">Rp juta</div>{opex_chart}{legend([(k, v) for k, v in CAT_COLOR.items()])}</div>
 <div class="card"><h3>Bagaimana basis biaya bergerak</h3><div class="sub">Membaca buku besar per kategori</div>
  <ul style="margin:0;padding-left:18px;color:var(--ink2)">
   <li><b>Penyusutan</b> Rp {rp(cat_tot['Penyusutan'][0])} juta → {rp(cat_tot['Penyusutan'][2])} juta per bulan ({p0(cat_tot['Penyusutan'][2]/S['opex'])} dari opex September); naik Rp {rp(cat_tot['Penyusutan'][2]-cat_tot['Penyusutan'][1])} juta di September karena penambahan bangunan Rp {rp(bldg_add_sep)} juta.</li>
   <li><b>SDM</b> (gaji, insentif, BPJS, mess, pelatihan): Rp {rp(cat_tot['SDM'][0])} juta → {rp(cat_tot['SDM'][1])} juta → {rp(cat_tot['SDM'][2])} juta. Gaji berayun antara Rp {rp(min(gaji))} juta dan Rp {rp(max(gaji))} juta; insentif Rp {rp(J['insentif'])} → {rp(A['insentif'])} → {rp(S['insentif'])} juta mengikuti penjualan, bukan laba.</li>
   <li><b>Fasilitas &amp; administrasi</b> Rp {rp(cat_tot['Fasilitas & administrasi'][0])} juta → {rp(cat_tot['Fasilitas & administrasi'][1])} juta → {rp(cat_tot['Fasilitas & administrasi'][2])} juta: lonjakan Agustus adalah pemeliharaan satu kali Rp {rp(maint_aug)} juta; listrik Rp {rp(ga('2026-09','Biaya Listrik'))} juta adalah pos rutin terbesar (oven dan kompresor).</li>
   <li><b>Penjualan &amp; promosi</b> kecil (Rp {rp(cat_tot['Penjualan & promosi'][2])} juta di September, terutama komisi); unit hampir tidak membelanjakan apa pun untuk mendatangkan pekerjaan.</li>
  </ul></div>
</div>
<div class="card flow pb" style="margin-top:14px"><h3>Buku besar akun lengkap</h3><div class="sub">Rp juta · diperingkat menurut September · "Porsi Kw III" adalah porsi akun terhadap opex Juli–September · "s.d. Sep" = Januari–September 2026 · grafik kecil menunjukkan pola tiga bulan</div>
<table class="ledger"><thead><tr><th>#</th><th>Akun (sebagaimana dibukukan) / keterangan</th><th class="num">Jul</th><th class="num">Agu</th><th class="num">Sep</th><th class="num">Sep vs Agu</th><th class="num">Sep vs Jul</th><th class="num">Total Kw III</th><th class="num">Porsi Kw III</th><th class="num">s.d. Sep</th><th>Tren</th></tr></thead>
<tbody>{ledger_rows(ledger)}
<tr class="total"><td></td><td>Total beban operasional</td><td class="num">{rp(J['opex'])}</td><td class="num">{rp(A['opex'])}</td><td class="num">{rp(S['opex'])}</td><td class="num">{pct(chg(A['opex'], S['opex']))}</td><td class="num">{pct(chg(J['opex'], S['opex']))}</td><td class="num">{rp(Q3['opex'])}</td><td class="num">100%</td><td class="num">{rp(YTD['opex'])}</td><td></td></tr>
</tbody></table>
<p class="note" style="margin:8px 0 0">Akun tanpa beban pada ketiga bulan dan nihil s.d. September tidak ditampilkan. Bonus/THR Rp {rp(sum(ga(m,'Biaya Bonus/THR') for m in Y26))} juta dibayarkan di Maret. Harga pokok penjualan (bagi hasil tim pengerjaan dan suku cadang) tidak termasuk opex dan dianalisis per sumber pendapatan di §2. "t/b" = tidak bermakna (basis mendekati nol).</p></div>

<h2 class="sec pb"><span class="n">4</span>Penyusutan: tanah &amp; gedung serta peralatan</h2>
<p class="lead">Fasilitas ini baru dibangun, sehingga penyusutan adalah pos biaya terbesar. Dua kelompok dibahas terpisah: tanah &amp; gedung (umur panjang, beban kecil) dan peralatan bengkel serta kantor (umur pendek, beban besar); angka ditelusuri dari nilai historis dan akumulasi penyusutan pada neraca unit.</p>
<div class="depbox">
 <div class="card"><h3>Tanah &amp; gedung</h3><div class="sub">Bangunan · Biaya Penyusutan Gedung · tanah tidak tercatat di unit</div>
  <div class="big">Rp {rp(S['dep_bldg'])} juta <span style="font-size:13px;color:var(--muted);font-weight:500">per bulan · {p0(S['dep_bldg']/S['dep'])} dari penyusutan</span></div>
  <div class="meter"><i style="width:{bldg_pct*100:.1f}%"></i></div>
  <div class="note">Gedung: harga perolehan Rp {rpbn(S['fa_bldg_cost'])} miliar, akumulasi Rp {rp(S['acc_bldg'])} juta ({p1(bldg_pct)} tersusutkan), nilai buku Rp {rpbn(S['nbv_bldg'])} miliar</div>
  <ul>
   <li><b>Tanah: nihil di neraca unit.</b> Tanah bengkel berada di luar pembukuan ini (dealer utama mencatat Tanah Rp {rpbn(HO_LAND)} miliar dan Investasi dalam Tanah &amp; Bangunan Rp {idn(HO_INV_LAND_BLDG/1e9,1)} miliar). Tanah tidak disusutkan, tetapi modal yang dipakai unit tersaji terlalu rendah dan tidak ada beban sewa atau biaya modal atasnya.</li>
   <li><b>Gedung</b> Rp {rpbn(S['fa_bldg_cost'])} miliar disusutkan {p1(bldg_rate)} per tahun (umur {idn(bldg_life_y,0)} tahun): Rp {rp(S['dep_bldg'])} juta per bulan, Rp {rp(sum(M[m]['dep_bldg'] for m in Y26))} juta sejak awal tahun, tersisa sekitar {idn(bldg_months_left/12,0)} tahun sampai {bldg_end}.</li>
   <li>Harga perolehan bertambah Rp {rp(reclass_jun)} juta (April 2026, semula dicatat sebagai peralatan kantor) dan Rp {rp(bldg_add_sep)} juta (September 2026); beban naik dari Rp {rp(M['2026-03']['dep_bldg'])} juta ke Rp {rp(S['dep_bldg'])} juta per bulan. Premi asuransi gedung habis Agustus 2026; perpanjangan polis perlu dipastikan.</li>
  </ul></div>
 <div class="card"><h3>Peralatan</h3><div class="sub">Peralatan Bengkel dan Peralatan Kantor · tercatat di neraca unit</div>
  <div class="big">Rp {rp(dep_equipment)} juta <span style="font-size:13px;color:var(--muted);font-weight:500">per bulan · {p0(dep_equipment/S['dep'])} dari penyusutan</span></div>
  <div class="meter"><i style="width:{equip_pct*100:.1f}%"></i></div>
  <div class="note">Peralatan bengkel: harga perolehan Rp {rpbn(S['fa_equip_cost'])} miliar, akumulasi Rp {rpbn(S['acc_equip'])} miliar ({p1(equip_pct)} tersusutkan), nilai buku Rp {rpbn(S['nbv_equip'])} miliar</div>
  <ul>
   <li><b>Peralatan bengkel</b> (oven, booth cat, perkakas) Rp {rpbn(S['fa_equip_cost'])} miliar disusutkan {p0(equip_rate)} per tahun (umur {idn(equip_life_y,0)} tahun): Rp {rp(S['dep_equip'])} juta per bulan sampai {equip_end}, sisa {idn(equip_months_left,0)} bulan; {p0(S['dep_equip']/S['opex'])} dari opex dan {p0(S['dep_equip']/S['net_sales'])} dari pendapatan neto September.</li>
   <li>Pada umur 8 tahun, yang lazim untuk booth dan oven, beban turun ke Rp {rp(dep_equip_8y)} juta per bulan (hemat Rp {rp(dep_saving_8y)} juta, non-kas); perlu pandangan auditor dan konsultan pajak serta pemisahan peralatan berat dari perkakas kecil dalam daftar aktiva.</li>
   <li><b>Peralatan kantor</b> Rp {rp(S['fa_office_cost'])} juta, Rp {rp(S['dep_office'])} juta per bulan, tersisa {idn(office_months_left,0)} bulan. Tidak ada penambahan peralatan di kuartal III; nilai buku seluruh aset tetap Rp {rpbn(S['nbv'])} miliar.</li>
  </ul></div>
</div>
<div class="grid g2" style="margin-top:14px">
 <div class="card"><h3>Beban penyusutan per tahun, aktual dan proyeksi</h3><div class="sub">Rp juta · 2025* = Sep–Des (sejak dibuka) · 2026 = aktual Jan–Sep + proyeksi Okt–Des · 2027–2030 pada tarif saat ini, tanpa penambahan aset · peralatan habis mengikuti sisa nilai bukunya</div>{dep_year_chart(w=620, h=190)}{legend([('Peralatan bengkel', 'var(--s1)'), ('Gedung', 'var(--s2)'), ('Peralatan kantor', 'var(--s3)')])}</div>
 <div class="card"><h3>Jembatan laba rugi September</h3><div class="sub">Rp juta · dari laba kotor ke laba (rugi) bersih · hijau menambah, merah mengurangi</div>{wf}</div>
</div>
<div class="callout" style="margin-top:14px"><b>Penyusutan adalah {p0(S['dep']/S['opex'])} dari opex dan {p0(S['dep']/S['net_sales'])} dari pendapatan neto.</b> Titik impas kas hanya memerlukan penjualan bruto Rp {rp(cash_be_gross,0)} juta per bulan dan sudah terlampaui; titik impas penuh memerlukan Rp {rp(be_gross_now,0)} juta ({idn(be_gross_now/S['sales'],2)} kali September), atau Rp {rp(be_gross_8y,0)} juta bila oven dan booth disusutkan 8 tahun. Beban peralatan baru berakhir {equip_end}: jalan keluarnya volume, bukan menunggu.</div>

<h2 class="sec pb"><span class="n">5</span>Neraca, modal kerja dan uji integritas</h2>
<div class="grid g2">
 <div class="card"><h3>Pendanaan unit, September</h3><div class="sub">Rp {rpbn(ho_funding + S['grir'] + (bs('2026-09','HUTANG') - S['hutang_ho'] - S['grir']))} miliar kewajiban dan pendanaan HO · komposisi</div>{segbar(fund_parts)}{legend([(n, c) for n, v, c in fund_parts])}
  <table style="margin-top:10px"><thead><tr><th></th><th class="num">Jul</th><th class="num">Agu</th><th class="num">Sep</th></tr></thead><tbody>
  {tr_money('Kas dan bank', [J['cash'], A['cash'], S['cash']])}
  {tr_money('Piutang jasa', [J['ar'], A['ar'], S['ar']])}
  {tr_money('Hari penjualan bruto (DSO)', [J['dso'], A['dso'], S['dso']], fmt=lambda v: idn(v, 0))}
  {tr_money('Piutang afiliasi (PT DCM GR)', [J['piutang_gr'], A['piutang_gr'], S['piutang_gr']])}
  {tr_money('Persediaan suku cadang', [J['inv_parts'], A['inv_parts'], S['inv_parts']], cls='bold')}
  {tr_money('Persediaan bahan', [J['inv_bahan'], A['inv_bahan'], S['inv_bahan']])}
  </tbody></table></div>
 <div class="card"><h3>Kewajiban dan pendanaan</h3><div class="sub">Rp juta · neraca unit</div>
  <table><thead><tr><th></th><th class="num">Jul</th><th class="num">Agu</th><th class="num">Sep</th></tr></thead><tbody>
  {tr_money('Uang muka pelanggan', [J['uang_muka'], A['uang_muka'], S['uang_muka']])}
  {tr_money('GR/IR suku cadang (diterima, belum ditagih)', [J['grir_parts'], A['grir_parts'], S['grir_parts']])}
  {tr_money('GR/IR bahan / pihak ketiga', [J['grir_bahan'], A['grir_bahan'], S['grir_bahan']])}
  {tr_money('Hutang HO', [J['hutang_ho'], A['hutang_ho'], S['hutang_ho']], cls='bold')}
  {tr_money('Pembukuan Pusat HO (pendanaan belanja modal)', [J['ho_clearing'], A['ho_clearing'], S['ho_clearing']])}
  {tr_money('Ekuitas unit', [J['equity'], A['equity'], S['equity']], bold=True)}
  </tbody></table>
  <p class="note" style="margin:8px 0 0">Ekuitas adalah akumulasi rugi: 2025 ({rp(-bs('2026-09','Laba Ditahun Tahun Sebelumnya'))}) dan 2026 s.d. September ({rp(-YTD['net'])}). Tidak ada modal yang disetor; seluruh aset dibiayai kantor pusat melalui rekening kliring tanpa bunga.</p></div>
</div>
<div class="card" style="margin-top:14px"><h3>Uji integritas</h3><div class="sub">Dijalankan pada setiap bulan dalam cakupan (dan ke belakang sampai September 2025) · LOLOS atau PERHATIAN</div>
  <table><thead><tr><th style="width:38%">Pengujian</th><th style="width:10%">Hasil</th><th>Catatan</th></tr></thead><tbody>{integrity_html}</tbody></table></div>

<h2 class="sec pb"><span class="n">6</span>Temuan, diurutkan menurut tingkat keparahan</h2>
<div class="grid g2">{findings_html}</div>

<h2 class="sec pb"><span class="n">7</span>Rekomendasi: menjadikan Body &amp; Paint menguntungkan</h2>
<p class="lead">Hitungannya jelas. Biaya tunai sudah tertutup; yang belum tertutup adalah Rp {rp(S['dep'])} juta penyusutan per bulan atas fasilitas yang baru terisi separuh. Volume dari pelanggan Toyota grup sendiri adalah tuas yang cukup besar; tuas lainnya (bagi hasil, insentif, suku cadang, kas, umur aset) menjaga agar setiap rupiah volume tambahan benar-benar menjadi laba.</p>
<div class="grid g2">
 <div class="card"><h3>Jalan menuju laba, Rp juta per bulan</h3><div class="sub">Setiap langkah pada volume September kecuali disebutkan · kumulatif pada kolom terakhir</div>
  <table><thead><tr><th>Langkah</th><th class="num">Efek</th><th class="num">Hasil bulanan</th></tr></thead><tbody>{path_html}</tbody></table>
  <p class="note" style="margin:8px 0 0">Langkah-langkah bersifat aditif dan merupakan pendekatan pada tingkat diskon September; bukan proyeksi. Tambahan volume dihitung pada margin gabungan September {p1(gm_sep)} setelah diskon {p1(S['disc_rate'])}. Langkah terakhir non-kas dan bergantung pada pandangan auditor.</p></div>
 <div class="card"><h3>Perbandingan skenario</h3><div class="sub">Laba (rugi) bersih bulanan, Rp juta · A adalah September sesuai laporan · MK = margin kotor</div>{scen_chart()}</div>
</div>
<div class="card" style="margin-top:14px"><h3>Asumsi dan hasil skenario</h3><div class="sub">Bulanan, Rp juta · tingkat diskon ditahan pada {p1(S['disc_rate'])} dari penjualan bruto di setiap skenario · opex tunai dianggap tetap kecuali disebutkan</div>
  <table><thead><tr><th style="width:4%"></th><th>Skenario</th><th class="num">Penjualan bruto</th><th class="num">Margin kotor</th><th class="num">Opex</th><th class="num">Laba (rugi) bersih</th></tr></thead><tbody>{scen_rows}</tbody></table></div>
<div class="grid g2" style="margin-top:14px">{recs_html}</div>
<div class="card" style="margin-top:14px"><h3>Pembanding: Body Repair DCA (Suzuki), September 2026</h3><div class="sub">Dari tinjauan Body &amp; Paint DCA, Juli–September 2026 · Rp juta</div>
 <table><thead><tr><th>Ukuran</th><th class="num">DCM Body Paint</th><th class="num">DCA Body Repair</th><th>Bacaan</th></tr></thead><tbody>
 <tr><td>Penjualan bruto September</td><td class="num">{rp(S['sales'])}</td><td class="num">{rp(dca_cmp['sales'])}</td><td>DCM {p0(S['sales']/dca_cmp['sales']-1)} lebih besar dan tumbuh; DCA datar.</td></tr>
 <tr><td>Margin kotor gabungan</td><td class="num">{p1(S['gm'])}</td><td class="num">{p1(dca_cmp['gm'])}</td><td>Diskon DCM lebih rendah ({p1(S['disc_rate'])} vs 11,1%).</td></tr>
 <tr><td>Penyusutan per bulan</td><td class="num">{rp(S['dep'])}</td><td class="num">{rp(dca_cmp['dep'])}</td><td>Basis aset DCM {idn(S['fa_cost']/1.3445e9,1)} kali DCA; peralatan DCA habis Desember 2026, DCM {equip_end}.</td></tr>
 <tr><td>EBITDA September</td><td class="num">{rp(S['ebitda'])}</td><td class="num">{rp(dca_cmp['ebitda'])}</td><td>Keduanya positif secara kas.</td></tr>
 <tr><td>Laba (rugi) bersih September</td><td class="num">{rp(S['net'])}</td><td class="num">{rp(dca_cmp['net'])}</td><td>Rugi DCM {idn(S['net']/dca_cmp['net'],1)} kali DCA, seluruhnya karena penyusutan.</td></tr>
 </tbody></table></div>
<div class="card" style="margin-top:14px"><h3>Yang perlu dipantau setiap bulan mulai Oktober</h3><div class="sub">Kartu skor unit satu halaman, agar tinjauan berikutnya dapat menyatakan apakah rencana ini berjalan</div>
 <div class="grid g4">
  <div><b>Volume</b><div class="note">Unit masuk dan keluar · penjualan bruto per sumber (target jasa ≥ Rp {rp(S['sales_jasa'],0)} juta) · rujukan dari serah terima unit dan bengkel umum · bauran asuransi vs pribadi</div></div>
  <div><b>Margin</b><div class="note">Margin kotor per sumber (jasa ≥ {p0(S['gm_jasa'])}, suku cadang ≥ {p0(A['gm_parts'])}) · tingkat diskon ≤ 7% · bagi hasil pihak ketiga per tingkatan · insentif sebagai % laba kotor</div></div>
  <div><b>Biaya</b><div class="note">Opex tunai ≤ Rp {rp(cash_opex_h1,0)} juta · jam booth dan oven per minggu · kWh listrik per unit keluar · pos di atas Rp 5 juta dengan persetujuan</div></div>
  <div><b>Neraca</b><div class="note">Umur piutang asuransi (tidak ada di atas 60 hari) · GR/IR dicocokkan tiap bulan · persediaan suku cadang tidak negatif · saldo HO sama di kedua pembukuan · kas ≤ 1 bulan opex tunai</div></div>
 </div></div>

<footer>Ruang lingkup dan dasar. Tinjauan ini mencakup Laporan Neraca dan Laba Rugi PT DCM Body Paint (sistem ACCURATE) untuk Juli, Agustus dan September 2026, dengan seluruh bulan sejak dibuka (September 2025) dipakai untuk tren, angka tahun berjalan dan akumulasi rugi. Angka diekstraksi dengan skrip dari lapisan teks laporan dan direkonsiliasi: rincian akun terhadap subtotal laba rugi, neraca sampai ke rupiah, mutasi akumulasi penyusutan terhadap beban penyusutan, dan ekuitas terhadap laba rugi bulanan. Angka dealer utama (penjualan, piutang kepada unit, rekening pembukuan pusat, deposito) diambil dari Laporan Neraca dan Rugi Laba Inhouse PT DCM untuk bulan yang sama. Pembanding DCA diambil dari tinjauan Body &amp; Paint DCA Juli–September 2026. Dokumen ini adalah tinjauan analitis atas laporan manajemen, bukan audit, dan tidak memberikan opini asurans. Skenario adalah ilustrasi aritmetika pada asumsi yang dinyatakan, bukan proyeksi. Tidak ada data operasional (jumlah unit, jam kerja, utilisasi booth) dalam laporan; angka-angka tersebut akan mempertajam tinjauan berikutnya.</footer>
</div></body></html>
"""

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
out = os.path.join(HERE, 'out', 'report.html')
open(out, 'w', encoding='utf-8').write(HTML)
json.dump({'sep': S, 'aug': A, 'jul': J, 'ytd_2026': YTD, 'since_opening': INC,
           'depreciation': {'bldg_rate': bldg_rate, 'equip_rate': equip_rate, 'office_rate': office_rate, 'equip_months_left': equip_months_left, 'equip_end': equip_end,
                            'bldg_months_left': bldg_months_left, 'dep_equip_8y': dep_equip_8y, 'dep_saving_8y': dep_saving_8y, 'by_year': DEP_YEARS},
           'scenarios': [(c, n, g, gm, ox, net) for c, n, g, gm, ox, net, _ in SCEN_RES],
           'break_even': {'now_gross': be_gross_now, 'cash_gross': cash_be_gross, 'life8y_gross': be_gross_8y},
           'intercompany': {'hutang_ho_unit': S['hutang_ho'], 'piutang_bp_at_ho': ho_recv_bp, 'gap': ic_gap, 'clearing_unit': S['ho_clearing'], 'clearing_ho': G['sep']['pembukuan_pusat_cabang_bp'], 'clearing_gap': clearing_gap},
           'recon_exceptions': RECON},
          open(os.path.join(HERE, 'out', 'metrics.json'), 'w'), indent=1, default=str)
print('wrote', out, len(HTML), 'bytes')
print(f"Sep net {rp(S['net'])} | opex {rp(S['opex'])} | dep {rp(S['dep'])} | EBITDA {rp(S['ebitda'])} | BE now {rp(be_gross_now)} | BE 8y {rp(be_gross_8y)} | cash BE {rp(cash_be_gross)} | equip end {equip_end} | ic gap {rp(ic_gap)} | clearing gap {rp(clearing_gap)}")
for r in SCEN_RES:
    print(r[0], r[1], rp(r[5]))
