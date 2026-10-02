import sys
sys.stdout.reconfigure(encoding='utf-8')
from config import *
from prompts import *
from guardrails import InterviewState
from shbj_data import load_shbj
from chat_engine import KAKInterviewBot
from json_extractor import extract_json_from_response

print('✅ All modules import OK')
print(f'Model: {MODEL_NAME} | Temp: {TEMPERATURE}')
print(f'Pagu DPA: Rp {PAGU_DPA_MAKSIMAL:,}')
d = load_shbj()
print(f'SHBJ: {len(d.sections)} sections loaded')
s = InterviewState()
print(f'Progress: {s.progress_bar}')
test_json = extract_json_from_response('```json\n{"test": true}\n```')
print(f'JSON extractor: {test_json}')
