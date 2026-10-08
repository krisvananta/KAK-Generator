"""
KAK Wizard CLI — Bot Wawancara Adaptif untuk Penyusunan KAK/TOR
===============================================================

Bot automasi berbasis Gemini untuk membantu menyusun Kerangka Acuan Kerja
(KAK/TOR) standar pemerintah secara interaktif melalui terminal.

Fitur:
- Wawancara bertahap adaptif (7 tahap + QC)
- Validasi anggaran real-time berdasarkan SHBJ Pemkot Yogyakarta
- Output JSON terstruktur untuk templat Word KAK & Excel HPS

Penggunaan:
    Klik ganda  run.bat
    — atau —
    python kak_wizard_cli.py
"""

import sys

from chat_engine import KAKInterviewBot
from config import COMPLETION_TOKEN
from json_extractor import save_json_output
from prompts import INITIAL_TRIGGER, SYSTEM_INSTRUCTION


# ---------------------------------------------------------------------------
# Tampilan Terminal
# ---------------------------------------------------------------------------

def print_banner() -> None:
    """Tampilkan header aplikasi di terminal."""
    print("=" * 64)
    print("🤖 BOT PENYUSUNAN KAK/TOR ADAPTIF (BPKAD KOTA YOGYAKARTA)")
    print("=" * 64)
    print("Fitur: Wawancara 7 Tahap + QC + Validasi SHBJ + Output JSON")
    print("Ketik 'keluar' atau 'q' kapan saja untuk menghentikan.\n")


# ---------------------------------------------------------------------------
# Loop Wawancara
# ---------------------------------------------------------------------------

def run_interview(bot: KAKInterviewBot) -> bool:
    """Jalankan loop wawancara interaktif.

    Args:
        bot: Instance KAKInterviewBot yang sudah diinisialisasi.

    Returns:
        True jika wawancara selesai normal, False jika dibatalkan.
    """
    # Kirim pesan pemicu agar bot menyapa dan mengajukan Pertanyaan 1
    try:
        greeting = bot.send_initial_trigger(INITIAL_TRIGGER)
        print(f"🤖 Bot: {greeting}\n")
    except Exception as e:
        print(f"\n❌ [Sistem] Gagal memulai wawancara karena error: {e}")
        print("Silakan coba jalankan ulang aplikasi.\n")
        return False

    while True:
        # Tampilkan progress bar
        print(f"📊 Progres: {bot.progress}")
        user_input = input("👤 Anda: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("keluar", "q", "exit"):
            print("\n👋 Sesi wawancara dihentikan. Sampai jumpa!")
            return False

        print("\n⏳ Bot sedang berpikir...")
        try:
            response = bot.send_message(user_input)
            print(f"\n🤖 Bot: {response}\n")

            if bot.is_complete():
                print("\n✅ Wawancara selesai! Dokumen KAK/TOR telah berhasil disusun.")
                return True
        except Exception as e:
            print(f"\n❌ [Sistem] Terjadi kesalahan saat memproses pesan: {e}")
            print("Pesan Anda tidak terkirim. Silakan coba kirim ulang atau periksa koneksi Anda.\n")
            # Loop akan kembali ke input user tanpa mereset progres

    return False


# ---------------------------------------------------------------------------
# Ekstraksi JSON
# ---------------------------------------------------------------------------

def extract_and_save_json(bot: KAKInterviewBot) -> None:
    """Ekstrak data terstruktur dan simpan ke file JSON.

    Args:
        bot: Instance KAKInterviewBot dengan sesi chat yang sudah selesai.
    """
    print("\n" + "=" * 64)
    print("📦 MENGEKSTRAK DATA TERSTRUKTUR...")
    print("=" * 64)
    print("⏳ Memproses seluruh percakapan menjadi JSON terstruktur...\n")

    data = None
    while data is None:
        data = bot.extract_structured_json()

        if data is None:
            print("\n⚠️  Gagal mengekstrak JSON dari percakapan (Server penuh atau limit API tercapai).")
            pilihan = input("🔄 Tekan 'R' lalu Enter untuk MENCOBA LAGI, atau tombol lain untuk KELUAR: ").strip().lower()
            if pilihan != 'r':
                print("\n    Dokumen KAK teks sudah tersedia di atas.")
                print("    Anda bisa copy-paste secara manual.\n")
                return
            print("\n⏳ Mencoba mengekstrak ulang JSON...")

    # Simpan ke file JSON
    filepath = save_json_output(data)

    print(f"✅ Data JSON berhasil disimpan!")
    print(f"   📄 File JSON: {filepath}")

    generate_documents(filepath)


def generate_documents(filepath: str) -> None:
    """Membaca file JSON lalu merender PDF KAK dan Excel HPS."""
    import json
    
    # Baca ringkasan data dulu
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error membaca file JSON: {e}")
        return
        
    print("\n" + "=" * 64)
    print("🖨️  MEMBUAT DOKUMEN FINAL...")
    print("=" * 64)
    print(f"Menggunakan data dari: {filepath}\n")

    # Buat Dokumen PDF Final KAK dan Excel HPS
    try:
        from document_builder import generate_html_from_json, generate_pdf_from_html
        from hps_builder import generate_hps_excel
        
        # 1. Ekstrak data KAK dan buat HTML di memori (tidak disimpan ke file)
        html_text, base_filepath = generate_html_from_json(filepath)
        
        # Folder arsip spesifik sesi ini
        import os
        arsip_dir = os.path.dirname(base_filepath)
        
        # 2. Buat PDF KAK
        pdf_filepath = generate_pdf_from_html(html_text, base_filepath)
        
        # 3. Buat Excel HPS (masukkan ke folder arsip_dir yang sama)
        excel_filepath = generate_hps_excel(filepath, output_dir=arsip_dir)
        
        if pdf_filepath:
            print(f"   📑 File KAK Final (PDF)     : {pdf_filepath}")
        if excel_filepath:
            print(f"   📊 File HPS/RAB (Excel)     : {excel_filepath}")
            
        # Buka otomatis file PDF dan Excel
        if pdf_filepath or excel_filepath:
            import os, sys
            print("   (Membuka file dokumen secara otomatis...)")
            try:
                if sys.platform == "win32":
                    if pdf_filepath: os.startfile(pdf_filepath)
                    if excel_filepath: os.startfile(excel_filepath)
                elif sys.platform == "darwin":
                    import subprocess
                    if pdf_filepath: subprocess.call(["open", pdf_filepath])
                    if excel_filepath: subprocess.call(["open", excel_filepath])
                else:
                    import subprocess
                    if pdf_filepath: subprocess.call(["xdg-open", pdf_filepath])
                    if excel_filepath: subprocess.call(["xdg-open", excel_filepath])
            except Exception as e:
                print(f"   ⚠️ Gagal membuka PDF otomatis: {e}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"   ⚠️ Gagal membuat dokumen akhir: {e}\n")

    # Tampilkan ringkasan
    metadata = data.get("metadata", {})
    hps = data.get("hps", {})

    print("\n--- Ringkasan ---")
    print(f"   Judul  : {metadata.get('judul_pekerjaan', '-')}")
    print(f"   Tipe   : {metadata.get('tipe_kegiatan', '-')} — {metadata.get('deskripsi_tipe', '-')}")

    if hps.get("total"):
        total = hps["total"]
        print(f"   Total  : Rp {total:,.0f}")

    print()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point utama aplikasi."""
    import os
    import sys
    # Fix encoding untuk Windows terminal (emoji support)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Jika ada argumen (path file json), langsung render dokumen
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        print_banner()
        if not os.path.exists(json_path):
            print(f"❌ File tidak ditemukan: {json_path}")
        else:
            generate_documents(json_path)
        print("\n" + "=" * 64)
        print("Selesai! Terima kasih telah menggunakan KAK Generator.")
        print("=" * 64)
        return

    print_banner()
    print("\n⏳ Menginisialisasi bot & memuat data SHBJ...\n")
    bot = KAKInterviewBot(system_instruction=SYSTEM_INSTRUCTION)

    interview_completed = run_interview(bot)

    if interview_completed:
        extract_and_save_json(bot)

    print("=" * 64)
    print("Terima kasih telah menggunakan KAK Generator!")
    print("=" * 64)


if __name__ == "__main__":
    main()