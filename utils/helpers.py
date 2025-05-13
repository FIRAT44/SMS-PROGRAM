import re

def temiz_key(deger: str):
    return re.sub(r'[^a-zA-Z0-9_]', '_', deger)