"""
json_extractor.py — Structured JSON Output Extractor
====================================================

Setelah wawancara selesai, modul ini mengirim prompt ekstraksi ke
sesi chat yang sama untuk mengkonversi percakapan menjadi JSON
terstruktur yang siap diinjeksi ke templat Word KAK dan Excel HPS.
"""

import json
import os
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Prompt Ekstraksi JSON
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT: str = """\
Wawancara sudah selesai. Sekarang, rangkum SELURUH informasi yang telah \
dikumpulkan selama wawancara menjadi format JSON terstruktur.

ATURAN OUTPUT:
1. Output HANYA berupa JSON murni — tanpa markdown, tanpa komentar, tanpa teks lain.
2. Jangan tambahkan ```json atau ``` di awal/akhir.
3. Gunakan bahasa Indonesia untuk semua nilai teks.
4. Untuk field yang tidak dijawab user, isi dengan null.
5. Pastikan semua angka anggaran berupa integer (tanpa titik/koma).

SCHEMA JSON YANG HARUS DIIKUTI:

{
  "metadata": {
    "judul_pekerjaan": "string",
    "tipe_kegiatan": "A|B|C",
    "deskripsi_tipe": "Acara Pertemuan|Jasa Konsultansi|Pengadaan Barang",
    "tahun_anggaran": 2026,
    "tanggal_penyusunan": "YYYY-MM-DD"
  },
  "kak": {
    "latar_belakang": "string panjang, uraian lengkap",
    "maksud": "string",
    "tujuan": ["string", "string"],
    "sasaran": ["string"],
    "lokasi_kegiatan": "string",
    "sumber_pendanaan": {
      "sumber": "APBD",
      "pagu_anggaran": 100000000,
      "termasuk_ppn": true,
      "ppn_persen": 11
    },
    "ruang_lingkup": ["string"],
    "output_keluaran": ["string"],
    "waktu_pelaksanaan": {
      "durasi_hari": 90,
      "tanggal_mulai": "YYYY-MM-DD atau null",
      "tanggal_selesai": "YYYY-MM-DD atau null",
      "lokasi": "string"
    },
    "metodologi": "string panjang, uraian lengkap",
    "peserta": {
      "deskripsi": "string",
      "jumlah": 0,
      "rincian": ["string"]
    },
    "narasumber": [
      {
        "nama_atau_posisi": "string",
        "instansi": "string",
        "materi": "string"
      }
    ],
    "kebutuhan_personil": [
      {
        "posisi": "string",
        "jumlah": 1,
        "kualifikasi_pendidikan": "S1/S2/S3 Bidang",
        "pengalaman_tahun": 5
      }
    ],
    "jadwal_pelaksanaan": [
      {
        "tahapan": "string",
        "durasi_atau_hari_ke": "string"
      }
    ],
    "spesifikasi_teknis": ["string"]
  },
  "hps": {
    "biaya_personil": [
      {
        "uraian": "string",
        "volume": 1,
        "satuan_waktu": 3,
        "satuan": "ob",
        "harga_satuan": 6000000,
        "jumlah": 18000000,
        "kualifikasi": "string"
      }
    ],
    "biaya_non_personil": [
      {
        "uraian": "string",
        "volume": 1,
        "satuan_waktu": 1,
        "satuan": "kali",
        "harga_satuan": 1000000,
        "jumlah": 1000000
      }
    ],
    "subtotal": 0,
    "ppn": 0,
    "total": 0
  }
}
"""


# ---------------------------------------------------------------------------
# Extraction Logic
# ---------------------------------------------------------------------------

def extract_json_from_response(response_text: str) -> dict | None:
    """Ekstrak dan parse JSON dari respons bot.

    Mencoba beberapa strategi parsing untuk menangani
    kasus di mana bot membungkus JSON dalam markdown code blocks.

    Args:
        response_text: Teks respons mentah dari bot.

    Returns:
        Dict hasil parsing JSON, atau None jika gagal.
    """
    text = response_text.strip()

    # Strategi 1: Coba parse langsung
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategi 2: Ekstrak dari markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategi 3: Cari object JSON pertama di teks ({ ... })
    brace_start = text.find("{")
    if brace_start != -1:
        # Cari matching closing brace
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    return None


def save_json_output(data: dict, output_dir: str | None = None) -> str:
    """Simpan data JSON ke file di direktori output.

    Args:
        data: Dict data KAK/HPS yang sudah diekstrak.
        output_dir: Direktori output. Default: ./output/

    Returns:
        Path lengkap ke file JSON yang disimpan.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "output")

    os.makedirs(output_dir, exist_ok=True)

    # Buat nama file berdasarkan judul dan timestamp
    title = data.get("metadata", {}).get("judul_pekerjaan", "kak")
    # Bersihkan karakter tidak valid untuk nama file
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"KAK_{safe_title}_{timestamp}.json"

    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath
