from utils.firebase_db import db
import json

def temizle_raporlar(tur="voluntary"):
    collection = "voluntary_reports" if tur == "voluntary" else "hazard_reports"
    silinenler = []
    docs = db.collection(collection).stream()

    for doc in docs:
        data = doc.to_dict()
        cevaplar = data.get("cevaplar")

        # Eğer cevaplar string ise (bozuksa) sil
        if isinstance(cevaplar, str):
            try:
                json.loads(cevaplar)  # kontrol et, parse edilebilir mi
                db.collection(collection).document(doc.id).delete()
                db.collection("raporlar").document(doc.id).delete()
                silinenler.append({
                    "report_number": doc.id,
                    "rapor_konusu": data.get("rapor_konusu", ""),
                    "rapor_turu": tur
                })
            except Exception:
                pass  # bozuk json, yine de silinmesin
    return silinenler
