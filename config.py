"""
config.py — Konfigurasi Aplikasi KAK Generator
================================================

Memuat pengaturan dari file .env dan menyediakan konstanta konfigurasi
yang digunakan di seluruh aplikasi.
"""

import os
import sys

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Muat variabel dari .env (jika ada)
# ---------------------------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------------------------
# Konfigurasi API Gemini
# ---------------------------------------------------------------------------

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY belum diatur!")
    print("   Opsi 1: Buat file .env dengan isi  GEMINI_API_KEY=kunci_anda")
    print("   Opsi 2: Set env var  $env:GEMINI_API_KEY='kunci_anda'")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Konfigurasi Model
# ---------------------------------------------------------------------------

MODEL_NAME: str = "gemini-3.8-flash"
TEMPERATURE: float = 0.4
COMPLETION_TOKEN: str = "[SELESAI_WAWANCARA]"


# ---------------------------------------------------------------------------
# Batas Anggaran
# ---------------------------------------------------------------------------

PAGU_DPA_MAKSIMAL: int = 100_000_000       # Rp 100 juta (termasuk PPN)
PPN_PERSEN: float = 11.0                    # PPN 11%
DURASI_STANDAR_HARI: int = 90               # 90 hari kalender
