import streamlit as st
from datetime import datetime
from utils.auth import goster_oturum_paneli
from utils.firestore_soru import yukle_sorular, soru_ekle, soru_sil, soru_var_mi, guncelle_soru
from utils.firestore_rapor import rapor_kaydet_firestore
from utils.firebase_db import db  # Firestore bağlantısı
from utils.firestore_rapor import raporlari_cek, rapor_sil
import pandas as pd
from utils.firestore_rapor import rapor_json_goster


goster_oturum_paneli()
st.title("📄 Rapor Yönetimi")

# Rapor konuları sabitlenmişse yükle
if "rapor_konulari" not in st.session_state:
    st.session_state["rapor_konulari"] = ["Uçuş Operasyonu", "Teknik", "Meydan", "Diğer"]

# Sekmeler
sekme1, sekme2, sekme3 = st.tabs(["📝 Yeni Rapor Ekle", "⚙️ Soru Ayarları", "📋 Tüm Raporlar"])


# --- SEKME 1: RAPOR GİRİŞ ---
with sekme1:
    st.subheader("Yeni Rapor Girişi")

    report_number = st.text_input("Rapor Numarası", key="yeni_rapor_no")
    rapor_turu = st.selectbox("Rapor Türü", ["Voluntary", "Hazard"], key="yeni_rapor_turu")
    rapor_konusu = st.selectbox("Rapor Konusu", st.session_state["rapor_konulari"], key="yeni_rapor_konusu")
    olay_tarihi = f"{st.date_input('Olay Tarihi')} {st.time_input('Olay Saati', value=datetime.now().time())}"
    veri_giris_tarihi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Soruları getir ve filtrele
    cevaplar = {}
    sorular = yukle_sorular(db)
    for idx, soru in enumerate(sorular):
        if soru["rapor_turu"] == rapor_turu and rapor_konusu in soru["konular"]:
            widget_key = f"cevap_{idx}_{soru['soru']}"
            if soru["tip"] == "text_input":
                cevaplar[soru["soru"]] = st.text_input(soru["soru"], key=widget_key)
            elif soru["tip"] == "text_area":
                cevaplar[soru["soru"]] = st.text_area(soru["soru"], key=widget_key)
            elif soru["tip"] == "selectbox":
                cevaplar[soru["soru"]] = st.selectbox(soru["soru"], soru.get("secenekler", []), key=widget_key)

    if st.button("💾 Kaydet", key="btn_kaydet_rapor"):
        if not report_number:
            st.warning("⚠️ Rapor numarası boş olamaz.")
        else:
            sonuc = rapor_kaydet_firestore(db, report_number, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, cevaplar)

            if sonuc == "duplicate":
                st.error(f"❌ {report_number} numaralı bir rapor zaten mevcut.")
            elif sonuc is True:
                st.success("✅ Rapor başarıyla Firestore'a kaydedildi.")
            else:
                st.error("❌ Bir hata oluştu, kayıt yapılamadı.")

# --- SEKME 2: SORU AYARLARI ---
with sekme2:
    st.subheader("➕ Yeni Soru Tanımı")

    yeni_soru = st.text_input("Soru Başlığı", key="yeni_soru")
    yeni_tip = st.selectbox("Soru Tipi", ["text_input", "text_area", "selectbox"], key="soru_tip")
    yeni_rapor_turu = st.selectbox("Rapor Türü", ["Voluntary", "Hazard"], key="soru_rapor_turu")
    yeni_konular = st.multiselect("Konular", st.session_state["rapor_konulari"], key="soru_konular")
    yeni_secenekler = st.text_area("Seçenekler (virgülle ayrılmış)", key="soru_secenekler") if yeni_tip == "selectbox" else None

    if st.button("✅ Soruyu Kaydet", key="btn_soru_kaydet"):
        if not yeni_soru or not yeni_konular:
            st.warning("⚠️ Lütfen tüm alanları doldurun.")
        else:
            soru_dict = {
                "soru": yeni_soru,
                "tip": yeni_tip,
                "rapor_turu": yeni_rapor_turu,
                "konular": yeni_konular
            }
            if yeni_tip == "selectbox" and yeni_secenekler:
                soru_dict["secenekler"] = [s.strip() for s in yeni_secenekler.split(",")]

            if soru_var_mi(db, yeni_soru):
                guncelle_soru(db, yeni_soru, soru_dict)
                st.success("🔁 Soru güncellendi.")
            else:
                soru_ekle(db, soru_dict)
                st.success("✅ Soru eklendi.")

    # Soru listesi
    st.divider()
    st.subheader("🗑️ Mevcut Sorular")

    for idx, soru in enumerate(sorular):
        col1, col2 = st.columns([8, 1])
        with col1:
            st.markdown(f"**{soru['soru']}** ({soru['tip']}, {soru['rapor_turu']})")
        with col2:
            if st.button("❌", key=f"soru_sil_{idx}"):
                soru_sil(db, soru["soru"])
                st.success("🗑️ Soru silindi.")
                st.rerun()

with sekme3:
    st.subheader("📋 Tüm Raporlar")

    st.markdown("### 📄 Voluntary Raporları")
    voluntary = raporlari_cek(db, "voluntary")
    df_vol = pd.DataFrame(voluntary)

    if not df_vol.empty:
        # 🔍 Arama kutusu
        arama = st.text_input("🔍 Rapor Numarası ile Ara (Voluntary)", key="arama_vol")

        # 🔎 Filtre uygula
        if arama:
            df_vol = df_vol[df_vol["report_number"].astype(str).str.contains(arama, case=False)]

        # 📋 Sürüklenebilir tablo
        st.dataframe(df_vol, use_container_width=True, height=400)

        for idx, row in df_vol.iterrows():
            rapor_no = row["report_number"]
            silme_key = f"vol_sil_{rapor_no}"

            with st.expander(f"📄 {rapor_no} - {row.get('rapor_konusu', '')}"):
                rapor_json_goster(row)

                if silme_key not in st.session_state:
                    st.session_state[silme_key] = False

                if not st.session_state[silme_key]:
                    if st.button(f"🗑 Sil ({rapor_no})", key=f"btn_vol_{rapor_no}"):
                        st.session_state[silme_key] = True
                else:
                    st.error(f"⚠️ {rapor_no} numaralı voluntary raporunu silmek istediğinize emin misiniz?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Evet, Sil", key=f"onay_vol_{rapor_no}"):
                            if rapor_sil(db, "voluntary", rapor_no):
                                st.success(f"🗑 {rapor_no} silindi.")
                                st.session_state[silme_key] = False
                                st.rerun()
                    with col2:
                        if st.button("❌ Vazgeç", key=f"iptal_vol_{rapor_no}"):
                            st.session_state[silme_key] = False
    else:
        st.info("📭 Voluntary rapor bulunamadı.")

    # 🔍 Hazard Raporları
    st.markdown("### ⚠️ Hazard Raporları")
    hazard = raporlari_cek(db, "hazard")
    df_haz = pd.DataFrame(hazard)

    if not df_haz.empty:
        arama_h = st.text_input("🔍 Rapor Numarası ile Ara (Hazard)", key="arama_haz")
        if arama_h:
            df_haz = df_haz[df_haz["report_number"].astype(str).str.contains(arama_h, case=False)]

        st.dataframe(df_haz, use_container_width=True, height=400)

        for idx, row in df_haz.iterrows():
            rapor_no = row["report_number"]
            silme_key = f"haz_sil_{rapor_no}"

            with st.expander(f"⚠️ {rapor_no} - {row.get('rapor_konusu', '')}"):
                rapor_json_goster(row)

                if silme_key not in st.session_state:
                    st.session_state[silme_key] = False

                if not st.session_state[silme_key]:
                    if st.button(f"🗑 Sil ({rapor_no})", key=f"btn_haz_{rapor_no}"):
                        st.session_state[silme_key] = True
                else:
                    st.error(f"⚠️ {rapor_no} numaralı hazard raporunu silmek istediğinize emin misiniz?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Evet, Sil", key=f"onay_haz_{rapor_no}"):
                            if rapor_sil(db, "hazard", rapor_no):
                                st.success(f"🗑 {rapor_no} silindi.")
                                st.session_state[silme_key] = False
                                st.rerun()
                    with col2:
                        if st.button("❌ Vazgeç", key=f"iptal_haz_{rapor_no}"):
                            st.session_state[silme_key] = False
    else:
        st.info("📭 Hazard raporu bulunamadı.")

    from utils.firestore_temizleyici import temizle_raporlar
    import pandas as pd

    with st.expander("🧹 Firestore Temizleyici"):
        st.caption("❗ Sadece test verilerini temizlemek içindir. Cevaplar alanı bozuk (string-json) olan tüm kayıtlar silinir.")

        if st.button("🧼 Voluntary Temizle"):
            silinenler = temizle_raporlar("voluntary")
            if silinenler:
                st.success(f"🗑 {len(silinenler)} kayıt silindi.")
                df = pd.DataFrame(silinenler)
                st.dataframe(df)
                st.download_button("📥 Log'u İndir (CSV)", df.to_csv(index=False), file_name="silinen_voluntary.csv")
            else:
                st.info("✅ Temiz, silinecek kayıt bulunamadı.")

        if st.button("🧼 Hazard Temizle"):
            silinenler = temizle_raporlar("hazard")
            if silinenler:
                st.success(f"🗑 {len(silinenler)} kayıt silindi.")
                df = pd.DataFrame(silinenler)
                st.dataframe(df)
                st.download_button("📥 Log'u İndir (CSV)", df.to_csv(index=False), file_name="silinen_hazard.csv")
            else:
                st.info("✅ Temiz, silinecek kayıt bulunamadı.")

    from utils.firestore_onarici import cevaplari_onar
    import pandas as pd

    with st.expander("🛠️ Cevap Alanı Onarıcı"):
        st.caption("📦 String olarak kaydedilmiş cevaplar alanlarını JSON formatına dönüştürür.")

        if st.button("♻️ Voluntary Cevapları Onar"):
            onarilanlar = cevaplari_onar("voluntary")
            st.success(f"🔧 {len(onarilanlar)} kayıt kontrol edildi.")
            df = pd.DataFrame(onarilanlar)
            st.dataframe(df)
            st.download_button("📥 Log'u İndir (CSV)", df.to_csv(index=False), file_name="onarilan_voluntary.csv")

        if st.button("♻️ Hazard Cevapları Onar"):
            onarilanlar = cevaplari_onar("hazard")
            st.success(f"🔧 {len(onarilanlar)} kayıt kontrol edildi.")
            df = pd.DataFrame(onarilanlar)
            st.dataframe(df)
            st.download_button("📥 Log'u İndir (CSV)", df.to_csv(index=False), file_name="onarilan_hazard.csv")
