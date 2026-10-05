"""
chat_engine.py — Reusable Gemini Chat Engine dengan Guardrails & SHBJ
=====================================================================

Kelas wrapper yang mengelola sesi chat Gemini dengan mekanisme
penjaminan kepatuhan (guardrails), injeksi data SHBJ, dan
ekstraksi JSON terstruktur setelah wawancara selesai.
"""

import re

from google import genai
from google.genai import types

from config import COMPLETION_TOKEN, GEMINI_API_KEY, MODEL_NAME, TEMPERATURE
from guardrails import InterviewState
from json_extractor import EXTRACTION_PROMPT, extract_json_from_response


class KAKInterviewBot:
    """Bot wawancara adaptif untuk penyusunan KAK/TOR.

    Mengelola sesi chat Gemini dengan system instruction yang sudah
    dikonfigurasi. Mengintegrasikan guardrails untuk memastikan
    bot tetap patuh pada alur wawancara, dan menyediakan mekanisme
    ekstraksi JSON setelah wawancara selesai.

    Attributes:
        chat: Objek chat session dari Gemini SDK.
        state: InterviewState yang melacak posisi wawancara.
    """

    def __init__(self, system_instruction: str) -> None:
        """Inisialisasi bot dengan system instruction."""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.system_instruction = system_instruction
        
        # Jalur model cadangan untuk menghindari Limit Kuota (429)
        self.fallback_models = [MODEL_NAME, "gemini-3.7-flash", "gemini-3.5-flash", "gemini-flash-lite-latest"]
        self.current_model_idx = 0

        self.chat = self.client.chats.create(
            model=self.fallback_models[self.current_model_idx],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=TEMPERATURE,
            ),
        )

        self.state = InterviewState()
        self._last_raw_response: str = ""

    def _switch_to_next_model(self) -> bool:
        """Berpindah ke model cadangan (recreate chat session) jika kena limit."""
        if self.current_model_idx < len(self.fallback_models) - 1:
            old_model = self.fallback_models[self.current_model_idx]
            self.current_model_idx += 1
            new_model = self.fallback_models[self.current_model_idx]
            alasan = "Limit Kuota (429)" 
            print(f"\n   ⚠️ {alasan} pada {old_model}. Mengalihkan sesi wawancara ke {new_model}...")
            
            # Recreate chat session sambil membawa history percakapan sebelumnya
            old_history = self.chat.get_history()
            self.chat = self.client.chats.create(
                model=new_model,
                history=old_history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=TEMPERATURE,
                ),
            )
            return True
        return False

    def _send_with_retry(self, message: str):
        """Kirim pesan ke Gemini dengan Retry dan Model Fallback."""
        import time
        max_retries = 10
        base_wait_time = 5
        
        for attempt in range(max_retries):
            try:
                return self.chat.send_message(message)
            except Exception as e:
                error_str = str(e)
                
                # Khusus untuk 429 (Limit) atau 404 (Model tidak ada): Coba ganti model terlebih dahulu
                if ("429" in error_str or "404" in error_str) and self._switch_to_next_model():
                    time.sleep(2)
                    continue # Lanjut ke percobaan berikutnya menggunakan model baru
                    
                if "503" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_wait_time * (2 ** attempt) 
                        if "429" in error_str:
                            wait_time = max(wait_time, 35) # Minimal 35 detik untuk 429
                        wait_time = min(wait_time, 40)  # Maksimal tunggu 40 detik per attempt
                        
                        kode_error = "429 (Semua Jalur Model Penuh)" if "429" in error_str else "503 (Server Sibuk)"
                        print(f"\n   ⚠️ {kode_error}. Menunggu {wait_time} detik... (Percobaan {attempt+2}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise e
                else:
                    raise e
        raise Exception("Gagal setelah retry maksimal.")

    def send_initial_trigger(self, trigger_message: str) -> str:
        """Kirim pesan pemicu pertama (tanpa context injection)."""
        try:
            response = self._send_with_retry(trigger_message)
            self._last_raw_response = response.text
            self.state.update_from_response(response.text)
            return self._clean_response(response.text)
        except Exception as e:
            return f"❌ Maaf, terjadi kesalahan pada server AI: {e}"

    def send_message(self, user_message: str) -> str:
        """Kirim pesan user dengan context injection."""
        augmented_message = self.state.build_context_reminder(user_message)
        try:
            response = self._send_with_retry(augmented_message)
            self._last_raw_response = response.text
            self.state.update_from_response(response.text)
            return self._clean_response(response.text)
        except Exception as e:
            return f"❌ Maaf, terjadi kesalahan pada server AI: {e}"

    def extract_structured_json(self) -> dict | None:
        """Kirim prompt ekstraksi JSON ke sesi chat yang sama."""
        try:
            response = self._send_with_retry(EXTRACTION_PROMPT)
            return extract_json_from_response(response.text)
        except Exception as e:
            print(f"\n❌ Gagal mengekstrak JSON: {e}")
            return None

    @staticmethod
    def _clean_response(response_text: str) -> str:
        """Bersihkan tag internal dari respons sebelum ditampilkan ke user.

        Menghapus tag [TAHAP_X] dan [KONTEKS SISTEM] yang tidak perlu
        dilihat oleh pengguna akhir.

        Args:
            response_text: Teks respons mentah dari bot.

        Returns:
            Teks respons yang sudah dibersihkan.
        """
        # Hapus tag tahap (e.g., [TAHAP_1], [TAHAP_OUTPUT])
        cleaned = re.sub(
            r"\[TAHAP[_\s]?\w+\]\s*", "", response_text
        )

        return cleaned.strip()

    def is_complete(self, response_text: str | None = None) -> bool:
        """Cek apakah wawancara sudah selesai.

        Args:
            response_text: Teks respons untuk dicek.
                           Jika None, gunakan respons terakhir.

        Returns:
            True jika respons mengandung token penyelesaian.
        """
        text = response_text or self._last_raw_response
        return COMPLETION_TOKEN in text

    @property
    def progress(self) -> str:
        """Dapatkan progress bar wawancara saat ini."""
        return self.state.progress_bar
