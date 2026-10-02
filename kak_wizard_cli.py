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

    data = bot.extract_structured_json()

    if data is None:
        print("⚠️  Gagal mengekstrak JSON dari percakapan.")
        print("    Dokumen KAK teks sudah tersedia di atas.")
        print("    Anda bisa copy-paste secara manual.\n")
        return

    # Simpan ke file JSON
    filepath = save_json_output(data)

    print(f"✅ Data JSON berhasil disimpan!")
    print(f"   📄 File JSON: {filepath}")

    # Buat Dokumen PDF Final KAK
    try:
        from document_builder import generate_markdown_from_json, generate_pdf_from_markdown
        
        # Ekstrak data dan buat markdown di memori (tidak disimpan ke file)
        md_text, base_filepath = generate_markdown_from_json(filepath)
        
        # Buat PDF
        pdf_filepath = generate_pdf_from_markdown(md_text, base_filepath)
        
        if pdf_filepath:
            print(f"   📑 File KAK Final (PDF)     : {pdf_filepath}")
            
            # Buka otomatis file PDF-nya
            import os, sys
            print("   (Membuka file PDF secara otomatis...)")
            try:
                if sys.platform == "win32":
                    os.startfile(pdf_filepath)
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.call(["open", pdf_filepath])
                else:
                    import subprocess
                    subprocess.call(["xdg-open", pdf_filepath])
            except Exception as e:
                print(f"   ⚠️ Gagal membuka PDF otomatis: {e}")
                
    except Exception as e:
        print(f"   ⚠️ Gagal membuat dokumen akhir: {e}\n")

    # Tampilkan ringkasan
    metadata = data.get("metadata", {})
    hps = data.get("hps", {})

    print("--- Ringkasan ---")
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
    # Fix encoding untuk Windows terminal (emoji support)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print_banner()

    print("⏳ Menginisialisasi bot & memuat data SHBJ...\n")
    bot = KAKInterviewBot(system_instruction=SYSTEM_INSTRUCTION)

    interview_completed = run_interview(bot)

    if interview_completed:
        extract_and_save_json(bot)

    print("=" * 64)
    print("Terima kasih telah menggunakan KAK Generator!")
    print("=" * 64)


if __name__ == "__main__":
    main()