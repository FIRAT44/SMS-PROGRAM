from utils.firebase_db import db
import json

def cevaplari_onar(tur="voluntary"):
    collection = "voluntary_reports" if tur == "voluntary" else "hazard_reports"
    onarilanlar = []

    docs = db.collection(collection).stream()
    for doc in docs:
        data = doc.to_dict()
        cevaplar = data.get("cevaplar")

        if isinstance(cevaplar, str):
            try:
                # Parse edilebiliyorsa dict yap ve geri yaz
                parsed = json.loads(cevaplar)
                db.collection(collection).document(doc.id).update({"cevaplar": parsed})
                onarilanlar.append({
                    "report_number": doc.id,
                    "rapor_konusu": data.get("rapor_konusu", ""),
                    "durum": "onarildi"
                })
            except Exception:
                onarilanlar.append({
                    "report_number": doc.id,
                    "rapor_konusu": data.get("rapor_konusu", ""),
                    "durum": "bozuk ve onarılamadı"
                })

    return onarilanlar

    