from utils.firebase_db import db
import pandas as pd


def get_kapanis(report_number):
    doc_ref = db.collection("voluntary_kapanis").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def kaydet_kapanis(report_number, veri):
    db.collection("voluntary_kapanis").document(report_number).set(veri)


def get_all_kapanis_with_report_info():
    reports_ref = db.collection("voluntary_reports").stream()
    data = []
    for doc in reports_ref:
        report = doc.to_dict()
        report_number = doc.id
        kapanis_ref = db.collection("voluntary_kapanis").document(report_number).get()
        kapanis = kapanis_ref.to_dict() if kapanis_ref.exists else {}
        row = {
            "report_number": report_number,
            "rapor_turu": report.get("rapor_turu"),
            "rapor_konusu": report.get("rapor_konusu"),
            "olay_tarihi": report.get("olay_tarihi"),
            "durum": kapanis.get("durum") if kapanis else None
        }
        data.append(row)
    return pd.DataFrame(data)