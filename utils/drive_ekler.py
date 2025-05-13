import os
import tempfile
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Google Drive yapılandırması
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = "service_account.json"
DRIVE_KLASORLERI = {
    "voluntary": "1sElqt4AN8CnV5XvhMlcVCrHh-otWxNsx",  # kendi klasör ID'ni buraya yaz
    # "hazard": "...", # ileride eklenebilir
}

_drive = None

def drive_baglan():
    global _drive
    if _drive is None:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
        gauth = GoogleAuth()
        gauth.credentials = credentials
        _drive = GoogleDrive(gauth)
    return _drive

def yukle_drive_dosya(dosya, tur, rapor_no):
    drive = drive_baglan()
    klasor_id = DRIVE_KLASORLERI.get(tur)
    if not klasor_id:
        return None

    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as tmp_file:
        tmp_file.write(dosya.read())
        tmp_file_path = tmp_file.name

    dosya_adi = f"{rapor_no}_{dosya.name}"
    gfile = drive.CreateFile({
        'title': dosya_adi,
        'parents': [{'id': klasor_id}]
    })
    gfile.SetContentFile(tmp_file_path)

    with st.status("📤 Dosya yükleniyor... bu birkaç saniye sürebilir", expanded=True) as status:
        gfile.Upload()
        gfile.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
        status.update(label="✅ Dosya başarıyla yüklendi!", state="complete")

    try:
        os.remove(tmp_file_path)
    except Exception as e:
        print("Geçici dosya silinemedi:", e)

    return f"https://drive.google.com/uc?id={gfile['id']}&export=download"

def listele_drive_dosyalar(tur, rapor_no):
    if not rapor_no:
        return []

    drive = drive_baglan()
    klasor_id = DRIVE_KLASORLERI.get(tur)
    if not klasor_id:
        return []

    try:
        query = f"'{klasor_id}' in parents and trashed=false and title contains '{rapor_no}_'"
        files = drive.ListFile({'q': query}).GetList()
        return [{"adi": f["title"], "url": f"https://drive.google.com/uc?id={f['id']}&export=download"} for f in files]
    except Exception as e:
        print("🚨 Listeleme hatası:", e)
        return []

def sil_drive_dosya(tur, rapor_no, dosya_adi):
    drive = drive_baglan()
    klasor_id = DRIVE_KLASORLERI.get(tur)
    if not klasor_id:
        return

    query = f"'{klasor_id}' in parents and trashed=false and title = '{rapor_no}_{dosya_adi}'"
    files = drive.ListFile({'q': query}).GetList()
    for f in files:
        f.Delete()
