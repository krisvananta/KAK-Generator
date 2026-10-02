"""
shbj_data.py — Parser & Mapper Data SHBJ (Standar Harga Satuan Jasa)
====================================================================

Mem-parse file SHBJ.json dan memfilter item berdasarkan kategori biaya.
Menyediakan pemetaan tipe kegiatan (A/B/C) ke kategori SHBJ yang
relevan untuk diinjeksi ke konteks LLM.

Sumber data: Keputusan Wali Kota Yogyakarta No. 263 Tahun 2026
             Rincian Standar Harga Satuan Jasa TA 2027
"""

import os
import json
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Konfigurasi Path
# ---------------------------------------------------------------------------

SHBJ_FILE_PATH: str = os.path.join(
    os.path.dirname(__file__), "reference files", "SHBJ.json"
)

# ---------------------------------------------------------------------------
# Pemetaan Kategori SHBJ ke Tipe Kegiatan
# ---------------------------------------------------------------------------

# Kategori biaya yang relevan per tipe kegiatan
CATEGORIES_BY_TYPE: dict[str, list[str]] = {
    "A": [  # Acara / Pertemuan
        "JAMUAN_DAN_RAPAT", 
        "HONORARIUM_KEGIATAN", 
        "OPERASIONAL_SEWA", 
        "BIAYA_NON_PERSONIL"
    ],     
    "B": [  # Jasa Konsultansi / Kajian
        "BIAYA_PERSONIL_KONSULTANSI", 
        "JAMUAN_DAN_RAPAT", 
        "HONORARIUM_KEGIATAN", 
        "BIAYA_NON_PERSONIL", 
        "OPERASIONAL_SEWA"
    ],     
    "C": [  # Pengadaan Barang / Fisik / Aplikasi
        "BIAYA_NON_PERSONIL", 
        "HONORARIUM_KEGIATAN",
        "OPERASIONAL_SEWA"
    ],           
}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SHBJData:
    """Representasi data terstruktur SHBJ dari JSON."""
    metadata: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)

    def get_items_for_type(self, activity_type: str) -> list[dict[str, Any]]:
        """Ambil item SHBJ yang relevan untuk tipe kegiatan tertentu.

        Args:
            activity_type: "A", "B", atau "C".

        Returns:
            List dictionary item tarif yang relevan.
        """
        activity_type = activity_type.upper()
        allowed_categories = CATEGORIES_BY_TYPE.get(activity_type, [])
        return [
            item for item in self.items
            if item.get("kategori_biaya") in allowed_categories
        ]

    def format_for_injection(
        self,
        activity_type: str,
        max_chars: int = 30000,
    ) -> str:
        """Format item-item SHBJ yang relevan untuk diinjeksi ke prompt LLM.

        Mengonversi JSON object menjadi teks terstruktur yang mudah dipahami LLM.

        Args:
            activity_type: "A", "B", atau "C".
            max_chars: Batas maksimum karakter output.

        Returns:
            String berisi data tarif SHBJ yang siap diinjeksi.
        """
        items = self.get_items_for_type(activity_type)
        if not items:
            return ""

        instansi = self.metadata.get("instansi_penerbit", "Pemerintah Kota Yogyakarta")
        nomor_kep = self.metadata.get("nomor_keputusan", "")
        tahun = self.metadata.get("tahun_anggaran", "")

        parts = [
            f"=== DATA TARIF SHBJ {instansi} (TA {tahun}) ===",
            f"Sumber: {nomor_kep}",
            "GUNAKAN DATA INI untuk menghitung dan memvalidasi anggaran.",
            "JANGAN pernah menyuruh user mencari data harga sendiri.",
            "",
        ]

        current_chars = sum(len(p) for p in parts)

        # Kelompokkan item berdasarkan kategori agar lebih rapi
        grouped_items = {}
        for item in items:
            cat = item.get("kategori_biaya", "LAINNYA")
            if cat not in grouped_items:
                grouped_items[cat] = []
            grouped_items[cat].append(item)

        for cat, cat_items in grouped_items.items():
            section_header = f"\n--- KATEGORI: {cat} ---\n"
            parts.append(section_header)
            current_chars += len(section_header)

            for item in cat_items:
                uraian = item.get("uraian", "")
                satuan = item.get("satuan", "")
                harga = item.get("harga_satuan", 0)
                
                # Format kualifikasi jika ada
                kualifikasi = ""
                if "kualifikasi_ahli" in item:
                    k = item["kualifikasi_ahli"]
                    kualifikasi = f" [Pendidikan: {k.get('tingkat_pendidikan', '')}, Keahlian: {k.get('tingkat_keahlian', '')}, Pengalaman: {k.get('pengalaman_minimal_tahun', 0)} thn]"

                item_text = f"- {uraian}{kualifikasi}: Rp {harga:,} per {satuan}\n"

                if current_chars + len(item_text) > max_chars:
                    parts.append("\n[... bagian selanjutnya dipotong karena batas konteks ...]")
                    break

                parts.append(item_text)
                current_chars += len(item_text)
            
            if current_chars > max_chars:
                break

        parts.append("\n=== AKHIR DATA TARIF SHBJ ===")
        return "".join(parts)


# ---------------------------------------------------------------------------
# Parsing Functions
# ---------------------------------------------------------------------------

def parse_shbj_file(filepath: str | None = None) -> SHBJData:
    """Parse file SHBJ.json menjadi struktur SHBJData.

    Args:
        filepath: Path ke file SHBJ.json. Default: SHBJ_FILE_PATH.

    Returns:
        SHBJData berisi struktur data JSON.
    """
    filepath = filepath or SHBJ_FILE_PATH
    data = SHBJData()
    
    if not os.path.exists(filepath):
        print(f"⚠️ Peringatan: File {filepath} tidak ditemukan. Menggunakan data kosong.")
        return data

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            json_content = json.load(f)
            data.metadata = json_content.get("metadata", {})
            data.items = json_content.get("items", [])
        except json.JSONDecodeError:
            print(f"⚠️ Peringatan: File {filepath} bukan JSON yang valid.")

    return data


# ---------------------------------------------------------------------------
# Budget Constraint Constants
# ---------------------------------------------------------------------------

PAGU_DPA_MAKSIMAL: int = 100_000_000
PPN_PERSEN: float = 11.0
DURASI_STANDAR_HARI: int = 90

BUDGET_CONSTRAINTS_TEXT: str = f"""\
=== BATAS ANGGARAN ===
Pagu DPA Maksimal  : Rp {PAGU_DPA_MAKSIMAL:,.0f} (sudah termasuk PPN {PPN_PERSEN:.0f}%)
Subtotal Maksimal  : Rp {PAGU_DPA_MAKSIMAL / (1 + PPN_PERSEN / 100):,.0f} (sebelum PPN)
PPN                : {PPN_PERSEN:.0f}%
Durasi Standar     : {DURASI_STANDAR_HARI} hari kalender

ATURAN ANGGARAN:
- Hitung SEMUA biaya berdasarkan tarif SHBJ di atas.
- Jika total melebihi pagu, LANGSUNG beri peringatan dan saran alternatif.
- Jangan pernah bilang "silakan lihat dokumen SHBJ" — Anda SUDAH memiliki datanya.
- Berikan hitungan rinci: Volume × Satuan Waktu × Harga Satuan = Jumlah.
=== AKHIR BATAS ANGGARAN ===
"""


# ---------------------------------------------------------------------------
# Convenience: Load & Cache with Auto-Update
# ---------------------------------------------------------------------------

_cached_data: SHBJData | None = None
_last_mtime: float = 0.0


def load_shbj(filepath: str | None = None) -> SHBJData:
    """Load dan cache data SHBJ. Otomatis reload jika file diubah.

    Melacak waktu modifikasi file (mtime). Jika terdeteksi ada
    perubahan pada dokumen referensi, cache akan dibersihkan dan
    file di-parse ulang.

    Args:
        filepath: Path ke file SHBJ.json. Default: SHBJ_FILE_PATH.

    Returns:
        SHBJData yang up-to-date.
    """
    global _cached_data, _last_mtime
    
    path = filepath or SHBJ_FILE_PATH
    
    try:
        current_mtime = os.path.getmtime(path)
    except FileNotFoundError:
        current_mtime = 0.0

    # Reload jika cache kosong atau file sudah diubah sejak parse terakhir
    if _cached_data is None or current_mtime > _last_mtime:
        if current_mtime > 0:
            print(f"🔄 [Sistem] Memuat pembaruan referensi data tarif SHBJ JSON...")
        _cached_data = parse_shbj_file(path)
        _last_mtime = current_mtime
        
    return _cached_data
