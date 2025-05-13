import os

# Klasör varsa oluşturma, yoksa oluştur
os.makedirs("utils", exist_ok=True)

#
from utils.firebase_db import db

def get_geri_bildirim(report_number):
    doc_ref = db.collection("voluntary_geri_bildirim").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def kaydet_geri_bildirim(report_number, veriler):
    doc_ref = db.collection("voluntary_geri_bildirim").document(report_number)
    doc_ref.set(veriler)



