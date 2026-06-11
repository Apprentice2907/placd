import re
import json

def clean_and_parse_json(raw: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    text = match.group(1) if match else raw
    return json.loads(text.strip())
