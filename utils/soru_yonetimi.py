import json
from typing import List, Dict, Optional

SORU_JSON_DOSYASI = "utils/sorular.json"

def yukle_sorular() -> List[Dict]:
    """JSON dosyasından tüm soruları yükler."""
    try:
        with open(SORU_JSON_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def kaydet_sorular(sorular: List[Dict]) -> None:
    """Soru listesini JSON dosyasına kaydeder."""
    with open(SORU_JSON_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sorular, f, ensure_ascii=False, indent=2)

def soru_ekle(yeni_soru: Dict) -> None:
    """Yeni bir soruyu listeye ekler ve dosyaya kaydeder."""
    sorular = yukle_sorular()
    sorular.append(yeni_soru)
    kaydet_sorular(sorular)

def soru_sil(soru_basligi: str) -> None:
    """Belirtilen başlıktaki soruyu listeden siler."""
    sorular = yukle_sorular()
    sorular = [s for s in sorular if s.get("soru") != soru_basligi]
    kaydet_sorular(sorular)

def soru_var_mi(soru_basligi: str) -> bool:
    """Belirtilen başlıktaki bir sorunun mevcut olup olmadığını kontrol eder."""
    return any(s.get("soru") == soru_basligi for s in yukle_sorular())

def guncelle_soru(eski_soru: str, yeni_soru: Dict) -> bool:
    """Mevcut bir soruyu başlığına göre günceller."""
    sorular = yukle_sorular()
    for idx, s in enumerate(sorular):
        if s.get("soru") == eski_soru:
            sorular[idx] = yeni_soru
            kaydet_sorular(sorular)
            return True
    return False
