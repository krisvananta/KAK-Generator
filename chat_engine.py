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
        
        # Jalur model cadangan untuk menghindari Limit Kuota (429) dan Server Sibuk (503)
        self.fallback_models = [
            MODEL_NAME, 
            "gemini-3.7-flash", 
            "gemini-3.5-flash", 
            "gemini-2.5-flash", 
            "gemini-flash-lite-latest"
        ]
        self.current_model_idx = 0
        self.highest_available_idx = 0  # Menyimpan kasta tertinggi yang belum limit 429

        self.chat = self.client.chats.create(
            model=self.fallback_models[self.current_model_idx],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=TEMPERATURE,
            ),
        )

        self.state = InterviewState()
        self._last_raw_response: str = ""

    def _switch_to_next_model(self, error_type: str = "Limit Kuota (429)") -> bool:
        """Berpindah ke model cadangan (recreate chat session) jika kena limit atau server error."""
        if "429" in error_type:
            # Jika kena limit, jangan pernah coba model ini lagi
            self.highest_available_idx = max(self.highest_available_idx, self.current_model_idx + 1)
            
        if self.current_model_idx < len(self.fallback_models) - 1:
            old_model = self.fallback_models[self.current_model_idx]
            self.current_model_idx += 1
            new_model = self.fallback_models[self.current_model_idx]
            
            print(f"\n   ⚠️ {error_type} pada {old_model}. Mengalihkan sesi wawancara ke {new_model}...")
            
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

    def _reset_to_best_model(self) -> None:
        """Kembalikan sesi wawancara ke model paling tinggi yang belum terkena limit 429."""
        if self.current_model_idx > self.highest_available_idx:
            self.current_model_idx = self.highest_available_idx
            best_model = self.fallback_models[self.current_model_idx]
            print(f"\n   🔄 Mencoba mengembalikan sesi ke model utama yang lebih pintar ({best_model})...")
            
            old_history = self.chat.get_history()
            self.chat = self.client.chats.create(
                model=best_model,
                history=old_history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=TEMPERATURE,
                ),
            )

    def _send_with_retry(self, message: str):
        """Kirim pesan ke Gemini dengan Retry dan Model Fallback."""
        import time
        max_retries = 20  # Naikkan sedikit karena kita banyak retry di per-model
        model_attempts = 0
        
        for attempt in range(max_retries):
            try:
                return self.chat.send_message(message)
            except Exception as e:
                error_str = str(e)
                
                error_type = ""
                is_transient = False
                if "429" in error_str: 
                    error_type = "Limit Kuota (429)"
                    is_transient = False # 429 BUKAN transient, jangan di-retry 3x
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
                            print(f"\n   ⚠️ {error_type}. Menunggu {wait_time} detik untuk coba lagi... (Percobaan {model_attempts}/3 pada model ini)")
                            time.sleep(wait_time)
                            continue
                            
                    # Jika 404 (permanen) atau sudah 3x gagal di model ini, turun kasta
                    if self._switch_to_next_model(error_type):
                        model_attempts = 0  # Reset untuk model baru
                        time.sleep(2)
                        continue
                        
                # Jika sudah di model kasta terendah dan masih gagal, masuk antrean panjang
                if "503" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 35 if "429" in error_str else 20
                        print(f"\n   ⚠️ Semua Jalur Model Penuh. Menunggu {wait_time} detik... (Sisa retries: {max_retries - attempt - 1})")
                        time.sleep(wait_time)
                    else:
                        raise e
                else:
                    raise e
        raise Exception("Gagal setelah retry maksimal.")

    def send_initial_trigger(self, trigger_message: str) -> str:
        """Kirim pesan pemicu pertama (tanpa context injection)."""
        try:
            self._reset_to_best_model()
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
            self._reset_to_best_model()
            response = self._send_with_retry(augmented_message)
            self._last_raw_response = response.text
            self.state.update_from_response(response.text)
            return self._clean_response(response.text)
        except Exception as e:
            return f"❌ Maaf, terjadi kesalahan pada server AI: {e}"

    def extract_structured_json(self) -> dict | None:
        """Kirim prompt ekstraksi JSON ke sesi chat yang sama."""
        try:
            self._reset_to_best_model()
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
