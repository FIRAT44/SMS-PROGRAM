from utils.firebase_db import db

# 🔍 Tamamlanma durumu getir
def get_progress(report_number):
    doc_ref = db.collection("voluntary_progress").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

# 🔄 Tamamlanma durumu güncelle
def update_progress(report_number, bolum_verileri):
    doc_ref = db.collection("voluntary_progress").document(report_number)

    tamamlanan = sum(1 for k in bolum_verileri.values() if k)
    toplam = len(bolum_verileri)
    eksikler = [k for k, v in bolum_verileri.items() if not v]
    yuzde = int((tamamlanan / toplam) * 100)

    doc_ref.set({
        "tamamlanan": tamamlanan,
        "toplam": toplam,
        "yuzde": yuzde,
        "eksikler": ", ".join(eksikler)
    })

# 🔥 Rapor ve tüm ilişkili verileri sil (voluntary için)
def raporu_sil(report_number):
    paths = [
        ("voluntary_reports", report_number),
        ("voluntary_degerlendirme", report_number),
        ("voluntary_risk", report_number),
        ("voluntary_onlem", report_number),
        ("voluntary_geri_bildirim", report_number),
        ("voluntary_kapanis", report_number),
        ("voluntary_progress", report_number),
    ]
    for koleksiyon, belge_id in paths:
        db.collection(koleksiyon).document(belge_id).delete()
