import streamlit as st
from utils.auth import login_required



st.title("📊 Continuous Improvement Tools")


import zipfile
import io
import os
import streamlit as st

def zip_veri_yedegi():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 📁 Veritabanı dosyasını ekle
        if os.path.exists("sms_database2.db"):
            zip_file.write("sms_database2.db", arcname="sms_database2.db")

        # 📁 Voluntary ekleri
        for root, _, files in os.walk("uploads/voluntary_ekler"):
            for file in files:
                tam_yol = os.path.join(root, file)
                zip_file.write(tam_yol, arcname=os.path.relpath(tam_yol, "uploads"))

        # 📁 Hazard ekleri
        for root, _, files in os.walk("uploads/hazard_ekler"):
            for file in files:
                tam_yol = os.path.join(root, file)
                zip_file.write(tam_yol, arcname=os.path.relpath(tam_yol, "uploads"))

    return zip_buffer.getvalue()

# 📦 Butonla indirilebilir hale getir
st.markdown("### 📥 Veri Yedeği")
st.download_button(
    label="📦 Tüm Sistemi ZIP Olarak İndir",
    data=zip_veri_yedegi(),
    file_name="sms_yedek.zip",
    mime="application/zip"
)


import streamlit as st
import zipfile
import os
import io
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

def drive_baglan():
    scope = ['https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)

def zip_yedek_olustur():
    bugun = datetime.now().strftime("%Y-%m-%d")
    zip_adi = f"sms_yedek_{bugun}.zip"
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 📦 Veritabanları
        for db_file in ["sms_database.db", "sms_database2.db", "sms_database3.db", "sms_occurrence.db"]:
            if os.path.exists(db_file):
                zip_file.write(db_file, arcname=db_file)

        # 📂 Uploads klasörleri
        for root, _, files in os.walk("uploads"):
            for file in files:
                tam_yol = os.path.join(root, file)
                rel_path = os.path.relpath(tam_yol, ".")
                zip_file.write(tam_yol, arcname=rel_path)

    return zip_adi, zip_buffer.getvalue()

def google_drive_yukle(zip_adi, zip_bytes, klasor_id=None):
    drive = drive_baglan()

    with open("temp_upload.zip", "wb") as f:
        f.write(zip_bytes)

    gfile = drive.CreateFile({
        'title': zip_adi,
        'parents': [{'id': klasor_id}] if klasor_id else []
    })
    gfile.SetContentFile("temp_upload.zip")
    gfile.Upload()

    try:
        os.remove("temp_upload.zip")
    except:
        pass

    st.success(f"✅ {zip_adi} dosyası Google Drive'da klasörüne yüklendi.")




# 🚀 Streamlit arayüz
DRIVE_KLASOR_ID = "1sElqt4AN8CnV5XvhMlcVCrHh-otWxNsx"  # senin gerçek klasör ID'n

if st.button("📦 Yedekle ve Google Drive'a gönder"):
    zip_adi, zip_bytes = zip_yedek_olustur()
    google_drive_yukle(zip_adi, zip_bytes, klasor_id=DRIVE_KLASOR_ID)



import streamlit as st
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# Google Drive klasör ID'n
DRIVE_KLASOR_ID = "1sElqt4AN8CnV5XvhMlcVCrHh-otWxNsx"

def drive_baglan():
    scope = ['https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)

def yedek_listele():
    st.title("📦 Google Drive Yedekleme Geçmişi")
    drive = drive_baglan()
    yedekler = drive.ListFile({'q': f"'{DRIVE_KLASOR_ID}' in parents and trashed=false"}).GetList()

    if not yedekler:
        st.info("📭 Henüz yedek bulunmuyor.")
        return

    for dosya in sorted(yedekler, key=lambda x: x['modifiedDate'], reverse=True):
        st.markdown(f"""
        - 🗂 **{dosya['title']}**
        - 🕒 Tarih: {dosya['modifiedDate'][:10]}
        - 🔗 [İndir]({dosya['alternateLink']})
        """)

st.subheader("📦 Yedekleme Geçmişi")
yedek_listele()
st.markdown("---")  

import streamlit as st
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import zipfile
import os

def drive_baglan():
    scope = ['https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)

def geri_yukle_google_drive_dosyasi(dosya_id):
    drive = drive_baglan()
    gfile = drive.CreateFile({'id': dosya_id})

    # Geçici dosyaya indir
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        gfile.GetContentFile(temp_file.name)
        st.success(f"✅ {gfile['title']} başarıyla indirildi.")

        # ZIP dosyasını aç
        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
            zip_ref.extractall(path=".")  # Mevcut klasöre açar
            st.success("📂 ZIP içeriği başarıyla çıkarıldı!")

        st.info("🟢 uploads/ klasörleri ve .db dosyaları geri yüklendi.")

st.title("🔁 Google Drive Yedek Geri Yükleme")

DRIVE_KLASOR_ID = "1sElqt4AN8CnV5XvhMlcVCrHh-otWxNsx"  # kendi klasör ID'n

drive = drive_baglan()
yedek_dosyalar = drive.ListFile({'q': f"'{DRIVE_KLASOR_ID}' in parents and trashed=false"}).GetList()

zip_yedekler = [f"{f['title']} || {f['id']}" for f in yedek_dosyalar if f['title'].endswith(".zip")]

if zip_yedekler:
    secilen = st.selectbox("📦 Geri Yüklenecek ZIP Dosyasını Seç", zip_yedekler)
    if st.button("🔁 ZIP Yedeğini Geri Yükle"):
        secilen_id = secilen.split("||")[1].strip()
        geri_yukle_google_drive_dosyasi(secilen_id)
else:
    st.info("⛔ Yedek ZIP dosyası bulunamadı.")