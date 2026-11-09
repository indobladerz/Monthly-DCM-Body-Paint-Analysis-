#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the compact, Gmail-safe e-mail for the monthly Body Paint review.

  python3 render_email.py            # reads out/email_data.json (written by build_report.py)

Writes out/email.html (table layout, inline styles only: no <style> block, no var(), no flex/grid, no images, no SVG)
and out/email_subject.txt. Every figure comes pre-formatted from build_report.py; this script only lays it out and
escapes it. The last line of email.html is a sentinel `<!-- dcm-bp v1 YYYY-MM <hash> -->`: the scheduled run sends the
file's exact, complete contents as the HTML body, and a body whose last line is not that sentinel is not the report.
Gmail clips messages over ~102 KB, so the script refuses to write anything over 95,000 bytes.
"""
import hashlib, html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 95000
SEV = {'TINGGI': '#d03b3b', 'SEDANG': '#ec835a', 'RENDAH': '#fab219'}
FONT = "font-family:Arial,Helvetica,sans-serif;"


def e(s):
    return html.escape(str(s))


def main():
    d = json.load(open(os.path.join(HERE, 'out', 'email_data.json'), encoding='utf-8'))
    J, A, S = d['labels']
    out = []
    w = out.append
    w('<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      f'<title>{e(d["subject"])}</title></head>')
    w(f'<body style="margin:0;padding:0;background:#f1f0ec;{FONT}color:#1a1a1a;">')
    w('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f0ec;"><tr><td align="center" style="padding:16px 8px;">')
    w('<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:640px;background:#ffffff;">')

    # header
    w(f'<tr><td style="background:#a8191a;padding:24px 28px;{FONT}color:#ffffff;">'
      f'<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#f3d3d1;">PT DCM Body Paint</div>'
      f'<div style="font-size:26px;line-height:1.2;font-weight:bold;margin-top:6px;color:#ffffff;">Tinjauan Keuangan, {e(d["month_label"])}</div>'
      f'<div style="font-size:13px;margin-top:8px;color:#f3d3d1;">Tinjauan tiga bulan {e(d["window_label"])} &middot; Rp juta, angka negatif dalam kurung</div></td></tr>')

    # KPI 2x2
    k = d['kpis']
    def kpi(c):
        return (f'<td width="50%" valign="top" style="padding:12px 14px;border:1px solid #e1e0d9;{FONT}">'
                f'<div style="font-size:11px;color:#6b6a66;text-transform:uppercase;letter-spacing:1px;">{e(c["label"])}</div>'
                f'<div style="font-size:22px;font-weight:bold;margin-top:4px;color:#0b0b0b;">{e(c["value"])}</div>'
                f'<div style="font-size:12px;color:#52514e;margin-top:2px;">{e(c["sub"])}</div></td>')
    w('<tr><td style="padding:18px 28px 6px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">')
    for i in range(0, len(k), 2):
        w('<tr>' + ''.join(kpi(c) for c in k[i:i + 2]) + '</tr>')
    w('</table></td></tr>')

    # 3-month table
    w(f'<tr><td style="padding:18px 28px 0;{FONT}"><div style="font-size:16px;font-weight:bold;margin-bottom:8px;">Ringkasan tiga bulan</div>'
      '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;font-size:13px;">'
      f'<tr style="background:#f1f0ec;"><td style="padding:7px 8px;font-weight:bold;">Pos</td>'
      + ''.join(f'<td align="right" style="padding:7px 8px;font-weight:bold;">{e(x)}</td>' for x in (J, A, S)) + '</tr>')
    bold = {'Laba kotor', 'EBITDA', 'Laba (rugi) bersih'}
    for r in d['rows']:
        b = 'font-weight:bold;' if r['label'] in bold else ''
        w(f'<tr><td style="padding:6px 8px;border-top:1px solid #e1e0d9;{b}">{e(r["label"])}</td>'
          + ''.join(f'<td align="right" style="padding:6px 8px;border-top:1px solid #e1e0d9;{b}">{e(v)}</td>' for v in r['values']) + '</tr>')
    w('</table></td></tr>')

    # findings
    if d['findings']:
        w(f'<tr><td style="padding:22px 28px 0;{FONT}"><div style="font-size:16px;font-weight:bold;margin-bottom:4px;">Temuan utama</div>'
          '<div style="font-size:12px;color:#6b6a66;margin-bottom:8px;">Dihitung dari data bulan ini dan diurutkan menurut nilai rupiah angka yang dibahas.</div></td></tr>')
        for i, f in enumerate(d['findings'], 1):
            col = SEV.get(f['sev'], '#898781')
            fg = '#0b0b0b' if f['sev'] == 'RENDAH' else '#ffffff'
            w('<tr><td style="padding:0 28px 10px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #e1e0d9;"><tr>'
              f'<td width="6" style="background:{col};font-size:0;line-height:0;">&nbsp;</td>'
              f'<td style="padding:10px 12px;{FONT}">'
              f'<div style="font-size:11px;"><span style="background:{col};color:{fg};font-weight:bold;padding:2px 8px;">{e(f["sev"])}</span>'
              f' <span style="color:#6b6a66;">{e(f["area"])} &middot; Temuan {i}</span></div>'
              f'<div style="font-size:14px;font-weight:bold;margin-top:6px;">{e(f["title"])}</div>'
              f'<div style="font-size:13px;line-height:1.45;margin-top:4px;color:#2b2a28;">{e(f["body"])}</div>'
              f'<div style="font-size:11px;color:#898781;margin-top:5px;">Sumber: {e(f["evidence"])}</div></td></tr></table></td></tr>')

    # recommendations
    if d['recs']:
        w(f'<tr><td style="padding:14px 28px 0;{FONT}"><div style="font-size:16px;font-weight:bold;margin-bottom:8px;">Rekomendasi</div></td></tr>')
        for i, r in enumerate(d['recs'], 1):
            w(f'<tr><td style="padding:0 28px 10px;{FONT}"><div style="font-size:14px;font-weight:bold;">{i}. {e(r["title"])}</div>'
              f'<div style="font-size:13px;line-height:1.45;margin-top:3px;color:#2b2a28;">{e(r["body"])}</div>'
              f'<div style="font-size:12px;color:#52514e;margin-top:3px;">{e(r["impact"])}</div></td></tr>')

    # scenarios
    if d['scenarios']:
        w(f'<tr><td style="padding:14px 28px 0;{FONT}"><div style="font-size:16px;font-weight:bold;margin-bottom:8px;">Skenario (ilustrasi aritmetika, bukan proyeksi)</div>'
          '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;font-size:12px;">'
          '<tr style="background:#f1f0ec;"><td style="padding:6px 6px;font-weight:bold;">Skenario</td><td align="right" style="padding:6px 6px;font-weight:bold;">Penjualan bruto</td>'
          '<td align="right" style="padding:6px 6px;font-weight:bold;">Margin kotor</td><td align="right" style="padding:6px 6px;font-weight:bold;">Opex</td>'
          '<td align="right" style="padding:6px 6px;font-weight:bold;">Laba (rugi) bersih</td></tr>')
        for s in d['scenarios']:
            w(f'<tr><td style="padding:6px 6px;border-top:1px solid #e1e0d9;">{e(s["code"])}. {e(s["name"])}</td>'
              f'<td align="right" style="padding:6px 6px;border-top:1px solid #e1e0d9;">{e(s["gross"])}</td>'
              f'<td align="right" style="padding:6px 6px;border-top:1px solid #e1e0d9;">{e(s["gm"])}</td>'
              f'<td align="right" style="padding:6px 6px;border-top:1px solid #e1e0d9;">{e(s["opex"])}</td>'
              f'<td align="right" style="padding:6px 6px;border-top:1px solid #e1e0d9;font-weight:bold;">{e(s["net"])}</td></tr>')
        w('</table></td></tr>')

    # integrity
    ok = [x for x in d['integrity'] if x['ok']]
    bad = [x for x in d['integrity'] if not x['ok']]
    line = f'Uji integritas: {len(ok)} lolos' + (f', {len(bad)} perlu perhatian' if bad else ', tidak ada yang perlu perhatian') + '.'
    w(f'<tr><td style="padding:16px 28px 0;{FONT}font-size:13px;"><b>{e(line)}</b>')
    if bad:
        w('<ul style="margin:6px 0 0;padding-left:18px;">' + ''.join(f'<li>{e(x["name"])}</li>' for x in bad) + '</ul>')
    w('</td></tr>')

    # footer
    dealer = '' if d['dealer_data_used'] else ' Data dealer utama untuk bulan ini tidak dipakai, sehingga bagian antarperusahaan dihilangkan.'
    w(f'<tr><td style="padding:18px 28px 24px;{FONT}font-size:11px;line-height:1.45;color:#898781;">'
      'Ringkasan otomatis dari Laporan Neraca dan Laba Rugi PT DCM Body Paint (ACCURATE). Angka diekstraksi dengan skrip dan direkonsiliasi sampai ke rupiah. '
      'Ini tinjauan analitis atas laporan manajemen, bukan audit.' + e(dealer) + ' Versi lengkap dengan grafik tersedia atas permintaan.</td></tr>')
    w('</table></td></tr></table></body></html>')

    body = '\n'.join(out)
    for bad_token in ('var(', '<svg', 'data:', '<style', '<script', 'display:flex', 'display:grid'):
        assert bad_token not in body, f'email must not contain {bad_token!r}'
    for f in d['findings']:
        assert e(f['title']) in body, 'finding missing from e-mail'
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
    final = f'{body}\n<!-- dcm-bp v1 {d["period"]} {digest} -->\n'
    size = len(final.encode('utf-8'))
    if size > MAX_BYTES:
        sys.exit(f'email.html would be {size} bytes (> {MAX_BYTES}); Gmail would clip it. Not written.')
    open(os.path.join(HERE, 'out', 'email.html'), 'w', encoding='utf-8').write(final)
    open(os.path.join(HERE, 'out', 'email_subject.txt'), 'w', encoding='utf-8').write(d['subject'] + '\n')
    print(f'wrote out/email.html {size} bytes | {len(d["findings"])} findings, {len(d["recs"])} recs | subject: {d["subject"]}')
    print(f'sentinel: <!-- dcm-bp v1 {d["period"]} {digest} -->')


if __name__ == '__main__':
    main()
