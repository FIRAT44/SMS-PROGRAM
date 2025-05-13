from utils.firebase_db import db

def get_onlem(report_number):
    doc_ref = db.collection("voluntary_onlem").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def kaydet_onlem(report_number, data):
    db.collection("voluntary_onlem").document(report_number).set(data)
