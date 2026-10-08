"""
document_builder.py — Final Document Generator
==============================================

Mengambil data JSON hasil ekstraksi dari bot dan menyusunnya menjadi 
dokumen HTML yang kemudian dirender ke PDF. Dokumen final dijamin
sesuai dengan referensi layout standar (KAK_example.pdf), 
memperbaiki semua isu geometri, tipografi, struktur tabel, dan format nilai.
"""

import json
import os
import re
import math
from datetime import datetime, timedelta

# Path absolut ke gambar kop surat
KOP_SURAT_PATH = os.path.join(os.path.dirname(__file__), "kop_surat.jpg")

# -----------------------------------------------------------------------
# Helper Format: Tanggal, Angka, Rupiah
# -----------------------------------------------------------------------
NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NAMA_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
              "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
ROMAN_MONTH = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

def terbilang(n: int) -> str:
    """Mengubah angka menjadi teks bahasa Indonesia (untuk nominal & durasi)."""
    angka = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
    if n < 12: return angka[n]
    elif n < 20: return terbilang(n - 10) + " belas"
    elif n < 100: return terbilang(n // 10) + " puluh " + terbilang(n % 10)
    elif n < 200: return "seratus " + terbilang(n - 100)
    elif n < 1000: return terbilang(n // 100) + " ratus " + terbilang(n % 100)
    elif n < 2000: return "seribu " + terbilang(n - 1000)
    elif n < 1000000: return terbilang(n // 1000) + " ribu " + terbilang(n % 1000)
    elif n < 1000000000: return terbilang(n // 1000000) + " juta " + terbilang(n % 1000000)
    return str(n)

def format_rupiah(amount: int) -> str:
    """Format: Rp100.000.000 (seratus juta rupiah)"""
    if not amount: return "-"
    rupiah_str = f"Rp{amount:,}".replace(",", ".")
    terbilang_str = terbilang(amount).strip()
    return f"{rupiah_str} ({terbilang_str} rupiah)"

def format_durasi(days: int) -> str:
    """Format: 90 (sembilan puluh) hari kalender"""
    if not days: return "-"
    return f"{days} ({terbilang(days).strip()}) hari kalender"

def format_indo_date(dt: datetime) -> str:
    """Format: Senin, 4 Mei 2026 (Never locale-dependent)"""
    return f"{NAMA_HARI[dt.weekday()]}, {dt.day} {NAMA_BULAN[dt.month]} {dt.year}"

def clean_text(text) -> str:
    """Fallback ke '-' jika None/kosong."""
    if text is None or str(text).strip() == "" or str(text).strip().lower() == "none":
        return "-"
    return str(text).replace("&", "&amp;")

def parse_items(items_data):
    """Memastikan list items berbentuk array python, bukan string hyphen."""
    if isinstance(items_data, list):
        return [clean_text(i) for i in items_data]
    if isinstance(items_data, str):
        # Split jika string berupa teks multi-line bullet
        lines = [line.lstrip('-•').strip() for line in items_data.split('<br>') if line.strip()]
        if not lines:
            lines = [line.lstrip('-•').strip() for line in items_data.split('\n') if line.strip()]
        return lines if lines else [clean_text(items_data)]
    return []

# -----------------------------------------------------------------------
# HTML Generator Khusus Xhtml2pdf
# -----------------------------------------------------------------------

def render_paragraphs(text: str) -> str:
    """Pecah paragraf & set class 'last' pada paragraf terakhir (mencegah dead space)."""
    if not text or text == "-": return '<p class="last">-</p>'
    paragraphs = [p.strip() for p in str(text).split('\n') if p.strip()]
    if not paragraphs: return '<p class="last">-</p>'
    
    html = ""
    for i, p in enumerate(paragraphs):
        cls = ' class="last"' if i == len(paragraphs) - 1 else ''
        html += f'<p{cls}>{p}</p>'
    return html

def render_list(items, marker_type="1)", tight=True, start_idx=0) -> str:
    """Render structured list dengan indentasi hanging tanpa dead space bawah."""
    if not items: return '<p class="last">-</p>'
    spacing_class = "tight" if tight else "loose"
    html = f'<table class="list-table {spacing_class}">'
    for i, item in enumerate(items):
        idx = start_idx + i
        if marker_type == "1)": marker = f"{idx+1})"
        elif marker_type == "a)": marker = f"{chr(97+idx)})"
        else: marker = "-"
        
        # Bersihkan dead space <p> di dalam list text
        item_text = str(item)
        if item_text.endswith("</p>"): 
            item_text = item_text[:-4] + "</p>".replace("</p>", "")
            
        html += f'<tr><td class="list-marker">{marker}</td><td class="list-spacer"></td><td class="list-text"><p class="last">{item_text}</p></td></tr>'
    html += '</table>'
    return html

def generate_gantt_chart(start_date: datetime, n_days: int) -> str:
    """Merender Row 14: 15-column Gantt table."""
    months_count = max(3, math.ceil(n_days / 30))
    cols_total = months_count * 4
    days_per_col = n_days / cols_total
    
    # Calculate markers
    col_pendahuluan = min(cols_total, math.ceil(30 / days_per_col))
    col_antara = min(cols_total, math.ceil(60 / days_per_col))
    col_akhir = cols_total
    
    # Build Month Headers
    month_headers = ""
    current_month = start_date.month
    for i in range(months_count):
        m_idx = ((current_month - 1 + i) % 12) + 1
        month_headers += f'<th colspan="4">{NAMA_BULAN[m_idx].upper()}</th>'
        
    week_headers = "<th>I</th><th>II</th><th>III</th><th>IV</th>" * months_count
    
    # Shading Rows Helper
    def render_body_row(no, kegiatan, shade_start, shade_end, ket=""):
        row_html = f'<tr><td class="gantt-no">{no}</td><td class="gantt-keg">{kegiatan}</td>'
        for i in range(1, cols_total + 1):
            shade_cls = ' class="shade"' if shade_start <= i <= shade_end else ''
            row_html += f'<td{shade_cls}></td>'
        row_html += f'<td class="gantt-ket">{ket}</td></tr>'
        return row_html
    
    html = f'''
    <table class="gantt">
        <tr>
            <th rowspan="2" class="gantt-no-hdr">No</th>
            <th rowspan="2" class="gantt-keg-hdr">Kegiatan</th>
            {month_headers}
            <th rowspan="2" class="gantt-ket-hdr">KET</th>
        </tr>
        <tr>{week_headers}</tr>
        {render_body_row("1", "Penandatanganan<br>Kontrak", 1, 1)}
        {render_body_row("2", "Pelaksanaan Pekerjaan", 1, cols_total)}
        {render_body_row("", "- Laporan Pendahuluan", col_pendahuluan, col_pendahuluan, "30 Hari")}
        {render_body_row("", "- Laporan Antara", col_antara, col_antara, "60 Hari")}
        {render_body_row("", "- Laporan Akhir", col_akhir, col_akhir, f"{n_days} Hari")}
        {render_body_row("3", "Serah Terima Pekerjaan", col_akhir, col_akhir, f"{n_days} Hari")}
    </table>
    '''
    
    # Footnotes
    end_date = start_date + timedelta(days=n_days - 1)
    
    html += f'<p class="footnote" style="margin-top: 5pt;">*Mulai pada {format_indo_date(start_date)}</p>'
    html += f'<p class="footnote">*Batas Akhir ({n_days} hari) adalah {format_indo_date(end_date)}.</p>'
    
    if end_date.weekday() >= 5: # Sabtu atau Minggu
        days_to_sub = end_date.weekday() - 4
        tgl_jumat = end_date - timedelta(days=days_to_sub)
        n_jumat = n_days - days_to_sub
        
        html += f'<p class="footnote">*Serah Terima Pekerjaan: Karena {end_date.day} {NAMA_BULAN[end_date.month]} adalah hari {NAMA_HARI[end_date.weekday()]}, '
        html += f'Anda dapat memajukan serah terima menjadi Jumat, {tgl_jumat.day} {NAMA_BULAN[tgl_jumat.month]} {tgl_jumat.year} (berjalan {n_jumat} hari). '
        html += f'Hal ini diperbolehkan karena {n_days} hari adalah batas maksimal penyelesaian, dan ini sangat sejajar dengan arsiran minggu keempat bulan {NAMA_BULAN[end_date.month]}.</p>'

    return html

def generate_html_from_json(json_filepath: str) -> tuple[str, str]:
    """Menyusun JSON input menjadi dokumen HTML yang disesuaikan ketat untuk xhtml2pdf."""
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    meta = data.get("metadata", {})
    kak = data.get("kak", {})
    
    # Parsing values
    raw_paket = meta.get("judul_pekerjaan", "PEKERJAAN TIDAK DIKETAHUI")
    paket = re.sub(r'(?i)^BELANJA\s+JASA\s+KONSULTANSI\s+', '', raw_paket).strip()
    
    tipe_desc = meta.get("deskripsi_tipe", "JASA KONSULTANSI").upper()
    tahun = meta.get("tahun_anggaran", datetime.now().year)
    pagu = int(kak.get("sumber_pendanaan", {}).get("pagu_anggaran", 0))
    n_days = int(kak.get("waktu_pelaksanaan", {}).get("durasi_hari", 90))
    
    # Set Start Date (Default 4 Mei 2026 based on Golden Test, or user input if provided)
    start_date_str = kak.get("jadwal_pelaksanaan_mulai", "2026-05-04")
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        start_date = datetime(2026, 5, 4)

    # Base HTML Structure
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>KAK {paket.title()}</title>
        <style>
            @page {{
                size: 612pt 936pt;
                margin: 73pt 71pt 73pt 73pt;
            }}
            /* Fonts: Menggunakan metrik Times New Roman/Liberation Serif (base-14 standard mapping in xhtml2pdf) */
            body {{
                font-family: "Times New Roman", "Liberation Serif", serif;
                font-size: 11pt;
                line-height: 19pt;
                color: #000;
            }}
            p {{
                margin: 0;
                text-align: justify;
            }}
            p.last {{
                margin-bottom: 0;
            }}
            
            /* Cover Styles */
            img.letterhead {{
                width: 468pt;
                height: 151pt;
                margin-bottom: 48pt;
            }}
            .cover-title, .cover-title p {{
                text-align: center;
                font-weight: bold;
                font-size: 12pt;
                line-height: 14pt;
                text-transform: uppercase;
            }}
            .cover-nomor, .cover-nomor p {{
                text-align: center;
                font-weight: bold;
                font-size: 13pt;
                margin-top: 40pt;
                margin-bottom: 40pt;
            }}
            table.meta-table {{
                border-collapse: collapse;
                width: 468pt;
                font-size: 12pt;
                font-weight: bold;
                line-height: 14pt;
                text-transform: uppercase;
            }}
            table.meta-table td {{
                padding: 4pt 0 7pt 4pt; /* row spacing approx 11pt between baselines */
                vertical-align: top;
            }}
            .meta-lbl {{ width: 96pt; }}
            .meta-col {{ width: 15pt; }}
            .meta-val {{ width: 357pt; text-align: justify; }}
            
            .cover-bottom, .cover-bottom p {{
                text-align: center;
                font-weight: bold;
                font-size: 13pt;
                margin-top: 50pt;
            }}
            
            /* Main 17 Row Table */
            table.main {{
                width: 468pt;
                border-collapse: collapse;
            }}
            table.main td {{
                border: 0.75pt solid #000;
                vertical-align: top;
                padding: 4pt 6pt 4pt 5pt;
            }}
            td.col-no {{ width: 33pt; font-weight: bold; text-align: right; }}
            td.col-lbl {{ width: 126pt; font-weight: bold; text-align: left; }}
            td.col-body {{ width: 309pt; text-align: justify; }}
            
            /* Nested Lists */
            table.list-table {{ width: 100%; border: none; padding: 0; margin: 0; border-collapse: collapse; }}
            table.list-table td {{ border: none; padding: 0; vertical-align: top; }}
            table.list-table.tight td {{ padding-bottom: 0pt; }}
            table.list-table.loose td {{ padding-bottom: 0pt; }}
            td.list-marker {{ width: 16pt; text-align: right; }}
            td.list-spacer {{ width: 6pt; }}
            td.list-text {{ width: 274pt; text-align: justify; }}
            
            /* Row 13: Personnel */
            table.personnel {{
                width: 295pt;
                border-collapse: collapse;
                font-size: 9pt;
                line-height: 11pt;
                margin-top: 17pt;
            }}
            table.personnel th, table.personnel td {{
                border: 0.5pt solid #000;
                vertical-align: top;
                padding: 3pt;
            }}
            table.personnel th {{ font-weight: bold; text-align: center; vertical-align: middle; }}
            
            /* Row 14: Gantt */
            table.gantt {{
                width: 454pt;
                border-collapse: collapse;
                font-size: 8pt;
                line-height: 10pt;
                margin-left: 5pt;
                margin-bottom: 5pt;
            }}
            table.gantt th, table.gantt td {{ border: 0.5pt solid #000; vertical-align: top; padding: 2pt; text-align: left; }}
            table.gantt th {{ text-align: center; vertical-align: middle; }}
            th.gantt-no-hdr {{ width: 21pt; }} th.gantt-keg-hdr {{ width: 87pt; }} th.gantt-ket-hdr {{ width: 40pt; font-size: 7.5pt; }}
            td.gantt-no {{ width: 21pt; }} td.gantt-keg {{ width: 87pt; }} td.gantt-ket {{ width: 40pt; font-size: 7.5pt; text-align: center; }}
            td.shade {{ background-color: #B7B7B7; }}
            
            .footnote {{ font-size: 9pt; line-height: 10.3pt; text-align: justify; margin: 0; margin-left: 9.5pt; margin-right: 13pt; }}
        </style>
    </head>
    <body>
    """

    # 1. Cover
    doc_month = ROMAN_MONTH[datetime.now().month]
    doc_year = datetime.now().year
    doc_number = f"004/KAK-KAJIAN-04/{doc_month}/{doc_year}"
    
    html += f'<div style="text-align:center;"><img class="letterhead" src="{KOP_SURAT_PATH.replace(os.sep, "/")}" /><br><br><br></div>'
    html += f'<div class="cover-title"><p class="last">KERANGKA ACUAN KERJA (KAK)<br><br>{tipe_desc}<br><br>{paket.upper()}<br><br>KOTA YOGYAKARTA</p></div>'
    html += f'<div class="cover-nomor"><p class="last">Nomor : {doc_number}</p></div>'
    
    html += f'''
    <table class="meta-table">
        <tr><td class="meta-lbl">KEGIATAN</td><td class="meta-col">:</td><td class="meta-val">KEGIATAN PENGELOLAAN PENDAPATAN DAERAH</td></tr>
        <tr><td class="meta-lbl">SUB<br>KEGIATAN</td><td class="meta-col">:</td><td class="meta-val">ANALISA DAN PENGEMBANGAN PAJAK DAERAH, SERTA PENYUSUNAN KEBIJAKAN PAJAK DAERAH</td></tr>
        <tr><td class="meta-lbl">PEKERJAAN</td><td class="meta-col">:</td><td class="meta-val">BELANJA JASA KONSULTANSI KAJIAN PENDAPATAN ASLI DAERAH (JASA KONSULTANSI {paket.upper()})</td></tr>
        <tr><td class="meta-lbl">PAKET</td><td class="meta-col">:</td><td class="meta-val">{paket.upper()}</td></tr>
        <tr><td class="meta-lbl">NO DPA</td><td class="meta-col">:</td><td class="meta-val">DPA/A.1/5.02.0.00.0.00.01.0000/001/2026</td></tr>
    </table>
    '''
    html += f'<div class="cover-bottom"><p class="last">TAHUN ANGGARAN {tahun}</p></div>'
    html += '<pdf:nextpage />'
    
    # 2. Main Table
    html += '<table class="main">'
    
    # Row 1
    html += f'<tr><td class="col-no">1.</td><td class="col-lbl">Latar Belakang</td><td class="col-body">{render_paragraphs(clean_text(kak.get("latar_belakang")))}</td></tr>'
    
    # Row 2
    maksud_text = clean_text(kak.get("maksud"))
    tujuan_list = render_list(parse_items(kak.get("tujuan")), marker_type="a)", tight=True)
    html += f'<tr><td class="col-no">2.</td><td class="col-lbl">Maksud dan Tujuan</td><td class="col-body">'
    html += f'<table class="list-table tight"><tr><td class="list-marker">1)</td><td class="list-spacer"></td><td class="list-text"><p>Maksud</p><p class="last">{maksud_text}</p></td></tr>'
    html += f'<tr><td class="list-marker">2)</td><td class="list-spacer"></td><td class="list-text"><p>Tujuan</p>{tujuan_list}</td></tr></table>'
    html += '</td></tr>'
    
    # Row 3
    sasaran_items = parse_items(kak.get("sasaran"))
    sasaran_html = render_list(sasaran_items, tight=True) if len(sasaran_items) > 1 else render_paragraphs(sasaran_items[0] if sasaran_items else "-")
    html += f'<tr><td class="col-no">3.</td><td class="col-lbl">Sasaran</td><td class="col-body">{sasaran_html}</td></tr>'
    
    # Row 4
    html += f'<tr><td class="col-no">4.</td><td class="col-lbl">Lokasi Kegiatan</td><td class="col-body"><p class="last">Pekerjaan ini berlokasi di {clean_text(kak.get("lokasi_kegiatan", "Kota Yogyakarta"))}</p></td></tr>'
    
    # Row 5
    p5_1 = f"Kegiatan ini dibiayai dari sumber pendanaan Anggaran Pendapatan dan Belanja Daerah (APBD) Pemerintah Kota Yogyakarta Tahun Anggaran {tahun}."
    p5_2 = f"Total Perkiraan biaya yang diperlukan paling banyak {format_rupiah(pagu)}, sudah termasuk PPN 11%."
    html += f'<tr><td class="col-no">5.</td><td class="col-lbl">Sumber Pendanaan dan Perkiraan Biaya</td><td class="col-body">{render_list([p5_1, p5_2], tight=True)}</td></tr>'
    
    # Row 6
    ruang_list = render_list(parse_items(kak.get("ruang_lingkup")), tight=True)
    html += f'<tr><td class="col-no">6.</td><td class="col-lbl">Ruang Lingkup, Lokasi Pekerjaan, Fasilitas Penunjang</td><td class="col-body">'
    html += f'<p>Ruang Lingkup Pekerjaan:</p>{ruang_list}'
    html += f'<p class="last">Lokasi Pekerjaan: {clean_text(kak.get("lokasi_kegiatan", "Kota Yogyakarta"))}<br>Fasilitas Penunjang: {clean_text(kak.get("fasilitas_penunjang", "ruang rapat BPKAD Kota Yogyakarta"))}</p>'
    html += '</td></tr>'
    
    # Row 7
    hasil_list = render_list(parse_items(kak.get("output_keluaran")), tight=True)
    html += f'<tr><td class="col-no">7.</td><td class="col-lbl">Hasil Produk</td><td class="col-body">{hasil_list}</td></tr>'
    
    # Row 8
    html += f'<tr><td class="col-no">8.</td><td class="col-lbl">Waktu Pelaksanaan</td><td class="col-body"><p class="last">Durasi pekerjaan adalah {format_durasi(n_days)} sejak SPMK.</p></td></tr>'
    
    # Row 9 (Metodologi)
    metodologi = clean_text(kak.get("metodologi"))
    # Jika input sederhana, taruh di paragraf pembuka. Jika butuh parse kompleks, sesuaikan.
    html += f'<tr><td class="col-no">9.</td><td class="col-lbl">Pendekatan dan Metodologi</td><td class="col-body">'
    html += f'<p>Pekerjaan ini akan menggunakan beberapa pendekatan untuk dapat menghasilkan produk yang diharapkan.</p>'
    html += f'<table class="list-table tight"><tr><td class="list-marker">1)</td><td class="list-spacer"></td><td class="list-text"><p>Pendekatan Metodologi:</p>{render_list(parse_items(metodologi), marker_type="a)", tight=True)}</td></tr></table>'
    html += '</td></tr>'
    
    # Row 10
    spek_list = render_list(parse_items(kak.get("spesifikasi_teknis")), tight=True)
    html += f'<tr><td class="col-no">10.</td><td class="col-lbl">Spesifikasi Teknis</td><td class="col-body">{spek_list}</td></tr>'
    
    # Row 11
    alat_list = render_list(parse_items(kak.get("peralatan_material", ["Laptop dan printer dan peralatan kerja lainnya.", "Alat transportasi."])), tight=True)
    html += f'<tr><td class="col-no">11.</td><td class="col-lbl">Peralatan dan Material</td><td class="col-body">{alat_list}</td></tr>'
    
    # Row 12
    html += f'<tr><td class="col-no">12.</td><td class="col-lbl">Jangka Waktu Penyelesaian Pekerjaan</td><td class="col-body"><p class="last">Jangka waktu penyelesaian pekerjaan {paket.title()} adalah {format_durasi(n_days)} terhitung sejak ditandatanganinya Surat Perjanjian Kontrak (SPK).</p></td></tr>'
    
    # Row 13 (Kebutuhan Personil)
    personil_data = kak.get("kebutuhan_personil", [])
    if personil_data:
        p_html = '<table class="personnel"><tr><th style="width:25pt;">No</th><th style="width:68pt;">Posisi</th><th style="width:46pt;">Jumlah<br>Tenaga Ahli</th><th style="width:91pt;">Kualifikasi<br>Pendidikan Minimal</th><th style="width:65pt;">Pengalaman<br>Minimal (Tahun)</th></tr>'
        for idx, p in enumerate(personil_data):
            posisi = clean_text(p.get("posisi"))
            jumlah = str(p.get("jumlah", "-")).replace("Orang", "").replace("orang", "").strip()
            kual = clean_text(p.get("kualifikasi_pendidikan")).replace("/", "/ ")
            pengalaman = str(p.get("pengalaman_tahun", "-")).lower().replace("th", "").replace("tahun", "").strip()
            p_html += f'<tr><td>{idx+1}</td><td>{posisi}</td><td style="text-align:center;">{jumlah}</td><td style="text-align:center;">{kual}</td><td style="text-align:center;">{pengalaman}</td></tr>'
        p_html += '</table>'
    else:
        p_html = '<p class="last">-</p>'
        
    html += f'<tr><td class="col-no">13.</td><td class="col-lbl">Kebutuhan Personil</td><td class="col-body">'
    html += f'<p class="last">Untuk melaksanakan Pekerjaan ini, personil yang dibutuhkan adalah sebagai berikut:</p>{p_html}'
    html += '</td></tr>'
    
    # Row 14 (Jadwal Gantt)
    html += f'<tr style="page-break-inside: avoid;"><td class="col-no">14.</td><td class="col-lbl">Jadwal Pelaksanaan Pekerjaan</td><td class="col-body"><p class="last">Waktu yang dibutuhkan untuk menyelesaikan pekerjaan adalah {format_durasi(n_days)} dengan Jadwal Rencana Pelaksanaan Kegiatan pada tabel berikut :</p></td></tr>'
    html += f'<tr style="page-break-inside: avoid;"><td colspan="3" style="padding-top: 10pt;">{generate_gantt_chart(start_date, n_days)}</td></tr>'
    
    # Row 15
    laporan_items = parse_items(kak.get("laporan_akhir", ["Ringkasan Eksekutif", "Dasar Hukum", "Metodologi", "Studi Literatur", "Kesimpulan dan Rekomendasi", "Lampiran data pendukung"]))
    html += f'<tr><td class="col-no">15.</td><td class="col-lbl">Laporan Akhir</td><td class="col-body"><p>Laporan akhir sekurang-kurangnya memuat substansi sebagai berikut:</p>{render_list(laporan_items, tight=True)}</td></tr>'
    
    # Row 16
    pengumpulan_items = parse_items(kak.get("pedoman_pengumpulan_data", ["menjaga kerahasiaan data dan informasi pelaksanaan pekerjaan;", "berkoordinasi dengan Pemerintah Kota Yogyakarta sebelum, pada saat dan setelah melakukan pengumpulan data lapangan; dan", "dilarang menyebarluaskan data dan informasi yang diperoleh selama pelaksanaan pekerjaan kepada pihak manapun."]))
    html += f'<tr><td class="col-no">16.</td><td class="col-lbl">Pedoman Pengumpulan Data Lapangan</td><td class="col-body"><p>Pengumpulan data harus memenuhi persyaratan berikut:</p>{render_list(pengumpulan_items, tight=True)}</td></tr>'
    
    # Row 17
    alih_items = parse_items(kak.get("alih_pengetahuan", ["Seluruh data, metode dan kekayaan intelektual yang dihasilkan dalam proses pekerjaan ini menjadi milik Pemerintah Kota Yogyakarta.", "Pelatihan atau berbagai bentuk penyebarluasan informasi dan pengetahuan yang dihasilkan dari pelaksanaan pekerjaan ini harus memperoleh izin dan melibatkan Pemerintah Kota Yogyakarta."]))
    html += f'<tr><td class="col-no">17.</td><td class="col-lbl">Alih Pengetahuan</td><td class="col-body">{render_list(alih_items, tight=True)}</td></tr>'
    
    html += '</table></body></html>'
    
    # Format Nama File Output
    safe_title = "".join(c if c.isalnum() else "_" for c in raw_paket)
    safe_title = re.sub(r"_+", "_", safe_title).strip("_")[:40]
    
    timestamp = datetime.now().strftime('%d-%m-%Y_%H%M%S')
    base_out_name = f"KAK_{safe_title}_{timestamp}"
    session_folder_name = f"{timestamp}_{safe_title}"
    
    folder_arsip = os.path.join(os.path.dirname(__file__), "Arsip KAK", str(tahun), NAMA_BULAN[datetime.now().month], session_folder_name)
    os.makedirs(folder_arsip, exist_ok=True)
    
    base_filepath = os.path.join(folder_arsip, base_out_name)
    return html, base_filepath

def generate_pdf_from_html(html_text: str, base_filepath: str) -> str | None:
    """Merender HTML KAK langsung ke PDF menggunakan xhtml2pdf untuk kontrol pixel-perfect."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        print("⚠️ Library 'xhtml2pdf' tidak ditemukan.")
        print("   Silakan jalankan: pip install xhtml2pdf")
        return None

    pdf_filepath = base_filepath + ".pdf"
    with open(pdf_filepath, "wb") as result_file:
        pisa_status = pisa.CreatePDF(
            src=html_text,
            dest=result_file,
            encoding='utf-8'
        )

    if pisa_status.err:
        print(f"⚠️ Terjadi error saat membuat PDF: {pisa_status.err}")
        return None
        
    return pdf_filepath


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        html_text, base_path = generate_html_from_json(json_file)
        out_pdf = generate_pdf_from_html(html_text, base_path)
        if out_pdf:
            print(f"File PDF KAK berhasil dibuat: {out_pdf}")
    else:
        print("Penggunaan: python document_builder.py <path_ke_file.json>")
