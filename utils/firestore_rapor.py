import streamlit as st

def rapor_kaydet_firestore(db, report_number, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, cevaplar):
    try:
        # 🔒 Önce aynı numara var mı kontrol et
        if db.collection("raporlar").document(report_number).get().exists:
            return "duplicate"

        # Ortak kayıt (raporlar)
        db.collection("raporlar").document(report_number).set({
            "report_number": report_number,
            "rapor_turu": rapor_turu,
            "rapor_konusu": rapor_konusu,
            "olay_tarihi": olay_tarihi,
            "veri_giris_tarihi": veri_giris_tarihi
        })

        # Detay kayıt
        detay_koleksiyon = "voluntary_reports" if rapor_turu.lower() == "voluntary" else "hazard_reports"
        db.collection(detay_koleksiyon).document(report_number).set({
            "report_number": report_number,
            "rapor_konusu": rapor_konusu,
            "olay_tarihi": olay_tarihi,
            "veri_giris_tarihi": veri_giris_tarihi,
            "cevaplar": cevaplar
        })

        return True
    except Exception as e:
        print("Firestore kayıt hatası:", e)
        return False


def raporlari_cek(db, tur="voluntary"):
    collection = "voluntary_reports" if tur == "voluntary" else "hazard_reports"
    docs = db.collection(collection).stream()
    return [doc.to_dict() for doc in docs]

def rapor_sil(db, tur, report_number):
    try:
        if tur == "voluntary":
            db.collection("voluntary_reports").document(report_number).delete()
        else:
            db.collection("hazard_reports").document(report_number).delete()

        db.collection("raporlar").document(report_number).delete()
        return True
    except Exception as e:
        print("Silme hatası:", e)
        return False


def rapor_json_goster(row):
    import json

    veri = {
        "report_number": row.get("report_number", ""),
        "rapor_konusu": row.get("rapor_konusu", ""),
        "olay_tarihi": row.get("olay_tarihi", ""),
        "veri_giris_tarihi": row.get("veri_giris_tarihi", "")
    }

    cevaplar = row.get("cevaplar", {})
    if isinstance(cevaplar, str):
        try:
            cevaplar = json.loads(cevaplar)
        except Exception:
            cevaplar = {}

    veri["cevaplar"] = cevaplar
    st.json(veri)


# VOLUNTARY RAPORLARINI GÖSTER
def get_voluntary_report_by_number(db, report_number):
    doc = db.collection("voluntary_reports").document(report_number).get()
    if doc.exists:
        return doc.to_dict()
    return None

import json

def parse_cevaplar(ozel_cevaplar):
    if isinstance(ozel_cevaplar, dict):
        return ozel_cevaplar
    if isinstance(ozel_cevaplar, str):
        try:
            return json.loads(ozel_cevaplar)
        except:
            return {}
    return {}