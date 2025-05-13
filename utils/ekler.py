import os
import streamlit as st

# Yerel dosya yolu
UPLOAD_KLASORLERI = {
    "voluntary": "uploads/voluntary_ekler",
    "hazard": "uploads/hazard_ekler"
}

def yukle_drive_dosya(dosya, tur, rapor_no):
    klasor_root = UPLOAD_KLASORLERI.get(tur)
    if not klasor_root:
        return None

    klasor_yolu = os.path.join(klasor_root, rapor_no)
    os.makedirs(klasor_yolu, exist_ok=True)

    dosya_yolu = os.path.join(klasor_yolu, dosya.name)

    if not os.path.exists(dosya_yolu):
        with open(dosya_yolu, "wb") as f:
            f.write(dosya.read())
        st.success(f"✅ Dosya başarıyla kaydedildi: {dosya.name}")
        return dosya_yolu
    else:
        st.info(f"ℹ️ Bu dosya zaten mevcut: {dosya.name}")
        return dosya_yolu

def listele_drive_dosyalar(tur, rapor_no):
    klasor_root = UPLOAD_KLASORLERI.get(tur)
    klasor_yolu = os.path.join(klasor_root, rapor_no)

    if not os.path.exists(klasor_yolu):
        return []

    return [
        {"adi": dosya, "url": os.path.join(klasor_yolu, dosya)}
        for dosya in os.listdir(klasor_yolu)
    ]

def sil_drive_dosya(tur, rapor_no, dosya_adi):
    klasor_root = UPLOAD_KLASORLERI.get(tur)
    klasor_yolu = os.path.join(klasor_root, rapor_no)
    dosya_yolu = os.path.join(klasor_yolu, dosya_adi)

    if os.path.exists(dosya_yolu):
        os.remove(dosya_yolu)