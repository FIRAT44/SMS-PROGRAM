from utils.firebase_db import db

def get_risk(report_number):
    doc_ref = db.collection("voluntary_risk").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def kaydet_risk(report_number, data_dict):
    db.collection("voluntary_risk").document(report_number).set(data_dict)
