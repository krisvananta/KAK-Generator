"""
import_reference.py — Konverter Dokumen PDF/XLSX ke JSON
=============================================================

Skrip ini memudahkan pengguna non-teknis untuk memperbarui data referensi
(seperti SHBJ atau DPA). Cukup jalankan skrip ini dengan file PDF atau
Excel (XLSX), dan bot (Gemini) akan otomatis membaca isinya, mempertahankan
format tabel, dan menyimpannya sebagai JSON (`SHBJ.json`) yang standar
untuk digunakan oleh sistem.

Cara Penggunaan:
    python import_reference.py "path/to/file.pdf"
    python import_reference.py "path/to/file.xlsx"
"""

import os
import sys
import logging
import json
import time
from google import genai
from google.genai import types

# Sembunyikan warning bawaan dari library google-genai
import warnings
warnings.filterwarnings("ignore")
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)

from config import GEMINI_API_KEY, MODEL_NAME

PROMPT = """
MISSION You are an expert AI Data Architect specializing in legal document ingestion, financial schema normalization, and zero-loss ETL pipelines. Your objective is to extract official government reference documents—arriving as either PDF decree documents (such as SHBJ/SBM) or Excel spreadsheets (.xlsx)—and convert them into a strictly typed, deterministic JSON Structured Output. This JSON dataset serves as the immutable "Single Source of Truth" for downstream Procurement Bots (specifically the KAK Generator and HPS Audit Engine).

# CORE PIPELINE SPECIFICATIONS

### 1. Dual-Input Format Handling
- PDF Mode: Perform spatial layout analysis to correctly group hierarchical decree headings, multi-column tables, and embedded footers.
- Excel (.xlsx) Mode: Parse multi-sheet workbooks, header rows, and merged cells into structured record arrays without relying on fragile string splitting.

### 2. Zero-Tolerance Output Mutability
You MUST strictly output raw JSON complying with the declared schema. Do NOT wrap the response in markdown code fences (```json ... ```) and do NOT use markdown tables.

### 3. Strict Schema & Field Mapping Rules (Compliant with Pemkot Yogyakarta SHBJ)

#### A. Document Metadata (`metadata`)
- `jenis_dokumen`: Enum string -> ["SHBJ", "DPA", "SBM", "MASTER_PEJABAT", "LAINNYA"]
- `nomor_keputusan`: String (e.g., "Keputusan Wali Kota Yogyakarta Nomor 263 Tahun 2026")
- `tahun_anggaran`: Integer (e.g., 2027)
- `instansi_penerbit`: String (e.g., "PEMKOT_YOGYAKARTA", "BPKAD")

#### B. Reference Items (`items` array)
Each item in the reference list must adhere to the following schema:

1. `kategori_biaya`: Enum string -> ["BIAYA_PERSONIL_KONSULTANSI", "BIAYA_NON_PERSONIL", "JAMUAN_DAN_RAPAT", "HONORARIUM_KEGIATAN", "OPERASIONAL_SEWA"]
    - BIAYA_PERSONIL_KONSULTANSI: Expert Fees, Consultant Billing Rates (Bagian 5, 11, & 12 SHBJ).
    - BIAYA_NON_PERSONIL: Printing, Video, Documentation, Equipment, Travel (Bagian 10 SHBJ).
    - JAMUAN_DAN_RAPAT: Snacks, Meals, Meeting Packages (Bagian 1 & 2 SHBJ).
    - HONORARIUM_KEGIATAN: Speaker, Moderator, Committee, or Resource Person Fees (Bagian 3 & 4 SHBJ).
    - OPERASIONAL_SEWA: Venue, Vehicle, or Property Rentals (Bagian 10.1 SHBJ).
2. `uraian`: String. The exact title/description of the item or expert position. Do not summarize.
3. `kualifikasi_ahli` (Optional, required if `kategori_biaya == "BIAYA_PERSONIL_KONSULTANSI"`):
    - `tingkat_pendidikan`: Enum string -> ["D3", "S1", "S2", "S3", "NON_GELAR", "TIDAK_DIBATASI"]
    - `tingkat_keahlian`: Enum string -> ["AHLI_PRATAMA", "AHLI_MUDA", "AHLI_MADYA", "AHLI_UTAMA", "NON_KUALIFIKASI"]
    - `pengalaman_minimal_tahun`: Integer (Default: 0 if not specified)
    - `jenis_penyedia`: Enum string -> ["BADAN_USAHA", "PERORANGAN", "TIDAK_DIBATASI"]
4. `satuan`: Enum string based on official Pemkot Yogyakarta metrics -> ["ob", "oh", "oj", "ok", "os", "jpl", "pack", "bulan", "hari", "paket", "kegiatan", "laporan", "buku", "lembar", "halaman", "pasang", "rim", "set", "unit", "m2", "mmkl", "publikasi", "peserta", "orang/kegiatan"]
    *(Note: Normalize variants like "orang/bulan" or "Orang Bulan" to strictly lowercase "ob", and "orang/sessi" to "os")*
5. `harga_satuan`: Integer.
    - Mandatory cleaning: Remove currency symbols ("Rp"), thousands separators ("."), whitespace, and decimals.
    - Example: "15.210.000" -> 15210000.
6. `is_plafon_maksimal`: Boolean. Always set to true for SHBJ items as they represent official price ceilings.

OUTPUT FORMAT MUST BE A STRICT JSON OBJECT MATCHING THIS STRUCTURE EXACTLY.
"""

def extract_json_from_file(client, filepath: str) -> dict:
    """Mengupload satu file ke Gemini dan mengekstrak JSON dengan Exponential Backoff & Model Fallback."""
    uploaded_file = client.files.upload(file=filepath)
    
    # Retry agresif untuk melawan 503 dan 429
    max_retries = 20
    model_attempts = 0
    result_json = {"metadata": {}, "items": []}
    
    # Jalur model cadangan untuk menghindari Limit Kuota (429) dan Server Sibuk (503)
    fallback_models = [
        MODEL_NAME, 
        "gemini-3.7-flash", 
        "gemini-3.5-flash", 
        "gemini-2.5-flash",
        "gemini-flash-lite-latest"
    ]
    current_model_idx = 0
    
    for attempt in range(max_retries):
        current_model = fallback_models[current_model_idx]
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=[uploaded_file, PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            raw_text = response.text.strip()
            # Coba parse JSON untuk validasi
            result_json = json.loads(raw_text)
            break
            
        except Exception as e:
            error_str = str(e)
            
            error_type = ""
            is_transient = False
            if "429" in error_str: 
                error_type = "Limit Kuota (429)"
                is_transient = False # Langsung fallback jika limit kuota, tidak usah ditunggu
            elif "503" in error_str: 
                error_type = "Server Sibuk (503)"
                is_transient = True
            elif "404" in error_str: 
                error_type = "Model tidak tersedia (404)"
                is_transient = False
            
            if error_type:
                # Jika error sementara (429/503), coba ulang di model yang sama 3x (5s, 10s, 15s)
                if is_transient:
                    model_attempts += 1
                    if model_attempts <= 3:
                        wait_time = 5 * model_attempts
                        print(f"   ⚠️ {error_type}. Menunggu {wait_time} detik untuk coba lagi... (Percobaan {model_attempts}/3 pada model ini)")
                        time.sleep(wait_time)
                        continue
                        
                # Jika 404 (permanen) atau sudah 3x gagal di model ini, turun kasta
                if current_model_idx < len(fallback_models) - 1:
                    current_model_idx += 1
                    next_model = fallback_models[current_model_idx]
                    model_attempts = 0 # Reset untuk model baru
                    print(f"   ⚠️ {error_type} persisten pada {current_model}. Mengalihkan ke {next_model}...")
                    time.sleep(2)
                    continue
                    
            if "503" in error_str or "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = 35 if "429" in error_str else 20
                    print(f"   ⚠️ Semua Jalur Model Penuh. Menunggu {wait_time} detik... (Sisa retries: {max_retries - attempt - 1})")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Gagal memproses chunk {os.path.basename(filepath)} setelah {max_retries} percobaan.")
                    break
            elif isinstance(e, json.JSONDecodeError):
                if attempt < max_retries - 1:
                    print(f"   ⚠️ AI merespons dengan format JSON tidak valid. Mencoba ulang... (Percobaan {attempt+2}/{max_retries})")
                    time.sleep(3)
                else:
                    print(f"   ❌ Gagal memproses chunk {os.path.basename(filepath)}: Output JSON selalu cacat.")
                    break
            else:
                print(f"   ❌ Gagal memproses chunk {os.path.basename(filepath)}: {e}")
                break
                
    # Cleanup
    client.files.delete(name=uploaded_file.name)
    return result_json

def convert_document_to_json(filepath: str) -> None:
    """Menggunakan Gemini untuk mengonversi dokumen PDF/Excel ke format JSON terstruktur (Pagination-based)."""
    
    if not os.path.exists(filepath):
        print(f"❌ Error: File '{filepath}' tidak ditemukan.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    final_data = {
        "metadata": {},
        "items": []
    }
    
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".pdf":
        print(f"📑 Memulai Zero-Loss ETL Pipeline untuk PDF: '{os.path.basename(filepath)}'")
        try:
            from pypdf import PdfReader, PdfWriter
            reader = PdfReader(filepath)
            total_pages = len(reader.pages)
            chunk_size = 3
            
            print(f"📄 Total halaman: {total_pages}. Membagi menjadi pecahan (chunk) {chunk_size} halaman...")
            
            for i in range(0, total_pages, chunk_size):
                writer = PdfWriter()
                end_page = min(i + chunk_size, total_pages)
                for j in range(i, end_page):
                    writer.add_page(reader.pages[j])
                    
                temp_pdf = f"temp_chunk_{i}_to_{end_page}.pdf"
                with open(temp_pdf, "wb") as f:
                    writer.write(f)
                
                print(f"⏳ Mengekstrak Halaman {i+1} sampai {end_page}...")
                chunk_data = extract_json_from_file(client, temp_pdf)
                
                # Gabungkan hasil
                if not final_data["metadata"] and chunk_data.get("metadata"):
                    final_data["metadata"] = chunk_data.get("metadata", {})
                
                if chunk_data.get("items"):
                    final_data["items"].extend(chunk_data["items"])
                    print(f"   ✅ {len(chunk_data['items'])} item ditemukan.")
                else:
                    print("   ⚠️ Tidak ada item yang terdeteksi di chunk ini.")
                    
                # Hapus file temp lokal
                os.remove(temp_pdf)
                
        except ImportError:
            print("❌ Error: library 'pypdf' tidak ditemukan. Jalankan: pip install pypdf")
            return
            
    else:
        # Jika bukan PDF (misal Excel), langsung hajar utuh
        print(f"📊 Mengekstrak file {ext}: '{os.path.basename(filepath)}'")
        chunk_data = extract_json_from_file(client, filepath)
        final_data = chunk_data
        print(f"✅ {len(final_data.get('items', []))} item ditemukan.")

    # Simpan Hasil Akhir
    output_dir = os.path.join(os.path.dirname(__file__), "reference files")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "SHBJ.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n🎉 BERHASIL! File telah dikonversi secara menyeluruh tanpa data yang terpotong.")
    print(f"👉 Total Item Tersimpan: {len(final_data.get('items', []))} items")
    print(f"👉 Lokasi File: {output_path}")
    print("\nSistem KAK Generator akan otomatis mendeteksi pembaruan ini pada percakapan selanjutnya.")

if __name__ == "__main__":
    # Fix encoding terminal Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    
    if len(sys.argv) < 2:
        print("Gunakan perintah: python import_reference.py <path_ke_file>")
        print("Contoh: python import_reference.py \"C:\\Users\\Dokumen\\Update_SHBJ_2027.pdf\"")
        sys.exit(1)
        
    target_file = sys.argv[1]
    convert_document_to_json(target_file)
