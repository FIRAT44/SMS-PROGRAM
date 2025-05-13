import firebase_admin
from firebase_admin import credentials, firestore, storage

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # kendi JSON dosyan
    firebase_admin.initialize_app(cred, {
        "storageBucket": "sms-project-17d1c.appspot.com"  # 👈 BU KISIM ŞART
    })

db = firestore.client()
