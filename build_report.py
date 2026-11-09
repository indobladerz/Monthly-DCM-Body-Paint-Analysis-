#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Menyusun tinjauan keuangan tiga bulan Body & Paint PT Duta Cendana Mobilindo (PT DCM Body Paint).

  python3 build_report.py [--month YYYY-MM]

Tanpa --month dipakai bulan terbaru di data/<yyyy-mm>.json (hasil parse_dcm.py dari laporan Neraca & Laba Rugi
bulanan ACCURATE). Tiga bulan terakhir sampai bulan itu menjadi jendela analisis. Angka dealer utama
(data/raw/group_inhouse.json) bersifat opsional: bila bulan itu tidak ada di berkas tersebut, bagian antar perusahaan
dan rujukan dealer dihilangkan dan laporan menyatakannya. Asumsi skenario dan ambang ada di config/targets.json.
Setiap angka dalam laporan dihitung di sini dari berkas data/config tersebut; tidak ada yang diketik manual, dan temuan
yang tidak dapat dihitung untuk bulan terpilih dihilangkan. Laporan dalam Bahasa Indonesia, format angka Indonesia
(titik ribuan, koma desimal).
"""
import json, os, base64, html, math, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
CFG = json.load(open(os.path.join(HERE, 'config', 'targets.json'), encoding='utf-8'))
SC_CFG, POL, AN = CFG['scenario'], CFG['policy'], CFG['analysis']

ID_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
ID_MONL = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
EN_MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']   # kunci metrics.json
def month_add(y, mo, k):
    mo += k
    y += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    return y, mo
def ym(m): return int(m[:4]), int(m[5:])
def mshift(m, k):
    y, mo = month_add(*ym(m), k)
    return f'{y}-{mo:02d}'
def mname(m): return ID_MONL[ym(m)[1] - 1]
def mlabel(m): return f'{mname(m)} {m[:4]}'

AVAIL = sorted(f[:-5] for f in os.listdir(DATA) if re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])\.json', f))
if not AVAIL:
    sys.exit('Tidak ada data/<yyyy-mm>.json; jalankan parse_dcm.py dahulu.')
CHOSEN = AVAIL[-1]
if '--month' in sys.argv:
    CHOSEN = sys.argv[sys.argv.index('--month') + 1]
    if CHOSEN not in AVAIL:
        sys.exit(f'Bulan {CHOSEN} tidak ada di data/. Tersedia: {AVAIL[0]} .. {AVAIL[-1]}')
ALL = [m for m in AVAIL if m <= CHOSEN]
MONTHS = ALL[-3:]
if len(MONTHS) < 3 or MONTHS[1] != mshift(MONTHS[0], 1) or MONTHS[2] != mshift(MONTHS[1], 1):
    sys.exit(f'Tiga bulan berurutan sampai {CHOSEN} diperlukan; ada {MONTHS}.')
PRE = mshift(MONTHS[0], -1) if mshift(MONTHS[0], -1) in ALL else None       # bulan tepat sebelum jendela, bila ada
YR = [m for m in ALL if m[:4] == CHOSEN[:4]]
YEAR = int(CHOSEN[:4])
MLABEL = {m: mlabel(m) for m in ALL}
MSHORT = {m: ID_MON[ym(m)[1] - 1] + ('' if m[:4] == CHOSEN[:4] else ' ' + m[2:4]) for m in ALL}
MS, MA, MJ = MONTHS[2], MONTHS[1], MONTHS[0]
NS, NA, NJ = mname(MS), mname(MA), mname(MJ)                            # nama bulan terpilih, sebelumnya, dan awal jendela
SHS, SHA, SHJ = (ID_MON[ym(m)[1] - 1] for m in (MS, MA, MJ))
if MJ[:4] == MS[:4]:
    QLABEL = f'{NJ} – {NS} {MS[:4]}'
else:
    QLABEL = f'{mlabel(MJ)} – {mlabel(MS)}'
D = {m: json.load(open(os.path.join(DATA, f'{m}.json'), encoding='utf-8')) for m in ALL}
RECON = [x for x in json.load(open(os.path.join(DATA, 'recon_exceptions.json'), encoding='utf-8')) if x['month'] <= CHOSEN]

# data dealer utama (opsional): kunci 'YYYY-MM' atau kunci lama jul/aug/sep = 2026
GRAW = json.load(open(os.path.join(DATA, 'raw', 'group_inhouse.json'), encoding='utf-8'))
LEGACY_G = {'jul': '2026-07', 'aug': '2026-08', 'sep': '2026-09'}
GROUP = {}
for k, v in GRAW.items():
    if k.startswith('_'): continue
    GROUP[LEGACY_G.get(k, k)] = v
G = GROUP.get(MS)                      # None bila laporan dealer bulan ini tidak tersedia
GJ = GROUP.get(MJ)
TODAY = datetime.date.today()
today = f'{TODAY.day} {ID_MONL[TODAY.month - 1]} {TODAY.year}'

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


S, A, J = M[MS], M[MA], M[MJ]
def tot(key, months): return sum(M[m][key] for m in months)
def bsv(m, k):
    """Saldo neraca, None bila akun tidak ada pada bulan itu (temuan terkait dihilangkan)."""
    return D[m]['bs'].get(k)
def ac(a, b):
    c = chg(a, b)
    return None if c is None else abs(c)
def arah(x, naik='naik', turun='turun'): return naik if x >= 0 else turun
YTD = {k: tot(k, YR) for k in ['sales', 'sales_jasa', 'sales_parts', 'disc', 'net_sales', 'cogs', 'gp', 'selling', 'ga', 'opex', 'dep', 'net', 'ebitda', 'cash_opex', 'insentif', 'gaji']}
INC = {k: tot(k, ALL) for k in ['sales', 'net_sales', 'gp', 'opex', 'dep', 'net', 'ebitda']}       # sejak laporan pertama
BASE_M = [m for m in YR if m < MJ]                                  # bulan tahun berjalan sebelum jendela (pembanding), bila ada
BASE = {k: tot(k, BASE_M) / len(BASE_M) for k in ['sales', 'net', 'cash_opex', 'ebitda', 'net_sales', 'gp']} if BASE_M else None
BASE_LABEL = f'{mname(BASE_M[0])}–{mname(BASE_M[-1])}' if BASE_M else None
Q3 = {k: tot(k, MONTHS) for k in ['sales', 'net', 'opex', 'dep', 'ebitda', 'cash_opex', 'net_sales', 'gp', 'disc', 'selling', 'ga']}
ytd_gap = (bs(MS, 'Laba tahun ini') - YTD['net']) if (YR[0] == f'{YEAR}-01' and 'Laba tahun ini' in D[MS]['bs']) else None   # None bila tahun berjalan tidak lengkap di data
dep_gap_total = sum(x['gap'] for x in RECON if x['test'].startswith('akumulasi'))
inc_gap = S['equity'] - INC['net']           # selisih ekuitas vs jumlah laba rugi bulanan sejak laporan pertama
inc_unexplained = inc_gap - dep_gap_total    # sisa yang tidak dijelaskan oleh pengecualian penyusutan yang tercatat
INC['net_sum_pl'] = INC['net']; INC['net'] = S['equity']   # angka resmi sejak dibuka = ekuitas (rugi ditahan tahun lalu + laba tahun berjalan)

# ------------------------------------------------------------------ aset tetap & penyusutan
assert S['gm'] > 0 and S['disc_rate'] < 1 and S['sales'] > 0 and S['dep'] > 0, \
    'margin kotor <= 0, tanpa penjualan atau tanpa penyusutan: titik impas tidak terdefinisi; periksa data bulan ini'
bldg_rate = S['dep_bldg'] * 12 / S['fa_bldg_cost']; bldg_life_y = 1 / bldg_rate
equip_rate = S['dep_equip'] * 12 / S['fa_equip_cost']; equip_life_y = 1 / equip_rate
office_rate = S['dep_office'] * 12 / S['fa_office_cost']
bldg_pct = S['acc_bldg'] / S['fa_bldg_cost']; equip_pct = S['acc_equip'] / S['fa_equip_cost']; office_pct = S['acc_office'] / S['fa_office_cost']
bldg_months_left = S['nbv_bldg'] / S['dep_bldg']; equip_months_left = S['nbv_equip'] / S['dep_equip']; office_months_left = S['nbv_office'] / S['dep_office']
equip_share_dep = S['dep_equip'] / S['dep']
ALT_YEARS = SC_CFG['equipment_life_alt_years']
dep_equip_8y = S['fa_equip_cost'] / (ALT_YEARS * 12.0)         # bila umur ekonomis oven/booth = equipment_life_alt_years
dep_saving_8y = S['dep_equip'] - dep_equip_8y
ALT_OK = dep_saving_8y > 0                                      # tinjauan umur hanya bermakna bila umur saat ini lebih pendek
asset_turnover = S['sales'] * 12 / S['fa_cost']
bldg_add = S['fa_bldg_cost'] - A['fa_bldg_cost']
dep_land_bldg = S['dep_bldg']; dep_equipment = S['dep_equip'] + S['dep_office']
land_in_unit = any('tanah' in k.lower() for k in D[MS]['bs'])
HO_LAND = G.get('tanah') if G else None; HO_INV_LAND_BLDG = G.get('investasi_tanah_bangunan') if G else None

ey, em = month_add(YEAR, ym(MS)[1], math.ceil(equip_months_left)); equip_end = f'{ID_MONL[em-1]} {ey}'
by, bm = month_add(YEAR, ym(MS)[1], math.ceil(bldg_months_left)); bldg_end = f'{by}'

# proyeksi beban penyusutan per tahun pada kebijakan saat ini (berdasarkan tarif bulan terpilih, tanpa penambahan aset)
Y0 = int(ALL[0][:4])
def dep_by_year():
    out = {}
    eq_nbv, of_nbv = S['nbv_equip'], S['nbv_office']
    for y in range(Y0, YEAR + 5):
        if y < YEAR:
            ms_ = [m for m in ALL if m[:4] == str(y)]
            out[y] = [sum(M[m]['dep_equip'] for m in ms_), sum(M[m]['dep_bldg'] for m in ms_), sum(M[m]['dep_office'] for m in ms_)]
            continue
        eq = bl = of = 0.0
        start = 1
        if y == YEAR:
            eq, bl, of = YTD['dep'] - sum(M[m]['dep_bldg'] + M[m]['dep_office'] for m in YR), sum(M[m]['dep_bldg'] for m in YR), sum(M[m]['dep_office'] for m in YR)
            start = ym(MS)[1] + 1
        for mo in range(start, 13):
            e = min(S['dep_equip'], max(eq_nbv, 0)); eq_nbv -= e; eq += e
            o = min(S['dep_office'], max(of_nbv, 0)); of_nbv -= o; of += o
            bl += S['dep_bldg']
        out[y] = [eq, bl, of]
    return out
DEP_YEARS = dep_by_year()

# ------------------------------------------------------------------ titik impas & skenario (bulanan, Rupiah)
gm_now, gm_prev = S['gm'], A['gm']
be_net_now = S['opex'] / gm_now
be_gross_now = be_net_now / (1 - S['disc_rate'])
cash_be_gross = (S['cash_opex'] / gm_now) / (1 - S['disc_rate'])
opex_8y = S['opex'] - dep_saving_8y
be_gross_8y = (opex_8y / gm_now) / (1 - S['disc_rate'])
cash_opex_base = BASE['cash_opex'] if BASE else None

def scenario(gross, gm, opex):
    return gross * (1 - S['disc_rate']) * gm - opex + S['other']

UP = SC_CFG['volume_uplift']; CU = SC_CFG['cash_opex_uplift']; TGT = float(SC_CFG['target_gross_monthly'])
TGT_OK = TGT > S['sales']
SCEN = [('now', f'{MLABEL[MS]} sesuai laporan', S['sales'], gm_now, S['opex'], 'Aktual'),
        ('prevgm', f'Volume sama, margin kotor kembali ke level {NA}', S['sales'], gm_prev, S['opex'], f'Margin kotor {p1(gm_prev)} alih-alih {p1(gm_now)}'),
        ('vol', f'Volume +{idn(UP*100,0)}%{" dari rujukan dealer" if G else ""}, margin & opex {NS}', S['sales'] * (1 + UP), gm_now, S['opex'], f'Penjualan bruto Rp {rp(S["sales"]*(1+UP),0)} juta')]
if TGT_OK:
    SCEN.append(('target', f'Target Rp {idn(TGT/1e6,0)} juta/bulan, margin {NA}, opex tunai +{idn(CU*100,0)}%', TGT, gm_prev, S['opex'] + S['cash_opex'] * CU, f'Volume +{idn((TGT/S["sales"]-1)*100,0)}% vs {SHS}'))
    if ALT_OK:
        SCEN.append(('target8', f'Skenario target + umur oven/booth {ALT_YEARS} tahun', TGT, gm_prev, S['opex'] + S['cash_opex'] * CU - dep_saving_8y, f'Penyusutan peralatan turun Rp {rp(dep_saving_8y)} juta'))
SCODE = {s[0]: chr(65 + i) for i, s in enumerate(SCEN)}
SCEN_RES = [(SCODE[k], n, g, gm, ox, scenario(g, gm, ox), note) for k, n, g, gm, ox, note in SCEN]
SCEN_NET = {k: scenario(g, gm, ox) for k, n, g, gm, ox, note in SCEN}
if TGT_OK:   # kode skenario target dalam nama
    SCEN_RES = [(c, n.replace('Skenario target', f'Skenario {SCODE["target"]}'), g, gm, ox, net, note) for c, n, g, gm, ox, net, note in SCEN_RES]

# ------------------------------------------------------------------ buku besar akun per akun
ACCTS = []
for m in sorted(set(YR) | set(MONTHS)):
    for a in D[m]['ga_accounts']:
        if a not in ACCTS: ACCTS.append(a)
SELL_ACCTS = []
for m in sorted(set(YR) | set(MONTHS)):
    for a in D[m]['selling_accounts']:
        if a not in SELL_ACCTS: SELL_ACCTS.append(a)
ledger = []
for a in ACCTS:
    vals = [ga(m, a) for m in MONTHS]; ytd = sum(ga(m, a) for m in YR)
    if any(vals) or ytd:
        ledger.append({'acct': a, 'type': 'Umum & Adm', 'v': vals, 'ytd': ytd})
for a in SELL_ACCTS:
    vals = [sell(m, a) for m in MONTHS]; ytd = sum(sell(m, a) for m in YR)
    if any(vals) or ytd:
        ledger.append({'acct': a, 'type': 'Penjualan', 'v': vals, 'ytd': ytd})
for r in ledger:
    r['q3'] = sum(r['v']); r['share_sep'] = r['v'][2] / S['opex']; r['share_q3'] = r['q3'] / Q3['opex']
    r['mom'] = chg(r['v'][1], r['v'][2]); r['q'] = chg(r['v'][0], r['v'][2])
ledger.sort(key=lambda r: (-r['v'][2], -r['q3']))
assert abs(sum(r['v'][2] for r in ledger) - S['opex']) < 1, 'buku besar bulan terpilih tidak cocok dengan opex'
assert abs(sum(r['v'][1] for r in ledger) - A['opex']) < 1, 'buku besar bulan sebelumnya tidak cocok dengan opex'
assert abs(sum(r['q3'] for r in ledger) - Q3['opex']) < 1, 'buku besar tiga bulan tidak cocok dengan opex'
assert abs(sum(r['ytd'] for r in ledger) - YTD['opex']) < 1, 'buku besar tahun berjalan tidak cocok dengan opex'

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
    'Biaya Pemeliharaan Peralatan Kantor Matrial': 'Pemeliharaan peralatan',
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
    for i in range(3):
        cat_tot[cat(r['acct'])][i] += r['v'][i]

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
    """Pendapatan neto (batang) dengan laba bersih dan EBITDA (garis), bulan-bulan tahun berjalan."""
    padl, padr, padt, padb = 48, 16, 18, 34
    cats = YR
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
    yrs = sorted(DEP_YEARS)
    labels = [f'{y}*' if (y == yrs[0] and y < YEAR) else str(y) for y in yrs]
    eq = [DEP_YEARS[y][0] for y in yrs]; bl = [DEP_YEARS[y][1] for y in yrs]; of = [DEP_YEARS[y][2] for y in yrs]
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
def sdiv(a, b): return a / b if b else None
ho_recv_bp = G['piutang_dcm_body_paint'] if G else None
ic_gap = ho_recv_bp - S['hutang_ho'] if G else None
clearing_gap = S['ho_clearing'] - G['pembukuan_pusat_cabang_bp'] if G else None
ho_funding = S['ho_clearing'] + S['hutang_ho']
grir_months_cogs = sdiv(S['grir'], S['cogs'])
CASH_BASE = PRE or MJ; CASH_BASE_NAME = mname(CASH_BASE)
cash_q3_change = S['cash'] - M[CASH_BASE]['cash']; hutang_ho_q3_change = S['hutang_ho'] - M[CASH_BASE]['hutang_ho']
clearing_q3_change = S['ho_clearing'] - M[CASH_BASE]['ho_clearing']
idle_cash_income = S['cash'] * SC_CFG['idle_cash_rate_pa'] / 12
bank_interest = D[MS]['other_income_accounts'].get('Pendapatan Bunga Bank', 0.0)
ins_rate = {m: sdiv(M[m]['insentif'], M[m]['sales']) for m in MONTHS}
disc_svc_rate = {m: sdiv(M[m]['disc_jasa'], M[m]['sales_jasa']) for m in MONTHS}
disc_parts_rate = {m: sdiv(M[m]['disc_parts'], M[m]['sales_parts']) for m in MONTHS}
best_net_month = max(YR, key=lambda m: M[m]['net'])
group_sales = G['sales_gross'] if G else None
bp_share = S['sales'] / (group_sales + S['sales']) if G else None
aftersales_ho = (G['sales_sparepart'] + G['sales_service']) if G else None
TP_T = POL['third_party_share_target']
tp_to_40 = (S['tp_share'] - TP_T) * S['net_jasa']
ins_to_8pct = S['insentif'] - POL['incentive_cap_of_gross_sales'] * S['sales']
parts_to_prev = (A['gm_parts'] - S['gm_parts']) * S['net_parts']
disc_to_cap = (S['disc_rate'] - POL['discount_cap_of_gross_sales']) * S['sales']
vol_step = POL['volume_step'] * (1 - S['disc_rate']) * gm_now
EQ_FROM = AN['equity_test_from']; TOL_IC = AN['intercompany_tolerance_rp']

# perubahan harga perolehan aset tetap dalam jendela
FA_CLASSES = [('fa_bldg_cost', 'Bangunan', 'dep_bldg'), ('fa_office_cost', 'Peralatan Kantor', 'dep_office'), ('fa_equip_cost', 'Peralatan Bengkel', 'dep_equip')]
FA_EVENTS = []      # (bulan, jenis, jumlah, teks, kelas terdampak)
_chain = ([PRE] if PRE else []) + MONTHS
for p_, c_ in zip(_chain, _chain[1:]):
    dl = {nm: M[c_][k] - M[p_][k] for k, nm, _ in FA_CLASSES}
    nz = {nm: d for nm, d in dl.items() if abs(d) >= 1}
    if not nz: continue
    if len(nz) >= 2 and abs(sum(dl.values())) < 1:
        src = min(nz, key=nz.get); dst = max(nz, key=nz.get)
        FA_EVENTS.append((c_, 'pindah', nz[dst], f'{mname(c_)}: Rp {rp(nz[dst])} juta dipindahkan dari {src} ke {dst}', [src, dst]))
    else:
        for nm, d in nz.items():
            FA_EVENTS.append((c_, 'tambah' if d > 0 else 'kurang', abs(d), f'{mname(c_)}: {nm} {"bertambah" if d > 0 else "berkurang"} Rp {rp(abs(d))} juta', [nm]))
FA_SIZE = sum(e[2] for e in FA_EVENTS)
equip_add_window = sum(abs(M[c_][k] - M[p_][k]) for p_, c_ in zip(_chain, _chain[1:]) for k in ('fa_equip_cost', 'fa_office_cost'))

# ------------------------------------------------------------------ uji integritas
INTEG = []   # (nama, lolos, catatan, ukuran selisih Rp)
def T(name, ok, note, gap=0.0): INTEG.append((name, ok, note, gap))

bad_bs = [m for m in ALL if abs(D[m]['bs']['Jumlah Aktiva'] - D[m]['bs']['Jumlah Kewajiban dan Ekuitas']) >= 1]
T('Neraca seimbang (Aktiva = Kewajiban + Ekuitas)', not bad_bs,
  f'Seluruh {len(ALL)} bulan ({MSHORT[ALL[0]]}–{MSHORT[ALL[-1]]}) cocok sampai ke rupiah.' if not bad_bs else 'Tidak cocok: ' + ', '.join(MLABEL[m] for m in bad_bs))

eq_gaps = {}
for m in MONTHS:
    pm = mshift(m, -1)
    if m >= EQ_FROM and pm in D:
        eq_gaps[m] = D[m]['bs']['Jumlah Ekuitas'] - (D[pm]['bs']['Jumlah Ekuitas'] + M[m]['net'])
eq_bad = {m: g_ for m, g_ in eq_gaps.items() if abs(g_) >= 10}
if eq_gaps:
    def sg(v): return ('+' if v > 0 else '-') + f'Rp {idn(abs(v), 0)}'
    note = ''
    if eq_bad:
        note = ' dan '.join(f'{mname(m)} {sg(v)}' for m, v in eq_bad.items()) + ' di luar laba rugi'
        vals_ = list(eq_bad.values())
        if len(vals_) >= 2 and abs(sum(vals_)) < 0.01 * max(abs(v) for v in vals_):
            note += ' (saling membalik, tanpa jurnal penjelas)'
        okm = [mname(m) for m in eq_gaps if m not in eq_bad]
        if okm: note += '. ' + ', '.join(okm) + ' cocok.'
    else:
        note = ', '.join(mname(m) for m in eq_gaps) + ' cocok: laba rugi bulanan menjelaskan seluruh perubahan ekuitas.'
    T('Mutasi ekuitas (ekuitas awal + laba rugi bulan = ekuitas akhir)', not eq_bad, note, max([abs(v) for v in eq_bad.values()] or [0.0]))

leaf_bad = []
for m in MONTHS:
    P_ = D[m]['pl']
    for lab, leaves, tot_ in (('beban penjualan', D[m]['selling_accounts'], P_['selling']), ('umum & administrasi', D[m]['ga_accounts'], P_['ga'])):
        if abs(sum(leaves.values()) - tot_) >= 1: leaf_bad.append(f'{mname(m)} {lab}')
T('Akun rincian berjumlah sama dengan subtotal laba rugi', not leaf_bad,
  f'Penjualan, diskon, harga pokok, beban penjualan Rp {rp(S["selling"])} juta dan umum &amp; administrasi Rp {rp(S["ga"])} juta terbentuk kembali dari rincian akun pada setiap bulan.' if not leaf_bad else 'Tidak cocok: ' + ', '.join(leaf_bad))

dep_gaps = {}
for m in MONTHS:
    pm = mshift(m, -1)
    if pm in D:
        dep_gaps[m] = M[m]['dep'] - (D[pm]['bs']['AKUMULASI PENYUSUTAN'] - D[m]['bs']['AKUMULASI PENYUSUTAN'])
dep_bad = {m: g_ for m, g_ in dep_gaps.items() if abs(g_) >= 2}
hist = [x for x in RECON if x['test'].startswith('akumulasi') and x['month'] not in dep_bad]
hist_txt = (' Pengecualian historis: ' + '; '.join(f'{MLABEL[x["month"]]} selisih Rp {rp(abs(x["gap"]))} juta' for x in hist) + '.') if hist else ''
if dep_gaps:
    T('Mutasi akumulasi penyusutan = beban penyusutan yang dibukukan', not dep_bad,
      (', '.join(mname(m) for m in dep_gaps) + f' cocok (Rp {rp(S["dep"])} juta per bulan pada {NS}).' + hist_txt) if not dep_bad else
      '; '.join(f'{mname(m)}: beban Rp {rp(M[m]["dep"])} juta vs mutasi akumulasi Rp {rp(M[m]["dep"] - g_)} juta (selisih Rp {rp(abs(g_))} juta)' for m, g_ in dep_bad.items()) + '.' + hist_txt,
      max([abs(v) for v in dep_bad.values()] or [0.0]))

TOLR = AN['rate_spread_tolerance']
rate_bad = []
for k, nm, dk in FA_CLASSES:
    rs = [M[m][dk] * 12 / M[m][k] for m in MONTHS if M[m][k]]
    if rs and max(rs) - min(rs) > TOLR: rate_bad.append(nm)
T('Tarif penyusutan konsisten per kelompok aset', not rate_bad,
  f'Gedung {p1(bldg_rate)} per tahun, peralatan bengkel {p1(equip_rate)}, peralatan kantor {p1(office_rate)}' + ('; beban mengikuti perubahan harga perolehan (' + ', '.join(e[3] for e in FA_EVENTS) + ').' if FA_EVENTS else '.')
  if not rate_bad else 'Tarif berubah dalam jendela untuk: ' + ', '.join(rate_bad))

if G:
    T('Saldo antar perusahaan cocok dengan dealer utama', abs(ic_gap) < TOL_IC and abs(clearing_gap) < TOL_IC,
      f'Hutang HO Rp {rp(S["hutang_ho"])} juta vs Piutang PT DCM Body Paint Rp {rp(ho_recv_bp)} juta (selisih Rp {rp(ic_gap)} juta); pembukuan pusat selisih Rp {rp(clearing_gap)} juta.',
      max(abs(ic_gap), abs(clearing_gap)))

grir_growing = S['grir'] > J['grir'] + 1
inv_neg = S['inv_parts'] < 0
T('Akun kliring bersaldo wajar dan persediaan tidak negatif', not (grir_growing or inv_neg),
  f'GR/IR Rp {rp(S["grir"])} juta ({idn(grir_months_cogs) if grir_months_cogs is not None else "t/b"} bulan harga pokok), {"naik" if S["grir"] > J["grir"] else "turun"} dari Rp {rp(J["grir"])} juta di {NJ}; persediaan suku cadang Rp {rp(S["inv_parts"]) if S["inv_parts"] >= 0 else "(" + rp(-S["inv_parts"]) + ")"} juta.',
  max(S['grir'] if grir_growing else 0.0, -S['inv_parts'] if inv_neg else 0.0))

if ytd_gap is not None:
    T('Laba tahun berjalan di neraca = jumlah laba rugi bulanan tahun ini', abs(ytd_gap) < 10,
      f'Laba tahun ini di neraca Rp {rp(bs(MS, "Laba tahun ini"))} juta; jumlah laba rugi {mname(YR[0])}–{NS} Rp {rp(YTD["net"])} juta' + ('.' if abs(ytd_gap) < 10 else f'; selisih Rp {idn(abs(ytd_gap), 0)}.'),
      abs(ytd_gap) if abs(ytd_gap) >= 10 else 0.0)
T('Ekuitas sejak laporan pertama = jumlah laba rugi bulanan + pengecualian penyusutan tercatat', abs(inc_unexplained) < 100,
  f'Ekuitas Rp {rp(S["equity"])} juta; jumlah laba rugi bulanan Rp {rp(INC["net_sum_pl"])} juta; selisih Rp {rp(inc_gap)} juta, dari pengecualian penyusutan tercatat Rp {rp(dep_gap_total)} juta' + ('.' if abs(inc_unexplained) < 100 else f', sisa tidak terjelaskan Rp {rp(inc_unexplained)} juta.'),
  abs(inc_unexplained) if abs(inc_unexplained) >= 100 else 0.0)

# ------------------------------------------------------------------ temuan (dihitung dari data; diperingkat menurut ukuran Rp)
FINDINGS = []
def F(size, area, title, body, evidence):
    FINDINGS.append(dict(size=abs(size), area=area, title=title, body=body, evidence=evidence))
def sev_of(size):
    ratio = size / S['net_sales'] if S['net_sales'] > 0 else 0
    return 'TINGGI' if ratio >= AN['severity_high_pct_of_net_sales'] else ('SEDANG' if ratio >= AN['severity_medium_pct_of_net_sales'] else 'RENDAH')
def hasil(v): return 'rugi' if v < 0 else 'laba'
def jt(v): return f'Rp {rp(abs(v))} juta'
def neg_p(x, f=rp): return f'({f(-x)})' if x < 0 else f(x)

# 1. hasil bersih
nets = [M[m]['net'] for m in MONTHS]
if all(n < 0 for n in nets): t1 = 'Rugi di ketiga bulan: ' + ', '.join(f'{jt(M[m]["net"])} di {mname(m)}' for m in MONTHS)
elif all(n >= 0 for n in nets): t1 = 'Laba di ketiga bulan: ' + ', '.join(f'{jt(M[m]["net"])} di {mname(m)}' for m in MONTHS)
else: t1 = 'Hasil bersih berganti arah: ' + ', '.join(f'{mname(m)} {hasil(M[m]["net"])} {jt(M[m]["net"])}' for m in MONTHS)
b1 = [f'{QLABEL}: {hasil(Q3["net"])} bersih {jt(Q3["net"])} atas penjualan bruto Rp {rp(Q3["sales"])} juta.']
b1.append(f'Sejak {"awal tahun" if YR[0] == f"{YEAR}-01" else MLABEL[YR[0]]}, {hasil(YTD["net"])} bersih {jt(YTD["net"])}.')
_mod = (bsv(MS, 'MODAL') - bsv(MS, 'LABA DITAHAN')) if (bsv(MS, 'MODAL') is not None and bsv(MS, 'LABA DITAHAN') is not None) else None
b1.append(f'Ekuitas unit {"negatif Rp " + rpbn(-S["equity"]) if S["equity"] < 0 else "Rp " + rpbn(S["equity"])} miliar pada {NS} (laporan pertama: {MLABEL[ALL[0]]}){", tanpa modal disetor" if _mod is not None and abs(_mod) < 1 else ""}.')
_rank = sum(1 for m in YR if M[m]['net'] > S['net'] + 1)
if len(YR) >= 3:
    b1.append(f'{NS} adalah bulan dengan hasil terbaik' + (' tahun ini' if _rank == 0 else f' ke-{_rank + 1} dari {len(YR)} bulan tahun ini (terbaik: {mname(best_net_month)}, {hasil(M[best_net_month]["net"])} Rp {rp(abs(M[best_net_month]["net"]))} juta)') + '.')
if S['sales_jasa'] >= max(M[m]['sales_jasa'] for m in ALL) and len(ALL) > 1:
    b1.append(f'Pendapatan jasa {NS} Rp {rp(S["sales_jasa"])} juta adalah yang tertinggi sejak laporan pertama.')
F(S['net'], 'Profitabilitas', t1, ' '.join(b1), f'Laba Rugi PT DCM Body Paint, {MLABEL[ALL[0]]} – {MLABEL[MS]}; Neraca {MLABEL[MS]}, Ekuitas.')

# 2. penyusutan
b2 = [f'Rp {rp(S["dep"])} juta dari opex {NS} Rp {rp(S["opex"])} juta adalah penyusutan: peralatan bengkel Rp {rp(S["dep_equip"])} juta, gedung Rp {rp(S["dep_bldg"])} juta, peralatan kantor Rp {rp(S["dep_office"])} juta.']
if S['ebitda'] >= 0:
    b2.append(f'Di luar penyusutan, unit menutup biaya tunainya: EBITDA {NS} Rp {rp(S["ebitda"])} juta ({NJ} Rp {rp(J["ebitda"])} juta, {NA} Rp {rp(A["ebitda"])} juta).')
else:
    b2.append(f'EBITDA {NS} negatif Rp ({rp(-S["ebitda"])}) juta: biaya tunai pun belum tertutup ({NJ} Rp {rp(J["ebitda"])} juta, {NA} Rp {rp(A["ebitda"])} juta).')
_be = (be_gross_now / S['sales'] - 1) * 100
b2.append(f'Titik impas penuh memerlukan penjualan bruto Rp {rp(be_gross_now,0)} juta per bulan, {idn(abs(_be),0)}% {"di atas" if _be >= 0 else "di bawah"} {NS}.')
F(S['dep'], 'Struktur biaya', f'Penyusutan mencapai {p0(S["dep"]/S["opex"])} dari beban operasional dan {p0(S["dep"]/S["net_sales"])} dari pendapatan neto', ' '.join(b2),
  'Buku besar Beban Umum dan Administrasi; Neraca, Aktiva Tetap dan Akumulasi Penyusutan.')

# 3. basis aset dan umur ekonomis
b3 = [f'Peralatan bengkel Rp {rpbn(S["fa_equip_cost"])} miliar dibebankan {p0(equip_rate)} per tahun (umur {idn(equip_life_y,0)} tahun), gedung Rp {rpbn(S["fa_bldg_cost"])} miliar {p0(bldg_rate)} per tahun (umur {idn(bldg_life_y,0)} tahun).']
if ALT_OK:
    b3.append(f'Bila umur ekonomis oven dan booth {ALT_YEARS} tahun, beban peralatan turun dari Rp {rp(S["dep_equip"])} juta menjadi Rp {rp(dep_equip_8y)} juta per bulan dan titik impas turun ke Rp {rp(be_gross_8y,0)} juta penjualan bruto. '
              'Ini perubahan estimasi non-kas yang memerlukan bukti teknis serta pandangan auditor dan konsultan pajak, bukan alat untuk mengecilkan rugi.')
if not land_in_unit:
    b3.append('Tanah tidak tercatat di pembukuan unit (lihat §4).')
F(S['dep_equip'], 'Aset tetap', f'Basis aset Rp {rpbn(S["fa_cost"])} miliar berputar {idn(asset_turnover,2)} kali setahun; peralatan bengkel disusutkan {idn(equip_life_y,0)} tahun', ' '.join(b3),
  'Neraca, Nilai histori dan Akumulasi Penyusutan; Laba Rugi, Biaya Penyusutan.')

# 4. perubahan harga perolehan aset tetap
if FA_EVENTS:
    aff = []
    for k, nm, dk in FA_CLASSES:
        if any(nm in e[4] for e in FA_EVENTS):
            first = _chain[0]
            aff.append(f'beban penyusutan {nm.lower()} Rp {rp(M[first][dk])} juta di {mname(first)} menjadi Rp {rp(S[dk])} juta di {NS}')
    F(FA_SIZE, 'Aset tetap', 'Harga perolehan aset tetap berubah dalam jendela: ' + '; '.join(e[3] for e in FA_EVENTS),
      'Perubahan: ' + '; '.join(e[3] for e in FA_EVENTS) + '. Dampak pada beban: ' + '; '.join(aff) + '. Perubahan antar kelompok perlu didukung dokumen reklasifikasi; penambahan perlu dicocokkan dengan faktur dan tanggal siap pakai.',
      f'Neraca, Nilai histori, {MLABEL[_chain[0]]} – {MLABEL[MS]}.')

# 5. akun beban dengan pergerakan terbesar
mv = sorted(((r['acct'], r['v'][2] - r['v'][1], r['v'][1], r['v'][2]) for r in ledger), key=lambda x: -abs(x[1]))
mv = [x for x in mv if abs(x[1]) >= AN['mover_min_pct_of_opex'] * S['opex']][:3]
if mv:
    lines = []
    for a_, d_, v1, v2 in mv:
        extra = f', baru muncul di {NS}' if v1 == 0 else (f', tidak ada lagi di {NS}' if v2 == 0 else f' ({pct(chg(v1, v2))})')
        lines.append(f'{desc(a_)} {arah(d_)} Rp {rp(abs(d_))} juta dari Rp {rp(v1)} juta ({NA}) ke Rp {rp(v2)} juta ({NS}){extra}')
    od = S['opex'] - A['opex']
    F(abs(mv[0][1]), 'Beban operasional', f'Pergerakan akun terbesar {NA} → {NS}: {desc(mv[0][0])} {arah(mv[0][1])} Rp {rp(abs(mv[0][1]))} juta',
      '; '.join(lines) + f'. Total opex {arah(od)} Rp {rp(abs(od))} juta ({pct(chg(A["opex"], S["opex"]))}) dalam bulan yang sama.', f'Buku besar Beban Umum dan Administrasi serta Beban Penjualan, {NA}–{NS}.')

# 6. pendapatan
_tpr = [M[m]['tp_share'] for m in MONTHS]
b6 = [f'Pendapatan jasa {arah(S["sales_jasa"]-J["sales_jasa"])} {p1(ac(J["sales_jasa"], S["sales_jasa"]))} dalam kuartal ke Rp {rp(S["sales_jasa"])} juta (margin {p1(J["gm_jasa"])} → {p1(A["gm_jasa"])} → {p1(S["gm_jasa"])}). '
      f'Suku cadang {arah(S["sales_parts"]-J["sales_parts"])} {p1(ac(J["sales_parts"], S["sales_parts"]))} (Rp {rp(J["sales_parts"])} → {rp(A["sales_parts"])} → {rp(S["sales_parts"])} juta) dan marginnya {p1(J["gm_parts"])} → {p1(A["gm_parts"])} → {p1(S["gm_parts"])}.']
b6.append('Harga pokok jasa (bagi hasil tim pengerjaan pihak ketiga) ' + (f'tetap {p1(min(_tpr))}–{p1(max(_tpr))} dari pendapatan jasa neto di setiap bulan: pola bagi hasil tetap, bukan biaya yang mengikuti efisiensi.' if max(_tpr) - min(_tpr) <= TOLR else f'bergerak {p1(min(_tpr))}–{p1(max(_tpr))} dari pendapatan jasa neto.'))
F(S['sales'] - J['sales'], 'Pendapatan', f'Penjualan bruto {arah(S["sales"]-J["sales"])} {p1(ac(J["sales"], S["sales"]))} dalam kuartal ke Rp {rp(S["sales"])} juta: jasa {pct(chg(J["sales_jasa"], S["sales_jasa"]))}, suku cadang {pct(chg(J["sales_parts"], S["sales_parts"]))}', ' '.join(b6),
  'Laba Rugi, Penjualan dan Harga Pokok Penjualan per sumber.')

# 7. margin kotor
dgm = gm_now - gm_prev
F(dgm * S['net_sales'], 'Margin', f'Margin kotor gabungan {arah(dgm)} {idn(abs(dgm)*100,1)} poin persentase ke {p1(gm_now)} di {NS}',
  f'Margin kotor {p1(gm_prev)} di {NA} menjadi {p1(gm_now)} di {NS}; pada pendapatan neto {NS} selisih itu bernilai Rp {rp(abs(dgm*S["net_sales"]))} juta laba kotor. Margin jasa {p1(A["gm_jasa"])} → {p1(S["gm_jasa"])}, suku cadang {p1(A["gm_parts"])} → {p1(S["gm_parts"])}; suku cadang {p0(S["sales_parts"]/S["sales"])} dari penjualan dan {p0(S["gp_parts"]/S["gp"]) if S["gp"] else "t/b"} dari laba kotor.',
  'Laba Rugi, Laba Kotor per sumber.')

# 8. diskon
if S['sales_jasa'] and S['sales_parts'] and J['sales']:
    ddr = S['disc_rate'] - J['disc_rate']
    F(ddr * S['sales'], 'Diskon', f'Tingkat diskon {arah(ddr)} dari {p1(J["disc_rate"])} ({NJ}) ke {p1(S["disc_rate"])} ({NS}) dari penjualan bruto',
      f'Diskon {NS} Rp {rp(S["disc"])} juta: jasa {p1(disc_svc_rate[MJ])} → {p1(disc_svc_rate[MA])} → {p1(disc_svc_rate[MS])}, suku cadang {p1(disc_parts_rate[MJ])} → {p1(disc_parts_rate[MA])} → {p1(disc_parts_rate[MS])}. '
      f'Diskon tiga bulan Rp {rp(Q3["disc"])} juta setara {p0(Q3["disc"]/Q3["gp"]) if Q3["gp"] else "t/b"} dari laba kotor periode itu. Tidak ada matriks persetujuan diskon per jenis pelanggan dalam laporan.', 'Laba Rugi, Potongan Penjualan.')

# 9. insentif
if S['insentif'] > 0 and S['gaji'] > 0:
    F(S['insentif'], 'Beban SDM', f'Insentif Rp {rp(S["insentif"])} juta ({p1(ins_rate[MS])} dari penjualan bruto) setara {p0(S["insentif"]/S["gaji"])} dari gaji pokok Rp {rp(S["gaji"])} juta',
      f'Insentif berjalan {p1(ins_rate[MJ])}, {p1(ins_rate[MA])} dan {p1(ins_rate[MS])} dari penjualan bruto di {NJ}, {NA} dan {NS} (Rp {rp(J["insentif"])} → {rp(A["insentif"])} → {rp(S["insentif"])} juta)'
      + (', dibayarkan pada bulan merugi tanpa kaitan dengan laba.' if S['net'] < 0 else '.'), 'Buku besar Beban Umum dan Administrasi, Biaya Insentif dan Biaya Gaji.')

# 10. piutang usaha
if bsv(MJ, 'PIUTANG USAHA') is not None and bsv(MS, 'PIUTANG USAHA') is not None and (J['ar'] or S['ar']):
    arg_, sg_ = chg(J['ar'], S['ar']), chg(J['sales'], S['sales'])
    cmp_ = '' if arg_ is None or sg_ is None else (' lebih cepat dari penjualan' if arg_ > sg_ + 0.005 else (' lebih lambat dari penjualan' if arg_ < sg_ - 0.005 else ' sejalan dengan penjualan'))
    b10 = f'Piutang bergerak Rp {rp(J["ar"])} → {rp(A["ar"])} → {rp(S["ar"])} juta{cmp_}. Laporan tidak menyajikan umur piutang maupun rincian per perusahaan asuransi.'
    if bsv(MJ, 'UANG MUKA PENJUALAN') is not None and bsv(MS, 'UANG MUKA PENJUALAN') is not None:
        b10 += f' Uang muka pelanggan {arah(S["uang_muka"]-J["uang_muka"])} dari Rp {rp(J["uang_muka"])} juta menjadi Rp {rp(S["uang_muka"])} juta.'
    F(S['ar'] - J['ar'], 'Modal kerja', f'Piutang jasa {arah(S["ar"]-J["ar"])} {p1(ac(J["ar"], S["ar"]))} dalam tiga bulan menjadi Rp {rp(S["ar"])} juta ({idn(S["dso"],0)} hari penjualan)', b10, 'Neraca, Piutang Usaha dan Uang Muka Penjualan.')

# 11. kas, hutang HO dan rekening pembukuan pusat
if bsv(MS, 'KAS & BANK') is not None and (S['cash'] or S['hutang_ho'] or S['ho_clearing']):
    parts11 = [f'Kas Rp {rpbn(S["cash"])} miliar ({arah(cash_q3_change)} Rp {rp(abs(cash_q3_change))} juta sejak {CASH_BASE_NAME})']
    if bsv(MS, 'HUTANG AFILIASI') is not None: parts11.append(f'Hutang HO {arah(hutang_ho_q3_change)} Rp {rp(abs(hutang_ho_q3_change))} juta')
    b11 = [f'Kas dan bank Rp {rp(M[CASH_BASE]["cash"])} juta ({CASH_BASE_NAME}) menjadi Rp {rp(S["cash"])} juta ({NS}); bunga bank {NS} Rp {idn(bank_interest,0)}.']
    if bsv(MS, 'Piutang Transaksi Cabang') is not None:
        b11.append(f'Rekening Pembukuan Pusat HO Rp {rpbn(S["ho_clearing"])} miliar ' + (f'{arah(clearing_q3_change, "bertambah", "berkurang")} Rp {rp(abs(clearing_q3_change))} juta sejak {CASH_BASE_NAME}' if abs(clearing_q3_change) >= 1 else f'tidak bergerak sejak {CASH_BASE_NAME}') + f'; bersama Hutang HO, pendanaan HO Rp {rpbn(ho_funding)} miliar disajikan sebagai kliring, bukan pinjaman atau modal.')
    b11.append(f'Pada bunga ilustratif {p0(SC_CFG["idle_cash_rate_pa"])} per tahun, kas unit bernilai Rp {rp(idle_cash_income)} juta per bulan.')
    if G and 'deposito' in G: b11.append(f'Dealer utama memegang deposito Rp {idn(G["deposito"]/1e9,0)} miliar.')
    F(max(abs(cash_q3_change), abs(hutang_ho_q3_change), abs(clearing_q3_change)), 'Kas dan pendanaan', '; '.join(parts11), ' '.join(b11), 'Neraca, Kas dan Bank, Hutang Afiliasi, Piutang Transaksi Cabang' + ('; Neraca Inhouse PT DCM.' if G else '.'))

# 12. saldo antar perusahaan (hanya bila laporan dealer bulan ini dipakai)
if G and (abs(ic_gap) >= TOL_IC or abs(clearing_gap) >= TOL_IC):
    gl = [f'{mname(m)} Rp {rp(GROUP[m]["piutang_dcm_body_paint"] - M[m]["hutang_ho"])} juta' for m in MONTHS if m in GROUP]
    cl_vals = [(m, GROUP[m]['pembukuan_pusat_cabang_bp']) for m in MONTHS if m in GROUP]
    still = len(cl_vals) >= 2 and all(abs(v - cl_vals[-1][1]) < 1 for _, v in cl_vals)
    F(max(abs(ic_gap), abs(clearing_gap)), 'Integritas pembukuan', f'Saldo antar perusahaan tidak cocok: selisih Rp {rp(ic_gap)} juta pada hutang HO dan Rp {rp(clearing_gap)} juta pada rekening pembukuan pusat',
      f'Unit mencatat Hutang HO Rp {rp(S["hutang_ho"])} juta, sedangkan dealer utama mencatat Piutang PT DCM Body Paint Rp {rp(ho_recv_bp)} juta. Selisih per bulan (data dealer yang tersedia): ' + ', '.join(gl) + '. '
      f'Rekening Pembukuan Pusat HO di unit Rp {rpbn(S["ho_clearing"])} miliar, di dealer utama Rp {rpbn(G["pembukuan_pusat_cabang_bp"])} miliar' + (f' dan tidak bergerak di {mname(cl_vals[0][0])}–{mname(cl_vals[-1][0])}.' if still else '.'),
      f'Neraca PT DCM Body Paint dan Neraca Inhouse PT DCM, {NS}.')

# 13. akun kliring GR/IR dan persediaan negatif
if bsv(MS, 'GR/IR ACCOUNT') is not None and (grir_growing or inv_neg):
    F(max(S['grir'] if grir_growing else 0.0, -S['inv_parts'] if inv_neg else 0.0), 'Integritas pembukuan',
      f'Akun kliring GR/IR Rp {rp(S["grir"])} juta' + (f' setara {idn(grir_months_cogs)} bulan harga pokok' if grir_months_cogs is not None else '') + (f'; persediaan suku cadang bersaldo negatif Rp ({rp(-S["inv_parts"])}) juta' if inv_neg else ''),
      f'GR/IR {arah(S["grir"]-J["grir"])} dari Rp {rp(J["grir"])} juta ({NJ}) ke Rp {rp(S["grir"])} juta ({NS}); GR/IR suku cadang Rp {rp(S["grir_parts"])} juta.' + (' Persediaan negatif menunjukkan barang dijual sebelum penerimaan dan tagihannya dicatat.' if inv_neg else ''), 'Neraca, GR/IR Account dan Persediaan.')

# 14. uji rekonsiliasi yang tidak lolos di luar antar perusahaan dan GR/IR
rec_fail = [x for x in INTEG if not x[1] and not x[0].startswith(('Saldo antar', 'Akun kliring'))]   # keduanya punya temuan sendiri
if rec_fail:
    F(max(x[3] for x in rec_fail), 'Integritas pembukuan', f'{len(rec_fail)} uji rekonsiliasi pembukuan tidak cocok: ' + '; '.join(x[0] for x in rec_fail), ' '.join(f'{x[0]}: {x[2]}' for x in rec_fail), 'Neraca dan Laba Rugi, uji integritas §5.')

FINDINGS.sort(key=lambda f: -f['size'])
FINDINGS = FINDINGS[:AN['max_findings']]
for f in FINDINGS: f['sev'] = sev_of(f['size'])

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

# ------------------------------------------------------------------ HTML
logo_b64 = base64.b64encode(open(os.path.join(HERE, 'dcm_logo.png'), 'rb').read()).decode()
NEXT_NAME = mname(mshift(MS, 1))
G_NOTE = None if G else f'Laporan dealer utama (Neraca dan Rugi Laba Inhouse PT DCM) untuk {MLABEL[MS]} tidak dipakai: angkanya tidak tersedia di data/raw/group_inhouse.json, sehingga bagian saldo antar perusahaan dan rujukan dealer dihilangkan dan tidak ada angka yang diisi atau dibawa dari bulan lain.'
if G_NOTE: print('CATATAN:', G_NOTE)

def kpi(label, value, sub, delta=None, good_up=True, cls=''):
    dl = ''
    if delta is not None:
        up = delta >= 0; good = up == good_up
        dl = f'<div class="delta {"good" if good else "bad"}">{"▲" if up else "▼"} {p1(abs(delta))} vs {SHA}</div>'
    return f'<div class="kpi {cls}"><div class="kl">{label}</div><div class="kv">{value}</div>{dl}<div class="ks">{sub}</div></div>'

def tr_money(label, vals, bold=False, cls='', fmt=rp):
    cells = ''.join(f'<td class="num">{fmt(v) if not isinstance(v, str) else v}</td>' for v in vals)
    return f'<tr class="{cls}{" bold" if bold else ""}"><td>{label}</td>{cells}</tr>'

def plr(label, key, bold=False, neg=False, cls=''):
    vals = [M[m][key] * (-1 if neg else 1) for m in MONTHS]; q = sum(vals); y = YTD[key] * (-1 if neg else 1)
    cells = ''.join(f'<td class="num">{rp(v)}</td>' for v in vals)
    return f'<tr class="{cls}{" bold" if bold else ""}"><td>{label}</td>{cells}<td class="num">{rp(q)}</td><td class="num">{rp(y)}</td><td class="num">{pct(chg(vals[1], vals[2]))}</td><td class="num">{pct(chg(vals[0], vals[2]))}</td></tr>'

YTD['other'] = tot('other', YR); YTD['op'] = tot('op', YR); YTD['gp_jasa'] = tot('gp_jasa', YR); YTD['gp_parts'] = tot('gp_parts', YR)
YTD['cogs_jasa'] = tot('cogs_jasa', YR); YTD['cogs_parts'] = tot('cogs_parts', YR)
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
        out.append(
            f'<tr><td class="rank">{i+1}</td><td><span class="dot" style="background:{CAT_COLOR[cat(r["acct"])]}"></span>{esc(r["acct"])}<div class="gloss">{esc(desc(r["acct"]))} · {r["type"]}</div></td>'
            f'<td class="num">{rp(r["v"][0])}</td><td class="num">{rp(r["v"][1])}</td><td class="num"><b>{rp(r["v"][2])}</b></td>'
            f'<td class="num">{pct(r["mom"])}</td><td class="num">{pct(r["q"])}</td><td class="num">{rp(r["q3"])}</td><td class="num">{p1(r["share_q3"])}</td><td class="num">{rp(r["ytd"])}</td><td>{spark(r["v"])}</td></tr>')
    return ''.join(out)

ranked_rows = [(desc(r['acct']), r['acct'], r['v'][2], CAT_COLOR[cat(r['acct'])], r['share_sep']) for r in ledger if r['v'][2] > 0]
top3 = [r for r in ledger[:3]]
top3_share = sum(r['v'][2] for r in top3) / S['opex']
gaji = [M[m]['gaji'] for m in MONTHS]
bonus_months = [mname(m) for m in YR if ga(m, 'Biaya Bonus/THR') > 0]
bonus_ytd = sum(ga(m, 'Biaya Bonus/THR') for m in YR)

rev_chart = stacked_columns([('Jasa (tenaga kerja & cat)', 'var(--s1)', [M[m]['sales_jasa'] for m in MONTHS]), ('Suku cadang', 'var(--s2)', [M[m]['sales_parts'] for m in MONTHS])], [MSHORT[m] for m in MONTHS], w=420, h=250)
gp_chart = stacked_columns([('Laba kotor jasa', 'var(--s1)', [M[m]['gp_jasa'] for m in MONTHS]), ('Laba kotor suku cadang', 'var(--s2)', [M[m]['gp_parts'] for m in MONTHS])], [MSHORT[m] for m in MONTHS], w=420, h=250)
opex_chart = stacked_columns([(k, CAT_COLOR[k], v) for k, v in sorted(cat_tot.items(), key=lambda kv: -kv[1][2])], [MSHORT[m] for m in MONTHS], w=420, h=250)
wf = waterfall([
    ('Laba\nkotor', S['gp'], 'start'), ('Beban\npenjualan', -S['selling'], 'delta'), ('U&A\ntunai', -(S['ga'] - S['dep']), 'delta'),
    ('EBITDA', S['ebitda'] - S['other'], 'total'), ('Peny.\nperalatan', -S['dep_equip'], 'delta'), ('Peny.\ngedung', -S['dep_bldg'], 'delta'),
    ('Peny. perl.\nkantor', -S['dep_office'], 'delta'), ('Lain-lain\nneto', S['other'], 'delta'), ('Laba (rugi)\nbersih', S['net'], 'total'),
], w=640, h=215)

_ap = bsv(MS, 'HUTANG')
fund_parts = [('Pembukuan Pusat HO (belanja modal)', S['ho_clearing'], 'var(--s1)'), ('Hutang HO (operasional)', S['hutang_ho'], 'var(--s2)'), ('GR/IR dan kewajiban lain', S['grir'] + (_ap or 0.0) - S['hutang_ho'] - S['grir'], 'var(--s4)')]
fund_total = ho_funding + S['grir'] + ((_ap or 0.0) - S['hutang_ho'] - S['grir'])

sev_cls = {'TINGGI': 'high', 'SEDANG': 'med', 'RENDAH': 'low'}
findings_html = ''.join(
    f'<div class="finding {sev_cls[f["sev"]]}"><div class="fh"><span class="sev">{f["sev"]}</span><span class="area">{esc(f["area"])}</span><span class="fn">Temuan {i+1}</span></div>'
    f'<h4>{esc(f["title"])}</h4><p>{esc(f["body"])}</p><div class="ev">Sumber: {esc(f["evidence"])}</div></div>' for i, f in enumerate(FINDINGS))
integrity_html = ''.join(f'<tr><td>{esc(n)}</td><td class="{"pass" if ok else "fail"}">{"LOLOS" if ok else "PERHATIAN"}</td><td>{note}</td></tr>' for n, ok, note, _g in INTEG)
scen_rows = ''.join(
    f'<tr><td class="rank">{c}</td><td>{esc(n)}<div class="gloss">{esc(note)}</div></td><td class="num">{rp(g)}</td><td class="num">{p1(gm)}</td><td class="num">{rp(ox)}</td><td class="num {"good" if net >= 0 else "bad"}"><b>{rp(net)}</b></td></tr>'
    for c, n, g, gm, ox, net, note in SCEN_RES)

# rekomendasi: setiap butir dibuat hanya bila angkanya dapat dihitung dan bermakna untuk bulan ini
RECS = []
def REC(t, b, i): RECS.append((t, b, i))
b = []
if G:
    b.append(f'Dealer utama menjual unit Rp {idn(G["sales_unit"]/1e9,1)} miliar dan jasa serta suku cadang Rp {rp(aftersales_ho,0)} juta di {NS}; body &amp; paint hanya Rp {rp(S["sales"])} juta, {p1(bp_share)} dari penjualan grup. '
             'Jadikan setiap unit yang diserahkan sebagai pelanggan bengkel: rujukan rekanan asuransi saat serah terima, voucer perbaikan tahun pertama, booking silang oleh service advisor bengkel umum, dan akun armada. ')
_bev = (be_gross_now / S['sales'] - 1) * 100
b.append(f'Titik impas penuh pada basis biaya saat ini adalah penjualan bruto Rp {rp(be_gross_now,0)} juta per bulan ({"+" if _bev >= 0 else "-"}{idn(abs(_bev),0)}% dari {NS}); setiap tambahan Rp {rp(POL["volume_step"],0)} juta penjualan bruto menambah laba sekitar Rp {rp(vol_step)} juta karena biaya tunai hampir seluruhnya tetap.')
REC('Isi kapasitas dari jaringan Toyota DCM sendiri, bukan dari belanja pemasaran' if G else 'Tambah volume pada kapasitas yang sudah ada',
    ''.join(b),
    (f'Target: Rp {rp(TGT,0)} juta per bulan (skenario {SCODE["target"]}: hasil bulanan Rp {rp(SCEN_NET["target"])} juta), titik impas penuh Rp {rp(be_gross_now,0)} juta.' if TGT_OK else f'Titik impas penuh: Rp {rp(be_gross_now,0)} juta penjualan bruto per bulan.'))
if ALT_OK:
    REC(f'Tinjau umur ekonomis oven dan booth bersama auditor dan konsultan pajak',
        f'Seluruh peralatan bengkel Rp {rpbn(S["fa_equip_cost"])} miliar disusutkan {idn(equip_life_y,0)} tahun ({p0(equip_rate)} per tahun). Bila oven, booth dan peralatan berat dipisahkan dan disusutkan {ALT_YEARS} tahun sesuai umur teknisnya, beban turun Rp {rp(dep_saving_8y)} juta per bulan dan titik impas turun ke Rp {rp(be_gross_8y,0)} juta. '
        'Perubahan ini non-kas, memerlukan dasar teknis (spesifikasi pabrikan, jadwal pemeliharaan) dan konsistensi dengan kebijakan grup; jangan dipakai hanya untuk memperkecil rugi.',
        f'Dampak: ≈ Rp {rp(dep_saving_8y)} juta per bulan pada laba pembukuan, nol pada kas' + (f' (skenario {SCODE["target8"]}: Rp {rp(SCEN_NET["target8"])} juta).' if 'target8' in SCODE else '.'))
if (tp_to_40 > 0 or ins_to_8pct > 0) and S['net_jasa'] > 0:
    parts_ = []
    if tp_to_40 > 0: parts_.append(f'Rp {rp(tp_to_40)} juta (bagi hasil ke {p0(TP_T)})')
    if ins_to_8pct > 0: parts_.append(f'Rp {rp(ins_to_8pct)} juta (insentif ke {p0(POL["incentive_cap_of_gross_sales"])})')
    REC('Ubah skema bagi hasil pihak ketiga dan insentif agar mengikuti laba, bukan penjualan',
        f'Harga pokok jasa {p1(S["tp_share"])} dari pendapatan jasa neto, sementara insentif berjalan {p1(ins_rate[MS])} dari penjualan bruto' + (', keduanya dibayar penuh pada bulan rugi' if S['net'] < 0 else '') + '. '
        f'Terapkan tingkatan bagi hasil berbasis volume ({p0(TP_T)} hingga Rp {rp(POL["third_party_tier_threshold_jasa"],0)} juta jasa per bulan, {p0(POL["third_party_tier_high"])} di atasnya), biaya pemakaian booth/oven yang dipotong dari bagi hasil, klausul pengerjaan ulang, dan insentif yang dibayar dari EBITDA positif dengan batas {p0(POL["incentive_cap_of_gross_sales"])} dari penjualan bruto.',
        'Dampak: ≈ ' + ' + '.join(parts_) + f' per bulan pada volume {NS}.')
if parts_to_prev > 0 or inv_neg or disc_to_cap > 0:
    b = []
    b.append(f'Margin suku cadang {p1(J["gm_parts"])} → {p1(A["gm_parts"])} → {p1(S["gm_parts"])} dalam tiga bulan')
    if inv_neg: b.append(f'; persediaan suku cadang negatif Rp ({rp(-S["inv_parts"])}) juta dan GR/IR suku cadang Rp {rp(S["grir_parts"])} juta menunjukkan barang dijual sebelum penerimaan dan tagihannya dicatat')
    b.append(f'. Cocokkan GR/IR dengan faktur {"dealer utama" if G else "pemasok"} setiap bulan, pakai harga transfer yang disepakati')
    if parts_to_prev > 0: b.append(f', tetapkan margin dasar suku cadang {p0(A["gm_parts"])} per pekerjaan')
    b.append(f' dan terapkan matriks diskon (batas gabungan {p0(POL["discount_cap_of_gross_sales"])} dari penjualan bruto; {NS}: {p1(S["disc_rate"])}).')
    imp = []
    if parts_to_prev > 0: imp.append(f'Rp {rp(parts_to_prev)} juta per bulan (margin suku cadang kembali ke level {NA})')
    if disc_to_cap > 0: imp.append(f'Rp {rp(disc_to_cap)} juta dari disiplin diskon')
    REC('Perbaiki penetapan harga pokok suku cadang dan tetapkan margin dasar', ''.join(b), 'Dampak: ≈ ' + ' + '.join(imp) + '.' if imp else 'Dampak: neraca persediaan yang dapat dipercaya.')
_excess = S['cash'] - S['cash_opex']
if _excess > 0 and S['hutang_ho'] > 0:
    b = (f'Pindahkan kas yang tidak dibutuhkan (menyisakan sekitar satu bulan opex tunai, Rp {rp(S["cash_opex"],0)} juta) ke kantor pusat untuk melunasi Hutang HO Rp {rp(S["hutang_ho"])} juta, atau tempatkan dalam deposito. ')
    if S['ho_clearing'] > 0:
        b += f'Catat pendanaan belanja modal Rp {rpbn(S["ho_clearing"])} miliar sebagai pinjaman antar perusahaan atau penyertaan modal dengan biaya bunga internal, agar manajer unit dinilai atas modal yang dipakainya. '
    if G and (abs(ic_gap) >= TOL_IC or abs(clearing_gap) >= TOL_IC):
        b += f'Rekonsiliasi dan selesaikan selisih Rp {rp(ic_gap)} juta (Hutang HO vs piutang di dealer utama) dan Rp {rp(clearing_gap)} juta (pembukuan pusat) sebelum tutup buku.'
    REC('Rapikan pendanaan HO dan kas berlebih' + (', lalu rekonsiliasi saldo antar perusahaan' if G and (abs(ic_gap) >= TOL_IC or abs(clearing_gap) >= TOL_IC) else ''), b,
        f'Dampak: ≈ Rp {rp(idle_cash_income)} juta per bulan pendapatan bunga pada tingkat grup ({p0(SC_CFG["idle_cash_rate_pa"])} per tahun, ilustratif).')
if BASE:
    hi_m = [m for m in MONTHS if M[m]['cash_opex'] > cash_opex_base]
    b = f'Opex tunai rata-rata {BASE_LABEL} Rp {rp(cash_opex_base)} juta per bulan; ' + ', '.join(f'{mname(m)} Rp {rp(M[m]["cash_opex"])} juta' for m in MONTHS) + '. '
    if mv and mv[0][1] > 0:
        b += f'Kenaikan terbesar {NA} → {NS} ada pada {desc(mv[0][0])} (Rp {rp(mv[0][1])} juta); tinjau apakah rutin atau sekali pakai. '
    b += f'Tetapkan plafon Rp {rp(cash_opex_base,0)} juta per bulan dan wajibkan persetujuan tertulis untuk pos di atas Rp {rp(POL["approval_threshold"],0)} juta.'
    REC('Tahan opex tunai di level pembanding dan kendalikan pos sekali pakai', b,
        f'Dampak: Rp {rp(abs(Q3["cash_opex"]/3 - cash_opex_base))} juta per bulan {"di atas" if Q3["cash_opex"]/3 > cash_opex_base else "di bawah"} pembanding pada rata-rata tiga bulan terakhir.')
recs_html = ''.join(f'<div class="rec"><div class="rn">{i+1}</div><div><h4>{t}</h4><p>{b}</p><div class="impact">{esc(im)}</div></div></div>' for i, (t, b, im) in enumerate(RECS))

path_rows = [(f'Laba (rugi) bersih {MLABEL[MS]}', S['net'])]
if tp_to_40 > 0: path_rows.append((f'+ bagi hasil pihak ketiga ke {p0(TP_T)} dari jasa neto', tp_to_40))
if ins_to_8pct > 0: path_rows.append((f'+ insentif dibatasi {p0(POL["incentive_cap_of_gross_sales"])} dari penjualan bruto', ins_to_8pct))
if parts_to_prev > 0: path_rows.append((f'+ margin suku cadang kembali ke level {NA}', parts_to_prev))
path_rows.append((f'+ bunga atas kas ({p0(SC_CFG["idle_cash_rate_pa"])} p.a., tingkat grup)', idle_cash_income)) if _excess > 0 else None
path_rows.append((f'+ volume +Rp {rp(POL["volume_step"],0)} juta bruto pada margin {NS}', vol_step))
if ALT_OK: path_rows.append((f'+ umur oven/booth {ALT_YEARS} tahun (non-kas)', dep_saving_8y))
path_rows = [r for r in path_rows if r]
run = 0; path_html = ''
for i, (lab, v) in enumerate(path_rows):
    run = v if i == 0 else run + v
    path_html += f'<tr><td>{esc(lab)}</td><td class="num">{rp(v)}</td><td class="num {"good" if run >= 0 else "bad"}"><b>{rp(run)}</b></td></tr>'

# ------------------------------------------------------------------ kalimat turunan untuk HTML
def top_in(cname):
    rows = [r for r in ledger if cat(r['acct']) == cname and r['v'][2] > 0]
    return rows[0] if rows else None
_lead_net = f'{hasil(S["net"])} Rp {rp(abs(S["net"]))} juta'
if S['net'] >= 0:
    _lead_tail = f'Unit menutup seluruh biayanya, termasuk penyusutan Rp {rp(S["dep"])} juta per bulan atas gedung dan peralatan.'
elif S['ebitda'] >= 0:
    _lead_tail = f'Secara kas unit menutup biayanya (EBITDA Rp {rp(S["ebitda"])} juta), tetapi penyusutan Rp {rp(S["dep"])} juta per bulan atas gedung dan peralatan belum tertutup.'
else:
    _lead_tail = f'EBITDA negatif Rp ({rp(-S["ebitda"])}) juta: biaya tunai pun belum tertutup, dan penyusutan Rp {rp(S["dep"])} juta per bulan menambah beban.'
_g_lead = f' Seluruh unit ini baru {pct(bp_share, 2, sign=False)} dari penjualan grup DCM (dealer utama + unit).' if G else ''
_ebitda_back = f' · kembali positif di {NS}' if S['ebitda'] > 0 and A['ebitda'] <= 0 else ''
_pri_ret = bsv(MS, 'Laba Ditahun Tahun Sebelumnya')
def lossp(v): return f'({rp(-v)})' if v < 0 else rp(v)
_eq_note = (f'Ekuitas {"adalah akumulasi rugi" if S["equity"] < 0 else "terdiri dari hasil ditahan"}: {YEAR-1} dan sebelumnya {lossp(_pri_ret)} dan {YEAR} s.d. {NS} {lossp(YTD["net"])}. ' if _pri_ret is not None else '') + \
          ('Tidak ada modal yang disetor. ' if _mod is not None and abs(_mod) < 1 else '') + ('Pendanaan HO disajikan sebagai rekening kliring.' if S['ho_clearing'] else '')
_ins_gedung = [m for m in YR if ga(m, 'Biaya Asuransi Gedung') > 0]
_ins_li = (f'<li>Beban asuransi gedung nihil di {NS} (terakhir dibukukan {mlabel(_ins_gedung[-1])}); pastikan polis diperpanjang.</li>' if _ins_gedung and ga(MS, 'Biaya Asuransi Gedung') == 0 and _ins_gedung[-1] < MS else '')
_fa_bldg_ev = [e[3] for e in FA_EVENTS if 'Bangunan' in e[4]]
_fa_li = (f'<li>Harga perolehan gedung berubah: {"; ".join(_fa_bldg_ev)}; beban gedung Rp {rp(M[_chain[0]]["dep_bldg"])} juta ({mname(_chain[0])}) menjadi Rp {rp(S["dep_bldg"])} juta ({NS}).</li>' if _fa_bldg_ev else '')
_land_li = ''
if not land_in_unit:
    _land_li = ('<li><b>Tanah: nihil di neraca unit.</b> Tanah bengkel berada di luar pembukuan ini' +
                (f' (dealer utama mencatat Tanah Rp {rpbn(HO_LAND)} miliar dan Investasi dalam Tanah &amp; Bangunan Rp {idn(HO_INV_LAND_BLDG/1e9,1)} miliar)' if HO_LAND is not None and HO_INV_LAND_BLDG is not None else '') +
                '. Tanah tidak disusutkan, tetapi modal yang dipakai unit tersaji terlalu rendah dan tidak ada beban sewa atau biaya modal atasnya.</li>')
_alt_li = (f'<li>Pada umur {ALT_YEARS} tahun, yang lazim untuk booth dan oven, beban turun ke Rp {rp(dep_equip_8y)} juta per bulan (hemat Rp {rp(dep_saving_8y)} juta, non-kas); perlu pandangan auditor dan konsultan pajak serta pemisahan peralatan berat dari perkakas kecil dalam daftar aktiva.</li>' if ALT_OK else '')
_ytd_since = 'sejak awal tahun' if YR[0] == f'{YEAR}-01' else f'sejak {MLABEL[YR[0]]}'
_office_li = (f'<li><b>Peralatan kantor</b> Rp {rp(S["fa_office_cost"])} juta, Rp {rp(S["dep_office"])} juta per bulan, tersisa {idn(office_months_left,0)} bulan. ' +
              (f'Tidak ada perubahan harga perolehan peralatan dalam {QLABEL}; ' if equip_add_window == 0 else '') + f'nilai buku seluruh aset tetap Rp {rpbn(S["nbv"])} miliar.</li>')
_cash_note = 'sudah terlampaui' if cash_be_gross <= S['sales'] else 'belum tercapai'
_dep_pct_inc = [(YR[0], M[YR[0]]['dep'])]
_vol_start = f'penjualan bruto {arah(S["sales"]-M[YR[0]]["sales"])} dari Rp {rp(M[YR[0]]["sales"])} juta ({mname(YR[0])}) ke Rp {rp(S["sales"])} juta' if YR[0] != MS else f'penjualan bruto Rp {rp(S["sales"])} juta'
_be_8y_txt = f', atau Rp {rp(be_gross_8y,0)} juta bila umur oven dan booth ditinjau menjadi {ALT_YEARS} tahun' if ALT_OK else ''
_dealer_txt = f' Dealer utama menjual unit Rp {idn(G["sales_unit"]/1e9,1)} miliar sebulan: sumber volume yang belum digarap (§7).' if G else ''
_ic_txt = f', dan saldo antar perusahaan berselisih Rp {rp(ic_gap)} juta' if G and abs(ic_gap) >= TOL_IC else ''
_tp_ins = f'Di atasnya, bagi hasil {p0(S["tp_share"])} kepada tim pihak ketiga' + (f' dan insentif {p1(ins_rate[MS])} dari penjualan' if ins_rate[MS] is not None and S['insentif'] > 0 else '') + (' dibayar penuh pada bulan rugi' if S['net'] < 0 else ' dibayar penuh') + _ic_txt + '.'
_top_names = ', '.join(desc(r['acct']).lower() for r in top3)
_gm_max = max(MONTHS, key=lambda m: M[m]['gm'])
_cat_fac = top_in('Fasilitas & administrasi'); _cat_sell = top_in('Penjualan & promosi')
_dep_up = cat_tot['Penyusutan'][2] - cat_tot['Penyusutan'][1]
_dep_reason = f' karena penambahan bangunan Rp {rp(bldg_add)} juta' if abs(bldg_add) >= 1 else ''
_bonus_note = f'Bonus/THR Rp {rp(bonus_ytd)} juta dibayarkan di {", ".join(bonus_months)}. ' if bonus_months else ''
_dealer_scope = f' Angka dealer utama (penjualan, piutang kepada unit, rekening pembukuan pusat, deposito) diambil dari Laporan Neraca dan Rugi Laba Inhouse PT DCM untuk {MLABEL[MS]}.' if G else f' {G_NOTE}'
_notice_html = f'<div class="callout blue" style="margin-top:14px"><b>Data dealer utama tidak dipakai.</b> {G_NOTE}</div>' if G_NOTE else ''
_ar_row = (tr_money('Piutang afiliasi', [J['piutang_gr'], A['piutang_gr'], S['piutang_gr']]) if any(M[m]['piutang_gr'] for m in MONTHS) else '')
_dso_target = POL['receivable_max_days']
_cost_opex_cap = cash_opex_base if BASE else S['cash_opex']

HTML = f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT DCM Body Paint — Tinjauan Keuangan, {MLABEL[MS]}</title>
<style>{CSS}</style></head>
<body><div class="page">

<section class="cover">
 <div class="brand"><img src="data:image/png;base64,{logo_b64}" alt="DCM"><span>PT Duta Cendana Mobilindo · Dealer Toyota</span></div>
 <h1>Tinjauan bisnis Body &amp; Paint<br>PT DCM Body Paint, {MLABEL[MS]}</h1>
 <h2>Ringkasan keuangan tiga bulan ({QLABEL}), analisis sub-buku besar akun per akun, penyusutan gedung dan peralatan, dan jalan menuju laba</h2>
 <div class="meta">
  <div><b>Disusun untuk</b>Manajemen PT DCM</div>
  <div><b>Disusun oleh</b>Financial Controller (tinjauan analitis)</div>
  <div><b>Sumber</b>Laporan Neraca &amp; Rugi Laba PT DCM Body Paint, {' / '.join(mname(m) for m in MONTHS[:-1])} / {MLABEL[MS]} (ACCURATE)</div>
  <div><b>Diterbitkan</b>{today}</div>
 </div>
 <div style="margin-top:18px"><span class="pill">Semua angka dalam juta Rupiah kecuali disebutkan lain</span><span class="pill">Perbandingan bulan ke bulan, {NJ} → {NS}</span><span class="pill">Bukan audit — tinjauan analitis atas laporan manajemen</span></div>
</section>
{_notice_html}

<h2 class="sec"><span class="n">1</span>Ringkasan eksekutif</h2>
<p class="lead">PT DCM Body Paint adalah bengkel body &amp; paint Toyota milik DCM; laporan keuangannya tersedia sejak {MLABEL[ALL[0]]} dengan basis aset tetap Rp {rpbn(S['fa_cost'])} miliar. {MLABEL[MS]}: penjualan bruto Rp {rp(S['sales'])} juta ({pct(chg(J['sales'], S['sales']))} dibanding {NJ}), {_lead_net}. {_lead_tail}</p>
<div class="grid g4">
 {kpi(f'Laba (rugi) bersih, {NS}', (f'<span style="color:#ffb4ad">{rp(S["net"])}</span>' if S['net'] < 0 else rp(S['net'])), f'{SHJ} {rp(J["net"])} · {SHA} {rp(A["net"])} · s.d. {SHS} {rp(YTD["net"])}', cls='hero')}
 {kpi('Penjualan bruto', rp(S['sales']), f'{SHJ} {rp(J["sales"])} · {SHA} {rp(A["sales"])} · {pct(chg(J["sales"], S["sales"]))} sepanjang kuartal', chg(A['sales'], S['sales']))}
 {kpi('Laba kotor', rp(S['gp']), f'Margin gabungan {p1(S["gm"])} dari pendapatan neto ({SHJ} {p1(J["gm"])}, {SHA} {p1(A["gm"])})', chg(A['gp'], S['gp']))}
 {kpi('Beban operasional', rp(S['opex']), f'termasuk penyusutan {rp(S["dep"])} ({p0(S["dep"]/S["opex"])})', chg(A['opex'], S['opex']), good_up=False)}
</div>
<div class="grid g4" style="margin-top:14px">
 {kpi('EBITDA (hasil kas)', rp(S['ebitda']), f'{SHJ} {rp(J["ebitda"])} · {SHA} {rp(A["ebitda"])}{_ebitda_back}', chg(A['ebitda'], S['ebitda']) if abs(A['ebitda']) > 1e5 else None)}
 {kpi('Piutang jasa', rp(S['ar']), f'{idn(S["dso"],0)} hari penjualan · {arah(S["ar"]-J["ar"])} {p1(ac(J["ar"], S["ar"]))} dalam kuartal', chg(A['ar'], S['ar']), good_up=False)}
 {kpi('Ekuitas unit', (f'<span class="bad">({rpbn(-S["equity"])}) miliar</span>' if S['equity'] < 0 else f'{rpbn(S["equity"])} miliar'), f'Ekuitas {"negatif" if S["equity"] < 0 else ""} sejak laporan pertama ({MSHORT[ALL[0]]}){", tanpa modal disetor" if _mod is not None and abs(_mod) < 1 else ""} · pendanaan HO Rp {rpbn(ho_funding)} miliar')}
 {kpi('Kas dan bank', rpbn(S['cash']) + ' miliar', f'{arah(cash_q3_change)} Rp {rp(abs(cash_q3_change))} juta sejak {CASH_BASE_NAME} · bunga bank {NS} Rp {idn(bank_interest,0)}')}
</div>
<div class="grid g2" style="margin-top:14px">
 <div class="callout"><b>Sorotan struktur biaya.</b> Fasilitas Rp {rpbn(S['fa_cost'])} miliar menghasilkan Rp {rp(S['sales'])} juta penjualan bruto per bulan ({idn(asset_turnover,2)} kali perputaran aset setahun), sehingga penyusutan Rp {rp(S['dep'])} juta memakan {p0(S['dep']/S['net_sales'])} dari pendapatan neto; peralatan bengkel disusutkan {idn(equip_life_y,0)} tahun, Rp {rp(S['dep_equip'])} juta per bulan sampai {equip_end}. {_tp_ins}</div>
 <div class="callout blue"><b>Gambaran kas dan volume.</b> EBITDA {NS} Rp {rp(S['ebitda'])} juta; {_vol_start}. Setiap tambahan Rp {rp(POL['volume_step'],0)} juta penjualan bruto menambah laba sekitar Rp {rp(vol_step)} juta. Titik impas penuh Rp {rp(be_gross_now,0)} juta per bulan{_be_8y_txt}.{_dealer_txt}</div>
</div>

<h2 class="sec pb"><span class="n">2</span>Analisis pendapatan, {QLABEL}</h2>
<p class="lead">Dua sumber pendapatan: jasa (tenaga kerja dan cat, dikerjakan oleh tim pihak ketiga dengan bagi hasil) serta suku cadang yang dipasang pada pekerjaan perbaikan. Dalam kuartal ini jasa {arah(S['sales_jasa']-J['sales_jasa'])} {p1(ac(J['sales_jasa'], S['sales_jasa']))} dan suku cadang {arah(S['sales_parts']-J['sales_parts'])} {p1(ac(J['sales_parts'], S['sales_parts']))}. Diskon menyerap {p1(S['disc_rate'])} dari penjualan bruto di {NS}.{_g_lead}</p>
<div class="grid g3">
 <div class="card"><h3>Penjualan bruto per sumber</h3><div class="sub">Rp juta · bruto, sebelum diskon</div>{rev_chart}{legend([('Jasa (tenaga kerja & cat)', 'var(--s1)'), ('Suku cadang', 'var(--s2)')])}</div>
 <div class="card"><h3>Laba kotor per sumber</h3><div class="sub">Rp juta · setelah diskon dan harga pokok penjualan</div>{gp_chart}{legend([('Laba kotor jasa', 'var(--s1)'), ('Laba kotor suku cadang', 'var(--s2)')])}</div>
 <div class="card"><h3>Apa yang ditunjukkan kuartal ini</h3><div class="sub">Membaca kedua grafik bersama-sama</div>
  <ul style="margin:0;padding-left:18px;color:var(--ink2)">
   <li><b>Jasa</b>: Rp {rp(J['sales_jasa'])} → {rp(A['sales_jasa'])} → {rp(S['sales_jasa'])} juta ({pct(chg(J['sales_jasa'], S['sales_jasa']))}); margin {p1(J['gm_jasa'])} → {p1(A['gm_jasa'])} → {p1(S['gm_jasa'])}; harga pokok jasa {p1(S['tp_share'])} dari jasa neto di {NS} (bagi hasil tim pihak ketiga).</li>
   <li><b>Suku cadang</b>: Rp {rp(J['sales_parts'])} → {rp(A['sales_parts'])} → {rp(S['sales_parts'])} juta ({pct(chg(J['sales_parts'], S['sales_parts']))}); margin {p1(J['gm_parts'])} → {p1(A['gm_parts'])} → {p1(S['gm_parts'])}. Suku cadang {p0(S['sales_parts']/S['sales'])} dari penjualan tetapi {p0(S['gp_parts']/S['gp']) if S['gp'] else 't/b'} dari laba kotor.</li>
   <li><b>Pergerakan bulanan</b>: penjualan bruto {pct(chg(J['sales'], A['sales']))} lalu {pct(chg(A['sales'], S['sales']))}; margin gabungan tertinggi di {mname(_gm_max)} ({p1(M[_gm_max]['gm'])}).</li>
   {f"<li><b>Laju berjalan</b>: rata-rata {BASE_LABEL} Rp {rp(BASE['sales'])} juta per bulan, tiga bulan terakhir Rp {rp(Q3['sales']/3)} juta ({pct(chg(BASE['sales'], Q3['sales']/3), 0)}).</li>" if BASE else ''}
   <li><b>Diskon</b> Rp {rp(S['disc'])} juta di {NS} (jasa {p1(disc_svc_rate[MS])}, suku cadang {p1(disc_parts_rate[MS])}), {p0(S['disc']/S['gp']) if S['gp'] else 't/b'} dari laba kotor.</li>
  </ul></div>
</div>
<div class="card" style="margin-top:14px"><h3>Pendapatan neto, EBITDA dan laba (rugi) bersih per bulan, {mname(YR[0])}–{MLABEL[YR[-1]]}</h3><div class="sub">Rp juta · batang = pendapatan neto setelah diskon · garis biru = EBITDA (laba sebelum penyusutan) · garis merah = laba (rugi) bersih</div>{trend_chart(h=240)}{legend([('Pendapatan neto', 'var(--s2)'), ('EBITDA', 'var(--s1)'), ('Laba (rugi) bersih', 'var(--neg)')])}<p class="note" style="margin:6px 0 0">Jarak garis biru ke garis merah adalah penyusutan, Rp {rp(M[YR[0]]['dep'])}–{rp(S['dep'])} juta per bulan.</p></div>
<div class="card" style="margin-top:14px"><h3>Laporan laba rugi unit, tiga bulan</h3><div class="sub">Rp juta · Laba/Rugi PT DCM Body Paint · beban disajikan sebagai angka negatif · s.d. {SHS} = {mname(YR[0])}–{NS} {YEAR}</div>
<table><thead><tr><th>Pos</th><th class="num">{SHJ}</th><th class="num">{SHA}</th><th class="num">{SHS}</th><th class="num">Total 3 bln</th><th class="num">s.d. {SHS}</th><th class="num">{SHS} vs {SHA}</th><th class="num">{SHS} vs {SHJ}</th></tr></thead>
<tbody>{pl_table}{memo}</tbody></table></div>

<h2 class="sec pb"><span class="n">3</span>Analisis sub-buku besar, akun per akun</h2>
<p class="lead">Seluruh akun beban operasional pada Beban Umum dan Administrasi serta Beban Penjualan, diperingkat menurut beban {NS}. Rincian akun ini cocok sampai ke rupiah dengan baris beban di Laba Rugi pada ketiga bulan. Tiga akun terbesar ({_top_names}) membentuk {p0(top3_share)} dari opex {NS}.</p>
<div class="card"><h3>Beban terbesar, {MLABEL[MS]}</h3><div class="sub">Rp juta dan porsi dari total opex Rp {rp(S['opex'])} juta · 12 teratas dari {len(ranked_rows)} akun yang berbeban · warna = kategori biaya</div>{hbar_ranked(ranked_rows, w=1000)}{legend([(k, v) for k, v in CAT_COLOR.items()])}</div>
<div class="grid g2" style="margin-top:14px">
 <div class="card"><h3>Opex per kategori biaya, tiga bulan</h3><div class="sub">Rp juta</div>{opex_chart}{legend([(k, v) for k, v in CAT_COLOR.items()])}</div>
 <div class="card"><h3>Bagaimana basis biaya bergerak</h3><div class="sub">Membaca buku besar per kategori</div>
  <ul style="margin:0;padding-left:18px;color:var(--ink2)">
   <li><b>Penyusutan</b> Rp {rp(cat_tot['Penyusutan'][0])} juta → {rp(cat_tot['Penyusutan'][2])} juta per bulan ({p0(cat_tot['Penyusutan'][2]/S['opex'])} dari opex {NS}); {arah(_dep_up, 'naik', 'turun')} Rp {rp(abs(_dep_up))} juta di {NS}{_dep_reason}.</li>
   <li><b>SDM</b> (gaji, insentif, BPJS, mess, pelatihan): Rp {rp(cat_tot['SDM'][0])} juta → {rp(cat_tot['SDM'][1])} juta → {rp(cat_tot['SDM'][2])} juta. Gaji antara Rp {rp(min(gaji))} juta dan Rp {rp(max(gaji))} juta; insentif Rp {rp(J['insentif'])} → {rp(A['insentif'])} → {rp(S['insentif'])} juta ({p1(ins_rate[MJ])} → {p1(ins_rate[MS])} dari penjualan bruto).</li>
   <li><b>Fasilitas &amp; administrasi</b> Rp {rp(cat_tot['Fasilitas & administrasi'][0])} juta → {rp(cat_tot['Fasilitas & administrasi'][1])} juta → {rp(cat_tot['Fasilitas & administrasi'][2])} juta{f"; pos terbesar {NS}: {desc(_cat_fac['acct']).lower()} Rp {rp(_cat_fac['v'][2])} juta" if _cat_fac else ''}.</li>
   <li><b>Penjualan &amp; promosi</b> Rp {rp(cat_tot['Penjualan & promosi'][2])} juta di {NS}{f", terutama {desc(_cat_sell['acct']).lower()}" if _cat_sell else ''}.</li>
  </ul></div>
</div>
<div class="card flow pb" style="margin-top:14px"><h3>Buku besar akun lengkap</h3><div class="sub">Rp juta · diperingkat menurut {NS} · "Porsi 3 bln" adalah porsi akun terhadap opex {QLABEL} · "s.d. {SHS}" = {mname(YR[0])}–{NS} {YEAR} · grafik kecil menunjukkan pola tiga bulan</div>
<table class="ledger"><thead><tr><th>#</th><th>Akun (sebagaimana dibukukan) / keterangan</th><th class="num">{SHJ}</th><th class="num">{SHA}</th><th class="num">{SHS}</th><th class="num">{SHS} vs {SHA}</th><th class="num">{SHS} vs {SHJ}</th><th class="num">Total 3 bln</th><th class="num">Porsi 3 bln</th><th class="num">s.d. {SHS}</th><th>Tren</th></tr></thead>
<tbody>{ledger_rows(ledger)}
<tr class="total"><td></td><td>Total beban operasional</td><td class="num">{rp(J['opex'])}</td><td class="num">{rp(A['opex'])}</td><td class="num">{rp(S['opex'])}</td><td class="num">{pct(chg(A['opex'], S['opex']))}</td><td class="num">{pct(chg(J['opex'], S['opex']))}</td><td class="num">{rp(Q3['opex'])}</td><td class="num">100%</td><td class="num">{rp(YTD['opex'])}</td><td></td></tr>
</tbody></table>
<p class="note" style="margin:8px 0 0">Akun tanpa beban pada ketiga bulan dan nihil s.d. {NS} tidak ditampilkan. {_bonus_note}Harga pokok penjualan (bagi hasil tim pengerjaan dan suku cadang) tidak termasuk opex dan dianalisis per sumber pendapatan di §2. "t/b" = tidak bermakna (basis mendekati nol).</p></div>

<h2 class="sec pb"><span class="n">4</span>Penyusutan: tanah &amp; gedung serta peralatan</h2>
<p class="lead">Penyusutan adalah pos biaya besar karena fasilitas ini relatif baru. Dua kelompok dibahas terpisah: tanah &amp; gedung (umur panjang, beban kecil) dan peralatan bengkel serta kantor (umur pendek, beban besar); angka ditelusuri dari nilai historis dan akumulasi penyusutan pada neraca unit.</p>
<div class="depbox">
 <div class="card"><h3>Tanah &amp; gedung</h3><div class="sub">Bangunan · Biaya Penyusutan Gedung · {"tanah tidak tercatat di unit" if not land_in_unit else "termasuk akun tanah di neraca unit"}</div>
  <div class="big">Rp {rp(S['dep_bldg'])} juta <span style="font-size:13px;color:var(--muted);font-weight:500">per bulan · {p0(S['dep_bldg']/S['dep'])} dari penyusutan</span></div>
  <div class="meter"><i style="width:{bldg_pct*100:.1f}%"></i></div>
  <div class="note">Gedung: harga perolehan Rp {rpbn(S['fa_bldg_cost'])} miliar, akumulasi Rp {rp(S['acc_bldg'])} juta ({p1(bldg_pct)} tersusutkan), nilai buku Rp {rpbn(S['nbv_bldg'])} miliar</div>
  <ul>
   {_land_li}
   <li><b>Gedung</b> Rp {rpbn(S['fa_bldg_cost'])} miliar disusutkan {p1(bldg_rate)} per tahun (umur {idn(bldg_life_y,0)} tahun): Rp {rp(S['dep_bldg'])} juta per bulan, Rp {rp(sum(M[m]['dep_bldg'] for m in YR))} juta {_ytd_since}, tersisa sekitar {idn(bldg_months_left/12,0)} tahun sampai {bldg_end}.</li>
   {_fa_li}
   {_ins_li}
  </ul></div>
 <div class="card"><h3>Peralatan</h3><div class="sub">Peralatan Bengkel dan Peralatan Kantor · tercatat di neraca unit</div>
  <div class="big">Rp {rp(dep_equipment)} juta <span style="font-size:13px;color:var(--muted);font-weight:500">per bulan · {p0(dep_equipment/S['dep'])} dari penyusutan</span></div>
  <div class="meter"><i style="width:{equip_pct*100:.1f}%"></i></div>
  <div class="note">Peralatan bengkel: harga perolehan Rp {rpbn(S['fa_equip_cost'])} miliar, akumulasi Rp {rpbn(S['acc_equip'])} miliar ({p1(equip_pct)} tersusutkan), nilai buku Rp {rpbn(S['nbv_equip'])} miliar</div>
  <ul>
   <li><b>Peralatan bengkel</b> (oven, booth cat, perkakas) Rp {rpbn(S['fa_equip_cost'])} miliar disusutkan {p0(equip_rate)} per tahun (umur {idn(equip_life_y,0)} tahun): Rp {rp(S['dep_equip'])} juta per bulan sampai {equip_end}, sisa {idn(equip_months_left,0)} bulan; {p0(S['dep_equip']/S['opex'])} dari opex dan {p0(S['dep_equip']/S['net_sales'])} dari pendapatan neto {NS}.</li>
   {_alt_li}
   {_office_li}
  </ul></div>
</div>
<div class="grid g2" style="margin-top:14px">
 <div class="card"><h3>Beban penyusutan per tahun, aktual dan proyeksi</h3><div class="sub">Rp juta · {Y0}* = {ID_MON[ym(ALL[0])[1]-1]}–{ID_MON[ym([m for m in ALL if m[:4]==str(Y0)][-1])[1]-1]} (sejak laporan pertama) · {YEAR} = aktual {mname(YR[0])}–{NS} + proyeksi sisa tahun · tahun berikutnya pada tarif saat ini, tanpa penambahan aset · peralatan habis mengikuti sisa nilai bukunya</div>{dep_year_chart(w=620, h=190)}{legend([('Peralatan bengkel', 'var(--s1)'), ('Gedung', 'var(--s2)'), ('Peralatan kantor', 'var(--s3)')])}</div>
 <div class="card"><h3>Jembatan laba rugi {NS}</h3><div class="sub">Rp juta · dari laba kotor ke laba (rugi) bersih · hijau menambah, merah mengurangi</div>{wf}</div>
</div>
<div class="callout" style="margin-top:14px"><b>Penyusutan adalah {p0(S['dep']/S['opex'])} dari opex dan {p0(S['dep']/S['net_sales'])} dari pendapatan neto.</b> Titik impas kas memerlukan penjualan bruto Rp {rp(cash_be_gross,0)} juta per bulan dan {_cash_note}; titik impas penuh memerlukan Rp {rp(be_gross_now,0)} juta ({idn(be_gross_now/S['sales'],2)} kali {NS}){_be_8y_txt.replace(', atau', ', atau').replace('ditinjau menjadi', 'disusutkan')}. Beban peralatan bengkel baru berakhir {equip_end}.</div>

<h2 class="sec pb"><span class="n">5</span>Neraca, modal kerja dan uji integritas</h2>
<div class="grid g2">
 <div class="card"><h3>Pendanaan unit, {NS}</h3><div class="sub">Rp {rpbn(fund_total)} miliar kewajiban dan pendanaan HO · komposisi</div>{segbar(fund_parts)}{legend([(n, c) for n, v, c in fund_parts])}
  <table style="margin-top:10px"><thead><tr><th></th><th class="num">{SHJ}</th><th class="num">{SHA}</th><th class="num">{SHS}</th></tr></thead><tbody>
  {tr_money('Kas dan bank', [J['cash'], A['cash'], S['cash']])}
  {tr_money('Piutang jasa', [J['ar'], A['ar'], S['ar']])}
  {tr_money('Hari penjualan bruto (DSO)', [J['dso'], A['dso'], S['dso']], fmt=lambda v: idn(v, 0))}
  {_ar_row}
  {tr_money('Persediaan suku cadang', [J['inv_parts'], A['inv_parts'], S['inv_parts']], cls='bold')}
  {tr_money('Persediaan bahan', [J['inv_bahan'], A['inv_bahan'], S['inv_bahan']])}
  </tbody></table></div>
 <div class="card"><h3>Kewajiban dan pendanaan</h3><div class="sub">Rp juta · neraca unit</div>
  <table><thead><tr><th></th><th class="num">{SHJ}</th><th class="num">{SHA}</th><th class="num">{SHS}</th></tr></thead><tbody>
  {tr_money('Uang muka pelanggan', [J['uang_muka'], A['uang_muka'], S['uang_muka']])}
  {tr_money('GR/IR suku cadang (diterima, belum ditagih)', [J['grir_parts'], A['grir_parts'], S['grir_parts']])}
  {tr_money('GR/IR bahan / pihak ketiga', [J['grir_bahan'], A['grir_bahan'], S['grir_bahan']])}
  {tr_money('Hutang HO', [J['hutang_ho'], A['hutang_ho'], S['hutang_ho']], cls='bold')}
  {tr_money('Pembukuan Pusat HO (pendanaan belanja modal)', [J['ho_clearing'], A['ho_clearing'], S['ho_clearing']])}
  {tr_money('Ekuitas unit', [J['equity'], A['equity'], S['equity']], bold=True)}
  </tbody></table>
  <p class="note" style="margin:8px 0 0">{_eq_note}</p></div>
</div>
<div class="card" style="margin-top:14px"><h3>Uji integritas</h3><div class="sub">Dijalankan pada setiap bulan dalam cakupan (neraca seimbang: ke belakang sampai {MLABEL[ALL[0]]}) · LOLOS atau PERHATIAN</div>
  <table><thead><tr><th style="width:38%">Pengujian</th><th style="width:10%">Hasil</th><th>Catatan</th></tr></thead><tbody>{integrity_html}</tbody></table>
  {f'<p class="note" style="margin:8px 0 0">{G_NOTE}</p>' if G_NOTE else ''}</div>

<h2 class="sec pb"><span class="n">6</span>Temuan, diurutkan menurut ukuran</h2>
<p class="lead">Setiap temuan dihitung dari data bulan ini; temuan yang tidak dapat dihitung dihilangkan. Urutan menurut nilai rupiah angka yang dibahas; tingkat keparahan menurut nilai itu terhadap pendapatan neto {NS} (TINGGI &ge; {p0(AN['severity_high_pct_of_net_sales'])}, SEDANG &ge; {p0(AN['severity_medium_pct_of_net_sales'])}).</p>
<div class="grid g2">{findings_html}</div>

<h2 class="sec pb"><span class="n">7</span>Rekomendasi: menjadikan Body &amp; Paint menguntungkan</h2>
<p class="lead">{'Biaya tunai sudah tertutup (EBITDA Rp ' + rp(S['ebitda']) + ' juta); yang belum tertutup adalah penyusutan Rp ' + rp(S['dep']) + ' juta per bulan.' if S['net'] < 0 and S['ebitda'] >= 0 else ('Unit sudah menutup seluruh biayanya; fokusnya menjaga margin dan volume.' if S['net'] >= 0 else 'Biaya tunai pun belum tertutup (EBITDA Rp (' + rp(-S['ebitda']) + ') juta); penyusutan Rp ' + rp(S['dep']) + ' juta per bulan menambah beban.')} Volume adalah tuas yang paling besar; tuas lainnya (bagi hasil, insentif, suku cadang, kas, umur aset) menjaga agar setiap rupiah volume tambahan benar-benar menjadi laba. Hanya rekomendasi yang angkanya dapat dihitung untuk bulan ini yang ditampilkan.</p>
<div class="grid g2">
 <div class="card"><h3>Jalan menuju laba, Rp juta per bulan</h3><div class="sub">Setiap langkah pada volume {NS} kecuali disebutkan · kumulatif pada kolom terakhir</div>
  <table><thead><tr><th>Langkah</th><th class="num">Efek</th><th class="num">Hasil bulanan</th></tr></thead><tbody>{path_html}</tbody></table>
  <p class="note" style="margin:8px 0 0">Langkah-langkah bersifat aditif dan merupakan pendekatan pada tingkat diskon {NS}; bukan proyeksi. Tambahan volume dihitung pada margin gabungan {NS} {p1(gm_now)} setelah diskon {p1(S['disc_rate'])}.{' Langkah terakhir non-kas dan bergantung pada pandangan auditor.' if ALT_OK else ''}</p></div>
 <div class="card"><h3>Perbandingan skenario</h3><div class="sub">Laba (rugi) bersih bulanan, Rp juta · A adalah {NS} sesuai laporan · MK = margin kotor</div>{scen_chart()}</div>
</div>
<div class="card" style="margin-top:14px"><h3>Asumsi dan hasil skenario</h3><div class="sub">Bulanan, Rp juta · tingkat diskon ditahan pada {p1(S['disc_rate'])} dari penjualan bruto di setiap skenario · opex tunai dianggap tetap kecuali disebutkan · asumsi dari config/targets.json{'' if TGT_OK else f' · skenario target tidak dibuat karena penjualan bruto {NS} sudah melampaui target Rp {rp(TGT,0)} juta'}</div>
  <table><thead><tr><th style="width:4%"></th><th>Skenario</th><th class="num">Penjualan bruto</th><th class="num">Margin kotor</th><th class="num">Opex</th><th class="num">Laba (rugi) bersih</th></tr></thead><tbody>{scen_rows}</tbody></table></div>
<div class="grid g2" style="margin-top:14px">{recs_html}</div>
<div class="card" style="margin-top:14px"><h3>Yang perlu dipantau setiap bulan mulai {NEXT_NAME}</h3><div class="sub">Kartu skor unit satu halaman, agar tinjauan berikutnya dapat menyatakan apakah rencana ini berjalan</div>
 <div class="grid g4">
  <div><b>Volume</b><div class="note">Unit masuk dan keluar · penjualan bruto per sumber (jasa ≥ Rp {rp(S['sales_jasa'],0)} juta) · rujukan dari serah terima unit dan bengkel umum · bauran asuransi vs pribadi</div></div>
  <div><b>Margin</b><div class="note">Margin kotor per sumber (jasa ≥ {p0(S['gm_jasa'])}, suku cadang ≥ {p0(A['gm_parts'])}) · tingkat diskon ≤ {p0(POL['discount_cap_of_gross_sales'])} · bagi hasil pihak ketiga per tingkatan · insentif sebagai % laba kotor</div></div>
  <div><b>Biaya</b><div class="note">Opex tunai ≤ Rp {rp(_cost_opex_cap,0)} juta · jam booth dan oven per minggu · kWh listrik per unit keluar · pos di atas Rp {rp(POL['approval_threshold'],0)} juta dengan persetujuan</div></div>
  <div><b>Neraca</b><div class="note">Umur piutang asuransi (tidak ada di atas {_dso_target} hari) · GR/IR dicocokkan tiap bulan · persediaan suku cadang tidak negatif · saldo HO sama di kedua pembukuan · kas ≤ 1 bulan opex tunai</div></div>
 </div></div>

<footer>Ruang lingkup dan dasar. Tinjauan ini mencakup Laporan Neraca dan Laba Rugi PT DCM Body Paint (sistem ACCURATE) untuk {', '.join(mname(m) for m in MONTHS[:-1])} dan {MLABEL[MS]}, dengan seluruh bulan sejak laporan pertama ({MLABEL[ALL[0]]}) dipakai untuk tren, angka tahun berjalan dan akumulasi rugi. Angka diekstraksi dengan skrip dari lapisan teks laporan dan direkonsiliasi: rincian akun terhadap subtotal laba rugi, neraca sampai ke rupiah, mutasi akumulasi penyusutan terhadap beban penyusutan, dan ekuitas terhadap laba rugi bulanan.{_dealer_scope} Dokumen ini adalah tinjauan analitis atas laporan manajemen, bukan audit, dan tidak memberikan opini asurans. Skenario adalah ilustrasi aritmetika pada asumsi yang dinyatakan (config/targets.json), bukan proyeksi. Tidak ada data operasional (jumlah unit, jam kerja, utilisasi booth) dalam laporan; angka-angka tersebut akan mempertajam tinjauan berikutnya.</footer>
</div></body></html>
"""

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
out = os.path.join(HERE, 'out', 'report.html')
open(out, 'w', encoding='utf-8').write(HTML)
_k = [EN_MON[ym(m)[1] - 1] for m in (MS, MA, MJ)]
_metrics = {_k[0]: S, _k[1]: A, _k[2]: J, f'ytd_{YEAR}': YTD, 'since_opening': INC,
            'depreciation': {'bldg_rate': bldg_rate, 'equip_rate': equip_rate, 'office_rate': office_rate, 'equip_months_left': equip_months_left, 'equip_end': equip_end,
                             'bldg_months_left': bldg_months_left, 'dep_equip_8y': dep_equip_8y, 'dep_saving_8y': dep_saving_8y, 'by_year': DEP_YEARS},
            'scenarios': [(c, n, g, gm, ox, net) for c, n, g, gm, ox, net, _ in SCEN_RES],
            'break_even': {'now_gross': be_gross_now, 'cash_gross': cash_be_gross, 'life8y_gross': be_gross_8y},
            'intercompany': ({'hutang_ho_unit': S['hutang_ho'], 'piutang_bp_at_ho': ho_recv_bp, 'gap': ic_gap, 'clearing_unit': S['ho_clearing'], 'clearing_ho': G['pembukuan_pusat_cabang_bp'], 'clearing_gap': clearing_gap} if G else None),
            'recon_exceptions': RECON}
json.dump(_metrics, open(os.path.join(HERE, 'out', 'metrics.json'), 'w'), indent=1, default=str)
print('wrote', out, len(HTML), 'bytes; month', CHOSEN, '| window', QLABEL, '| dealer data', 'dipakai' if G else 'TIDAK dipakai')
print(f"{NS} net {rp(S['net'])} | opex {rp(S['opex'])} | dep {rp(S['dep'])} | EBITDA {rp(S['ebitda'])} | BE now {rp(be_gross_now)} | BE alt {rp(be_gross_8y)} | cash BE {rp(cash_be_gross)} | equip end {equip_end}" + (f" | ic gap {rp(ic_gap)} | clearing gap {rp(clearing_gap)}" if G else ''))
for r in SCEN_RES:
    print(r[0], r[1], rp(r[5]))
print(f'{len(FINDINGS)} temuan:', ' | '.join(f"{f['sev']} {f['area']} ({rp(f['size'])})" for f in FINDINGS))
