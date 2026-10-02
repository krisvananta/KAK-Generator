"""
document_builder.py — Final Document Generator
==============================================

Mengambil data JSON hasil ekstraksi dari bot dan menyusunnya menjadi 
dokumen Markdown final (yang bisa diekspor ke Word/PDF) sesuai dengan
tata letak standar (17 poin KAK) termasuk menyisipkan Kop Surat.
"""

import json
import os
from datetime import datetime

# Path absolut ke gambar kop surat
KOP_SURAT_PATH = os.path.join(os.path.dirname(__file__), "kop_surat.jpg")

def generate_markdown_from_json(json_filepath: str, output_dir: str = None) -> str:
    """Membaca file JSON dan membuat file Markdown final KAK.
    
    Args:
        json_filepath: Path ke file JSON hasil ekstraksi.
        output_dir: Direktori output (default: sama dengan json).
        
    Returns:
        Path ke file Markdown yang dihasilkan.
    """
    if output_dir is None:
        output_dir = os.path.dirname(json_filepath)
        
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    meta = data.get("metadata", {})
    kak = data.get("kak", {})
    
    judul = meta.get("judul_pekerjaan", "PEKERJAAN TIDAK DIKETAHUI").upper()
    tipe_desc = meta.get("deskripsi_tipe", "").upper()
    tahun = meta.get("tahun_anggaran", datetime.now().year)
    pagu = kak.get("sumber_pendanaan", {}).get("pagu_anggaran", 0)
    waktu = kak.get("jangka_waktu", f"{kak.get('waktu_pelaksanaan', {}).get('durasi_hari', 0)} hari")
    
    # Path relatif untuk markdown link (kalau markdown dan gambar ada di folder berbeda, 
    # lebih aman menggunakan absolute path atau file copy. Di sini kita gunakan absolute path untuk referensi visual)
    kop_surat_md = f"![Kop Surat]({KOP_SURAT_PATH.replace(os.sep, '/')})"
    
    # Merangkai dokumen markdown
    md = []
    
    # 1. KOP SURAT
    md.append('<div class="cover-page">')
    md.append(f'<img src="{KOP_SURAT_PATH.replace(os.sep, "/")}" alt="Kop Surat" />')
    md.append('</div>')
    
    # 2. JUDUL
    md.append('<div class="cover-page title-section">')
    md.append('KERANGKA ACUAN KERJA (KAK)<br><br>')
    if tipe_desc:
        md.append(f'{tipe_desc}<br><br>')
    md.append(f'{judul}<br><br>')
    md.append('KOTA YOGYAKARTA<br><br><br>')
    
    # Generate random / placeholder doc number
    doc_number = f"004/KAK-KAJIAN-04/{datetime.now().strftime('%m/%Y')}"
    md.append(f'Nomor : {doc_number}<br><br><br>')
    md.append('</div>')
    
    # 3. META TABLE (Kegiatan, Sub Kegiatan, Pekerjaan, Paket, No DPA)
    md.append('<table class="meta-table">')
    md.append('<tr><td class="meta-label">KEGIATAN</td><td class="meta-colon">:</td><td class="meta-value">KEGIATAN PENGELOLAAN PENDAPATAN DAERAH</td></tr>')
    md.append('<tr><td class="meta-label">SUB KEGIATAN</td><td class="meta-colon">:</td><td class="meta-value">ANALISA DAN PENGEMBANGAN PAJAK DAERAH, SERTA PENYUSUNAN KEBIJAKAN PAJAK DAERAH</td></tr>')
    md.append(f'<tr><td class="meta-label">PEKERJAAN</td><td class="meta-colon">:</td><td class="meta-value">BELANJA JASA KONSULTANSI KAJIAN PENDAPATAN ASLI DAERAH ({judul})</td></tr>')
    md.append(f'<tr><td class="meta-label">PAKET</td><td class="meta-colon">:</td><td class="meta-value">{judul}</td></tr>')
    md.append('<tr><td class="meta-label">NO DPA</td><td class="meta-colon">:</td><td class="meta-value">DPA/A.1/5.02.0.00.0.00.01.0000/001/2026</td></tr>')
    md.append('</table>')
    
    md.append('<div class="cover-page title-section">')
    md.append(f'TAHUN ANGGARAN {tahun}')
    md.append('</div>')
    
    # Page break sebelum tabel utama
    md.append('<div class="page-break"></div>\n')
    
    # 4. TABEL 17 POIN
    md.append("| No. | Uraian | Keterangan |")
    md.append("|:---:|:---|:---|")
    
    # Poin 1-17
    md.append(f"| 1. | Latar Belakang | {kak.get('latar_belakang', '-')} |")
    
    maksud_tujuan = f"**Maksud:** {kak.get('maksud', '-')}<br><br>**Tujuan:**<br>"
    if isinstance(kak.get('tujuan'), list):
        maksud_tujuan += "".join([f"- {t}<br>" for t in kak.get('tujuan')])
    else:
        maksud_tujuan += str(kak.get('tujuan', '-'))
    md.append(f"| 2. | Maksud dan Tujuan | {maksud_tujuan} |")
    
    sasaran = "".join([f"- {s}<br>" for s in kak.get('sasaran', [])]) if isinstance(kak.get('sasaran'), list) else kak.get('sasaran', '-')
    md.append(f"| 3. | Sasaran | {sasaran} |")
    
    md.append(f"| 4. | Lokasi Kegiatan | {kak.get('lokasi_kegiatan', '-')} |")
    md.append(f"| 5. | Sumber Pendanaan & Biaya | APBD Kota Yogyakarta. Pagu Anggaran maksimal Rp {pagu:,} |")
    
    ruang = "".join([f"- {r}<br>" for r in kak.get('ruang_lingkup', [])]) if isinstance(kak.get('ruang_lingkup'), list) else kak.get('ruang_lingkup', '-')
    md.append(f"| 6. | Ruang Lingkup | {ruang} |")
    
    hasil = "".join([f"- {h}<br>" for h in kak.get('output_keluaran', [])]) if isinstance(kak.get('output_keluaran'), list) else kak.get('output_keluaran', '-')
    md.append(f"| 7. | Hasil Produk | {hasil} |")
    md.append(f"| 8. | Waktu Pelaksanaan | {kak.get('waktu_pelaksanaan', {}).get('durasi_hari', '-')} hari kalender |")
    md.append(f"| 9. | Metodologi | {kak.get('metodologi', '-')} |")
    
    spek = "".join([f"- {s}<br>" for s in kak.get('spesifikasi_teknis', [])]) if isinstance(kak.get('spesifikasi_teknis'), list) else kak.get('spesifikasi_teknis', '-')
    md.append(f"| 10. | Spesifikasi Teknis | {spek} |")
    md.append(f"| 11. | Peralatan dan Material | - |")
    md.append(f"| 12. | Jangka Waktu | {waktu} |")
    
    # Poin 13: Personil (Tabel HTML agar bisa masuk dalam sel tabel Markdown)
    personil_html = "<table><tr><th>Posisi</th><th>Jumlah</th><th>Kualifikasi</th><th>Pengalaman</th></tr>"
    for p in kak.get('kebutuhan_personil', []):
        personil_html += f"<tr><td>{p.get('posisi')}</td><td>{p.get('jumlah')}</td><td>{p.get('kualifikasi_pendidikan')}</td><td>{p.get('pengalaman_tahun')} th</td></tr>"
    personil_html += "</table>"
    if not kak.get('kebutuhan_personil'):
        personil_html = "Menyesuaikan kebutuhan kegiatan."
    md.append(f"| 13. | Kebutuhan Personil | {personil_html} |")
    
    # Poin 14: Jadwal
    jadwal_html = "<ul>"
    for j in kak.get('jadwal_pelaksanaan', []):
        jadwal_html += f"<li>{j.get('tahapan')} (Waktu: {j.get('durasi_atau_hari_ke')})</li>"
    jadwal_html += "</ul>"
    if not kak.get('jadwal_pelaksanaan'):
        jadwal_html = "-"
    md.append(f"| 14. | Jadwal Pelaksanaan | {jadwal_html} |")
    
    md.append(f"| 15. | Laporan Akhir | Disusun pada akhir kegiatan. |")
    md.append(f"| 16. | Pedoman Pengumpulan Data | {kak.get('pedoman_pengumpulan_data', '-')} |")
    md.append(f"| 17. | Alih Pengetahuan | {kak.get('alih_pengetahuan', '-')} |")
    
    md_content = "\n".join(md)
    
    # -----------------------------------------------------------------------
    # Standarisasi Folder & Penamaan File
    # -----------------------------------------------------------------------
    sekarang = datetime.now()
    tahun_sekarang = sekarang.strftime("%Y")
    
    # Nama bulan dalam bahasa Indonesia
    bulan_indo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    nama_bulan = bulan_indo[sekarang.month - 1]
    
    # Struktur Folder: Arsip KAK / Tahun / Bulan
    base_arsip = os.path.join(os.path.dirname(__file__), "Arsip KAK")
    folder_arsip = os.path.join(base_arsip, tahun_sekarang, nama_bulan)
    os.makedirs(folder_arsip, exist_ok=True)
    
    # Format Nama File
    safe_title = meta.get("judul_pekerjaan", "Tanpa_Judul")
    safe_title = "".join(c if c.isalnum() else "_" for c in safe_title)
    import re
    safe_title = re.sub(r"_+", "_", safe_title).strip("_")[:40]
    
    waktu_str = sekarang.strftime("%d-%m-%Y_%H%M%S")
    base_out_name = f"KAK_{safe_title}_{waktu_str}"
    
    # KODE MARKDOWN DI-COMMENT DULU (Aktifkan jika sewaktu-waktu butuh file .md)
    # out_md_path = os.path.join(folder_arsip, base_out_name + ".md")
    # with open(out_md_path, "w", encoding="utf-8") as f:
    #     f.write(md_content)
        
    return md_content, os.path.join(folder_arsip, base_out_name)


def generate_pdf_from_markdown(md_text: str, base_filepath: str) -> str | None:
    """Mengonversi teks Markdown KAK menjadi file PDF yang rapi.
    
    Membutuhkan library `markdown` dan `xhtml2pdf`.
    """
    try:
        import markdown
        from xhtml2pdf import pisa
    except ImportError:
        print("⚠️ Library 'markdown' atau 'xhtml2pdf' tidak ditemukan.")
        print("   Silakan jalankan: pip install markdown xhtml2pdf")
        return None

    # Konversi MD -> HTML
    # Extension 'tables' untuk memastikan tabel Markdown di-render benar ke HTML
    html_body = markdown.markdown(md_text, extensions=['tables'])

    # CSS Khusus untuk meniru layout persis seperti contoh PDF
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2.5cm 2cm 2.5cm 2cm;
            }}
            body {{
                font-family: "Times New Roman", Times, serif;
                font-size: 11pt;
                line-height: 1.5;
                color: #000;
            }}
            .cover-page {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .cover-page img {{
                width: 100%;
                max-width: 800px;
                height: auto;
                margin-bottom: 30px;
            }}
            .title-section {{
                font-weight: bold;
                margin-bottom: 40px;
                line-height: 1.8;
            }}
            .meta-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 40px;
                text-align: left;
            }}
            .meta-table td {{
                padding: 8px 4px;
                vertical-align: top;
                border: none;
            }}
            .meta-label {{
                width: 25%;
                font-weight: bold;
            }}
            .meta-colon {{
                width: 2%;
                font-weight: bold;
            }}
            .meta-value {{
                width: 73%;
                font-weight: bold;
            }}
            
            /* Table 17 Poin */
            table.main-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            /* Sembunyikan header markdown */
            table.main-table thead {{
                display: none;
            }}
            table.main-table th, table.main-table td {{
                border: 1px solid #000;
                padding: 10px;
                vertical-align: top;
                text-align: justify;
            }}
            /* Mengatur lebar kolom utama */
            table.main-table > tbody > tr > td:nth-child(1) {{
                width: 5%;
                text-align: center;
                font-weight: bold;
            }}
            table.main-table > tbody > tr > td:nth-child(2) {{
                width: 25%;
                font-weight: bold;
            }}
            table.main-table > tbody > tr > td:nth-child(3) {{
                width: 70%;
            }}
            
            /* Sub-tabel (Personil & Jadwal) */
            table.main-table td table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 5px;
            }}
            table.main-table td table th, 
            table.main-table td table td {{
                border: 1px solid #000;
                padding: 5px;
                font-size: 10pt;
                text-align: center;
                font-weight: normal;
            }}
            table.main-table td table th {{
                font-weight: bold;
            }}
            
            /* List styling */
            ul, ol {{
                margin-top: 0;
                margin-bottom: 0;
                padding-left: 20px;
            }}
            
            /* Utils */
            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # Ganti tag tabel utama dengan class yang spesifik
    html_template = html_template.replace('<table>', '<table class="main-table">', 1)

    # Buat nama file PDF
    pdf_filepath = base_filepath + ".pdf"

    # Render HTML -> PDF
    with open(pdf_filepath, "wb") as result_file:
        pisa_status = pisa.CreatePDF(
            src=html_template,
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
        md_text, base_path = generate_markdown_from_json(json_file)
        out_pdf = generate_pdf_from_markdown(md_text, base_path)
        if out_pdf:
            print(f"File PDF KAK berhasil dibuat: {out_pdf}")
    else:
        print("Penggunaan: python document_builder.py <path_ke_file.json>")
