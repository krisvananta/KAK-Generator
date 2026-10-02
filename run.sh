#!/bin/bash

# ============================================================
#   KAK Generator - Setup & Launch (Mac/Linux)
# ============================================================

echo ""
echo "============================================================"
echo "  KAK Generator - Setup & Launch"
echo "============================================================"
echo ""

# --- Cek apakah Python3 tersedia ---
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 tidak ditemukan!"
    echo "        Silakan install Python dari https://www.python.org/downloads/"
    echo "        Atau gunakan Homebrew: brew install python"
    echo ""
    read -p "Press any key to continue..."
    exit 1
fi

# --- Install dependencies ---
echo "[1/2] Memeriksa dependensi..."
python3 -m pip install -r "$(dirname "$0")/requirements.txt" --quiet --disable-pip-version-check
if [ $? -ne 0 ]; then
    echo "[ERROR] Gagal menginstall dependensi!"
    echo "        Pastikan koneksi internet aktif."
    echo ""
    read -p "Press any key to continue..."
    exit 1
fi
echo "      Dependensi siap."
echo ""

# --- Loop Menu ---
while true; do
    echo "============================================================"
    echo "  MENU UTAMA"
    echo "============================================================"
    echo "[1] Jalankan KAK Generator (Wawancara)"
    echo "[2] Update Data SHBJ (Import dari PDF / Excel)"
    echo "[3] Keluar"
    echo "============================================================"
    read -p "Pilih menu [1/2/3]: " pilihan

    if [ "$pilihan" == "1" ]; then
        echo ""
        echo "[2/2] Memulai KAK Generator..."
        echo ""
        python3 "$(dirname "$0")/kak_wizard_cli.py"
        echo ""
        read -p "Tekan Enter untuk kembali ke menu..."

    elif [ "$pilihan" == "2" ]; then
        echo ""
        echo "============================================================"
        echo "  IMPORT DATA SHBJ BARU"
        echo "============================================================"
        echo "Seret dan lepas (drag-and-drop) file PDF atau Excel ke jendela ini,"
        echo "atau ketikkan path lengkap filenya."
        read -p "Path file: " filepath
        
        # Hapus tanda kutip jika ditarik/drop otomatis
        filepath=$(echo "$filepath" | tr -d "'\"" | trim)

        echo ""
        python3 "$(dirname "$0")/import_reference.py" "$filepath"
        echo ""
        read -p "Tekan Enter untuk kembali ke menu..."

    elif [ "$pilihan" == "3" ]; then
        exit 0
    else
        echo "Pilihan tidak valid!"
    fi
done
