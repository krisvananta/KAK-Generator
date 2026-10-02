"""
guardrails.py — Mekanisme Penjaminan Kepatuhan Bot
===================================================

Mengelola state wawancara dan menyediakan mekanisme untuk memastikan
bot tetap mematuhi alur pertanyaan yang telah ditentukan di blueprint.

Strategi:
- Lacak tahap wawancara saat ini dari tag [TAHAP_X] di respons bot.
- Injeksi pengingat konteks ke setiap pesan agar bot tidak "lupa".
- Deteksi tipe kegiatan (A/B/C) untuk validasi logika adaptif.
- Injeksi data SHBJ yang relevan di tahap anggaran (Q5-Q7).
"""

import re
from dataclasses import dataclass, field

from shbj_data import BUDGET_CONSTRAINTS_TEXT, SHBJData, load_shbj


# ---------------------------------------------------------------------------
# Label Tahap Wawancara
# ---------------------------------------------------------------------------

STAGE_LABELS: dict[int, str] = {
    1: "Identitas & Jenis Kegiatan",
    2: "Latar Belakang & Urgensi",
    3: "Maksud, Tujuan & Output",
    4: "Penerima Manfaat / Peserta",
    5: "Sumber Daya & Kualifikasi",
    6: "Metode & Alur",
    7: "Anggaran",
}

TOTAL_STAGES: int = len(STAGE_LABELS)

# Tahap-tahap di mana data SHBJ perlu diinjeksi
SHBJ_INJECTION_STAGES: set[int] = {5, 6, 7}


# ---------------------------------------------------------------------------
# State Tracker
# ---------------------------------------------------------------------------

@dataclass
class InterviewState:
    """Melacak posisi dan konteks wawancara saat ini.

    Attributes:
        current_stage: Nomor tahap pertanyaan saat ini (1-7).
        activity_type: Tipe kegiatan yang dipilih ("A", "B", atau "C").
        validated_stages: Set berisi nomor tahap yang sudah tervalidasi.
        shbj_injected: Apakah data SHBJ sudah pernah diinjeksi.
    """

    current_stage: int = 1
    activity_type: str = ""
    validated_stages: set[int] = field(default_factory=set)
    shbj_injected: bool = False

    # --- Deteksi dari Respons Bot ---

    @staticmethod
    def detect_stage_tag(response: str) -> int | None:
        """Ekstrak nomor tahap dari tag [TAHAP_X] di respons bot.

        Returns:
            Nomor tahap (1-7) jika ditemukan, None jika tidak.
        """
        match = re.search(r"\[TAHAP[_\s]?(\d)\]", response, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def detect_activity_type(response: str) -> str | None:
        """Deteksi tipe kegiatan (A/B/C) dari respons.

        Returns:
            "A", "B", atau "C" jika terdeteksi, None jika tidak.
        """
        match = re.search(r"Tipe\s+([ABC])", response, re.IGNORECASE)
        return match.group(1).upper() if match else None

    # --- Update State ---

    def update_from_response(self, response: str) -> None:
        """Perbarui state berdasarkan respons terakhir bot.

        Args:
            response: Teks respons dari bot.
        """
        detected_stage = self.detect_stage_tag(response)
        if detected_stage is not None:
            # Tandai stage sebelumnya sebagai selesai jika maju
            if detected_stage > self.current_stage:
                self.validated_stages.add(self.current_stage)
            self.current_stage = detected_stage

        if not self.activity_type:
            atype = self.detect_activity_type(response)
            if atype:
                self.activity_type = atype

    # --- Context Injection ---

    def build_context_reminder(self, user_message: str) -> str:
        """Bungkus pesan user dengan pengingat konteks untuk bot.

        Menyisipkan informasi tahap saat ini, tipe kegiatan, dan
        (jika tahap >= 5) data tarif SHBJ yang relevan.

        Args:
            user_message: Pesan asli dari pengguna.

        Returns:
            Pesan yang sudah di-augmentasi dengan konteks.
        """
        label = STAGE_LABELS.get(self.current_stage, "")

        parts = [
            "[KONTEKS SISTEM — jangan tampilkan bagian ini ke user]",
            f"Anda sedang di: PERTANYAAN {self.current_stage} — {label}.",
        ]

        if self.activity_type:
            parts.append(
                f"Tipe kegiatan yang dipilih user: Tipe {self.activity_type}."
            )

        parts.extend([
            "INGAT: Ajukan SATU pertanyaan saja per pesan.",
            "Validasi jawaban user sebelum lanjut ke tahap berikutnya.",
            f"Awali respons Anda dengan tag [TAHAP_{self.current_stage}].",
        ])

        # Injeksi data SHBJ di tahap 5-7 (sumber daya, metode, anggaran)
        if (
            self.current_stage in SHBJ_INJECTION_STAGES
            and self.activity_type
            and not self.shbj_injected
        ):
            shbj_text = self._get_shbj_context()
            if shbj_text:
                parts.append("")
                parts.append(shbj_text)
                self.shbj_injected = True
        elif (
            self.current_stage in SHBJ_INJECTION_STAGES
            and self.shbj_injected
        ):
            # Pengingat singkat bahwa SHBJ sudah diberikan
            parts.append("")
            parts.append(
                "PENGINGAT: Data tarif SHBJ sudah diberikan sebelumnya. "
                "Gunakan data tersebut untuk menghitung & memvalidasi anggaran. "
                "JANGAN suruh user mencari harga sendiri."
            )
            parts.append(BUDGET_CONSTRAINTS_TEXT)

        parts.extend([
            "[/KONTEKS SISTEM]",
            "",
            user_message,
        ])

        return "\n".join(parts)

    def _get_shbj_context(self) -> str:
        """Ambil data tarif SHBJ yang relevan untuk tipe kegiatan saat ini.

        Returns:
            String berisi tabel tarif SHBJ yang relevan, atau kosong.
        """
        if not self.activity_type:
            return ""

        shbj_data: SHBJData = load_shbj()
        shbj_text = shbj_data.format_for_injection(self.activity_type)

        return f"{shbj_text}\n\n{BUDGET_CONSTRAINTS_TEXT}"

    # --- Progress Display ---

    @property
    def progress_bar(self) -> str:
        """Buat progress bar visual untuk ditampilkan di terminal.

        Returns:
            String progress bar (contoh: "██████░ Tahap 6/7 — Metode & Alur").
        """
        filled = "█" * self.current_stage
        empty = "░" * (TOTAL_STAGES - self.current_stage)
        label = STAGE_LABELS.get(self.current_stage, "")
        return f"{filled}{empty} Tahap {self.current_stage}/{TOTAL_STAGES} — {label}"

    @property
    def is_all_stages_done(self) -> bool:
        """Cek apakah semua 7 tahap sudah tervalidasi."""
        return (
            len(self.validated_stages) >= TOTAL_STAGES - 1
            and self.current_stage == TOTAL_STAGES
        )
