import streamlit as st
import pandas as pd
from google.cloud import firestore
from datetime import datetime

from utils.firebase_db import db
from utils.firestore_risk import get_risk
from utils.firestore_onlem import get_onlem
from utils.firestore_geri import get_geri_bildirim
from utils.firestore_kapanis import get_kapanis

# Firestore bağlantısı
from utils.firebase_db import db

# 🔧 Firestore değerlendirme güncelleme

def kaydet_degerlendirme_sonuc(report_number, veriler):
    doc_ref = db.collection("voluntary_degerlendirme").document(report_number)
    

    # 🔄 Değerlendirme sonrası progress güncelle
    progress_ref = db.collection("voluntary_progress").document(report_number)
    progress_doc = progress_ref.get()

    bolumler = {
    "Değerlendirme Paneli": False,
    "Risk Değerlendirme": False,
    "Önlemler ve Takip": False,
    "Geri Bildirim": False,
    "Durum ve Kapanış": False
}
    

    if veriler== "Risk Değerlendirme":
        bolumler = { "Risk Değerlendirme": True, }
    elif veriler== "Önlemler ve Takip":
        bolumler = {"Önlemler ve Takip": True,}
    elif veriler== "Geri Bildirim":
        bolumler = { "Geri Bildirim": True,}
    elif veriler== "Durum ve Kapanış":
        bolumler = { "Durum ve Kapanış": True}
    elif veriler== "Değerlendirme Paneli":
        bolumler = {"Değerlendirme Paneli": True}


    if progress_doc.exists:
        mevcut = progress_doc.to_dict()
        mevcut_eksikler = mevcut.get("eksikler", [])
        if isinstance(mevcut_eksikler, str):
            mevcut_eksikler = mevcut_eksikler.split(", ")
        for eksik in mevcut_eksikler:
            if eksik not in bolumler:
                bolumler[eksik] = False

    toplam = len(bolumler)
    tamamlanan = sum(1 for v in bolumler.values() if v)
    eksikler = [k for k, v in bolumler.items() if not v]
    yuzde = int((tamamlanan / toplam) * 100)

    progress_ref.set({
        "tamamlanan": tamamlanan,
        "toplam": toplam,
        "yuzde": yuzde,
        "eksikler": ", ".join(eksikler)
    }, merge=True)

def guncelle_progress(report_number):
    doc_ref = db.collection("voluntary_progress").document(report_number)

    def is_safe(func):
        try:
            return bool(func(report_number))
        except:
            return False

    bolumler = {
        "Değerlendirme Paneli": is_safe(get_degerlendirme),
        "Risk Değerlendirme": is_safe(get_risk),
        "Önlemler ve Takip": is_safe(get_onlem),
        "Geri Bildirim": is_safe(get_geri_bildirim),
        "Durum ve Kapanış": is_safe(get_kapanis)
    }

    tamamlanan = sum(1 for v in bolumler.values() if v)
    toplam = len(bolumler)
    eksikler = [k for k, v in bolumler.items() if not v]
    yuzde = int((tamamlanan / toplam) * 100)

    doc_ref.set({
        "tamamlanan": tamamlanan,
        "toplam": toplam,
        "yuzde": yuzde,
        "eksikler": ", ".join(eksikler)
    })

def get_degerlendirme(report_number):
    doc = db.collection("voluntary_degerlendirme").document(report_number).get()
    return doc.to_dict() if doc.exists else None

def kaydet_degerlendirme(report_number, veriler):
    doc_ref = db.collection("voluntary_degerlendirme").document(report_number)
    doc_ref.set(veriler)

    # 🔄 Değerlendirme sonrası progress güncelle
    progress_ref = db.collection("voluntary_progress").document(report_number)
    progress_doc = progress_ref.get()

    bolumler = {
        "Değerlendirme Paneli": True,  # sadece bu panelden güncelleniyor şu anda
        "Risk Değerlendirme": bool(get_risk(report_number)),
        "Önlemler ve Takip": bool(get_onlem(report_number)),
        "Geri Bildirim": bool(get_geri_bildirim(report_number)),
        "Durum ve Kapanış": bool(get_kapanis(report_number))
    }

    if progress_doc.exists:
        mevcut = progress_doc.to_dict()
        mevcut_eksikler = mevcut.get("eksikler", [])
        if isinstance(mevcut_eksikler, str):
            mevcut_eksikler = mevcut_eksikler.split(", ")
        for eksik in mevcut_eksikler:
            if eksik not in bolumler:
                bolumler[eksik] = False

    toplam = len(bolumler)
    tamamlanan = sum(1 for v in bolumler.values() if v)
    eksikler = [k for k, v in bolumler.items() if not v]
    yuzde = int((tamamlanan / toplam) * 100)

    progress_ref.set({
        "tamamlanan": tamamlanan,
        "toplam": toplam,
        "yuzde": yuzde,
        "eksikler": ", ".join(eksikler)
    }, merge=True)

# 🔍 Firestore tamamlanma durumu

def get_progress(report_number):
    doc_ref = db.collection("voluntary_progress").document(report_number)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def bolum_tamamlanma_goster(bolum_adi, report_number):
    tamamlanma = get_progress(report_number)
    if not tamamlanma:
        st.info("Henüz bu rapor için tamamlanma durumu hesaplanmadı.")
        return

    yuzde = tamamlanma.get("yuzde", 0)
    eksik = tamamlanma.get("eksikler", "").split(", ") if tamamlanma.get("eksikler") else []

    st.markdown("----")
    if bolum_adi in eksik:
        st.error(f"❌ Bu bölüm henüz tamamlanmamış: **{bolum_adi}**")
    else:
        st.success(f"✅ Bu bölüm tamamlanmış: **{bolum_adi}**")

    st.progress(yuzde / 100)
    st.caption(f"Genel ilerleme: **%{yuzde}**")
    



def goster_degerlendirme_paneli(report_number):
    st.subheader("🛠️ Değerlendirme Paneli")

    veri = get_degerlendirme(report_number)
    durumlar = ["Beklemede", "İşlemde", "Tamamlandı"]

    degerlendirme_durumu = st.selectbox("Değerlendirme Durumu", durumlar, index=durumlar.index(veri["degerlendirme_durumu"]) if veri else 0)
    sonuc_durumu = st.text_area("Sonuç Durumu", value=veri["sonuc_durumu"] if veri and "sonuc_durumu" in veri else "")
    geri_bildirim = st.text_area("Geri Bildirim", value=veri["geri_bildirim"] if veri and "geri_bildirim" in veri else "")
    atanan_kisi = st.text_input("Atanan Kişi", value=veri["atanan_kisi"] if veri and "atanan_kisi" in veri else "")
    atama_tarihi = st.date_input("Atama Tarihi", value=pd.to_datetime(veri["atama_tarihi"]).date() if veri and "atama_tarihi" in veri else datetime.today().date())

    if st.button("💾 Kaydet", key="btn_deg_kaydet"):
        kaydet_degerlendirme(report_number, {
            "degerlendirme_durumu": degerlendirme_durumu,
            "sonuc_durumu": sonuc_durumu,
            "geri_bildirim": geri_bildirim,
            "atanan_kisi": atanan_kisi,
            "atama_tarihi": str(atama_tarihi)
        })
        st.success("✅ Değerlendirme bilgileri Firestore'a kaydedildi.")

    if veri:
        st.markdown("---")
        st.markdown("### 📌 Kayıtlı Bilgiler")
        st.write(veri)

    # Bölüm tamamlanma durumu
    bolum_tamamlanma_goster("Değerlendirme Paneli", report_number)


def get_all_progress():
    docs = db.collection("voluntary_progress").stream()
    return [{**doc.to_dict(), "report_number": doc.id} for doc in docs]



