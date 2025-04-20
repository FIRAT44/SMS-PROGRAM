import streamlit as st
from utils.auth import login_required
login_required()

st.set_page_config(page_title="Kaza/Olay", layout="wide")
st.title("📊 Kaza/Olay")

import sqlite3
import os

db_dosyalar = [
    "sms_database.db",
    "sms_database2.db",
    "sms_database3.db",
]

def tum_tablolari_temizle(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablolar = cursor.fetchall()
    for (isim,) in tablolar:
        if isim != "sqlite_sequence":  # otomatik artan ID tablosunu silme
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {isim}")
            except Exception as e:
                print(f"Hata (drop {isim}):", e)
    conn.commit()


# if st.button("Tüm Tabloları Sıfırla"):
#     for db in db_dosyalar:
#         if os.path.exists(db):
#             print(f"🗑 Sıfırlanıyor: {db}")
#             conn = sqlite3.connect(db)
#             tum_tablolari_temizle(conn)
#             conn.close()
#             print(f"✅ {db} sıfırlandı.")
#         else:
#             print(f"❌ Dosya bulunamadı: {db}")
#     st.write("Tüm tablolar sıfırlandı.")
#     st.write("Artık yeni kayıtlar ekleyebilirsiniz.")