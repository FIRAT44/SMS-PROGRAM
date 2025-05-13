import streamlit as st
from utils.auth import login_required
import sqlite3


st.title("📊 Training Management")

import firebase_admin
from firebase_admin import credentials, firestore

# Firebase'e bağlan
cred = credentials.Certificate("firebase_key.json")  # kendi JSON dosyan
firebase_admin.initialize_app(cred)
db = firestore.client()

# sqlite bağlantısı
conn = sqlite3.connect("sms_database2.db")
cursor = conn.cursor()

# Örnek: voluntary_reports tablosunu al
cursor.execute("SELECT * FROM voluntary_reports")
rows = cursor.fetchall()

# Sütun adlarını çek
columns = [col[0] for col in cursor.description]

# Firebase'e aktar
for row in rows:
    data = dict(zip(columns, row))
    doc_id = data.get("report_number", None)
    if doc_id:
        db.collection("voluntary_reports").document(doc_id).set(data)


docs = db.collection("voluntary_reports").stream()
for doc in docs:
    print(f"{doc.id} => {doc.to_dict()}")