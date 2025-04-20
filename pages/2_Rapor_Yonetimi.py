import streamlit as st
import pandas as pd
from datetime import datetime
from utils.veritabani import veritabani_baglanti_yap, tablolar_olustur
from utils.soru_yonetimi import yukle_sorular, soru_ekle, soru_sil, soru_var_mi, guncelle_soru
from utils.rapor_kayit import rapor_kaydet
import os
from utils.auth import login_required
login_required()

# Başlık
st.set_page_config(page_title="📄 Rapor Yönetimi", layout="wide")
st.title("📄 Rapor Yönetimi")

# Veritabanı başlat
conn = veritabani_baglanti_yap()
cursor = conn.cursor()
tablolar_olustur(cursor)
conn.commit()

# Rapor konuları
if "rapor_konulari" not in st.session_state:
    st.session_state["rapor_konulari"] = ["Uçuş Operasyonu", "Teknik", "Meydan","Diğer"]

sekme1, sekme2, sekme3 = st.tabs(["📝 Yeni Rapor Ekle", "⚙️ Ayarlar","📋 Kayıtlı Raporlar"])

with sekme1:
    # Form alanları
    st.subheader("Yeni Rapor Girişi")
    report_number = st.text_input("Rapor Numarası")
    rapor_turu = st.selectbox("Rapor Türü", ["Voluntary", "Hazard"], key="rapor_turu_yeni")
    rapor_konusu = st.selectbox("Rapor Konusu", st.session_state["rapor_konulari"])
    olay_tarihi = f"{st.date_input('Olay Tarihi')} {st.time_input('Olay Saati', value=datetime.now().time())}"
    veri_giris_tarihi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cevaplar = {}
    for idx, soru in enumerate(yukle_sorular()):
        if soru["rapor_turu"] == rapor_turu and rapor_konusu in soru["konular"]:
            key = f"soru_{idx}"
            if soru["tip"] == "text_input":
                cevaplar[soru["soru"]] = st.text_input(soru["soru"], key=key)
            elif soru["tip"] == "text_area":
                cevaplar[soru["soru"]] = st.text_area(soru["soru"], key=key)
            elif soru["tip"] == "selectbox":
                cevaplar[soru["soru"]] = st.selectbox(soru["soru"], soru.get("secenekler", []), key=key)

    if st.button("Kaydet"):
        basarili = rapor_kaydet(cursor, report_number, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, cevaplar)
        if basarili:
            conn.commit()
            st.success("✅ Rapor başarıyla kaydedildi.")
with sekme2:
    st.subheader("➕ Yeni Soru Tanımı")

    yeni_soru = st.text_input("Soru Başlığı")
    yeni_tip = st.selectbox("Soru Tipi", ["text_input", "text_area", "selectbox"])
    yeni_rapor_turu = st.selectbox("Rapor Türü", ["Voluntary", "Hazard"], key="rapor_turu_ayar")

    yeni_konular = st.multiselect("Konular", st.session_state["rapor_konulari"])
    yeni_secenekler = st.text_area("Seçenekler (virgülle ayrılmış)") if yeni_tip == "selectbox" else None

    if st.button("✅ Soruyu Kaydet"):
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

            if soru_var_mi(yeni_soru):
                guncelle_soru(yeni_soru, soru_dict)
                st.success("🔁 Soru güncellendi.")
            else:
                soru_ekle(soru_dict)
                st.success("✅ Soru eklendi.")

    st.divider()
    st.subheader("🗑️ Mevcut Sorular")
    for soru in yukle_sorular():
        col1, col2 = st.columns([8, 1])
        with col1:
            st.markdown(f"**{soru['soru']}** ({soru['tip']}, {soru['rapor_turu']})")
        with col2:
            if st.button("❌", key=f"sil_{soru['soru']}"):
                soru_sil(soru["soru"])
                st.success("🗑️ Soru silindi.")


with sekme3:
    st.subheader("📋 Tüm Raporlar")

    # Ana rapor listesi
    df_raporlar = pd.read_sql("SELECT * FROM raporlar", conn)
    st.markdown("### 🧾 Ana Rapor Listesi")
    st.dataframe(df_raporlar, use_container_width=True)

    st.markdown("---")

    # Voluntary Raporları
    st.markdown("### 📄 Voluntary Raporları")
    df_vol = pd.read_sql("SELECT * FROM voluntary_reports", conn)

    for _, row in df_vol.iterrows():
        rapor_no = row["report_number"]
        silme_key = f"vol_sil_{rapor_no}"
        with st.expander(f"📄 {rapor_no} - {row['rapor_konusu']}"):
            st.write(row)

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
                        cursor.execute("DELETE FROM voluntary_reports WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM voluntary_degerlendirme WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM voluntary_ekler WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM raporlar WHERE report_number = ?", (rapor_no,))
                        conn.commit()
                        st.success(f"🗑 {rapor_no} silindi.")
                        st.session_state[silme_key] = False
                        from utils.veritabani import veritabani_temizle

                        # Silme işlemlerinden sonra
                        veritabani_temizle(cursor)
                        conn.commit()
                        st.rerun()
                with col2:
                    if st.button("❌ Vazgeç", key=f"iptal_vol_{rapor_no}"):
                        st.session_state[silme_key] = False

    st.markdown("---")

    # Hazard Raporları
    st.markdown("### ⚠️ Hazard Raporları")
    df_haz = pd.read_sql("SELECT * FROM hazard_reports", conn)

    for _, row in df_haz.iterrows():
        rapor_no = row["report_number"]
        silme_key = f"haz_sil_{rapor_no}"
        with st.expander(f"⚠️ {rapor_no} - {row['rapor_konusu']}"):
            st.write(row)

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
                        cursor.execute("DELETE FROM hazard_reports WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM hazard_risk WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM hazard_onlem_coklu WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM hazard_progress WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM hazard_geri_izleme WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM hazard_kapanis WHERE report_number = ?", (rapor_no,))
                        cursor.execute("DELETE FROM raporlar WHERE report_number = ?", (rapor_no,))
                        conn.commit()

                        # Ekleri de sil
                        ek_klasor_path = os.path.join("uploads/hazard_ekler", rapor_no)
                        if os.path.exists(ek_klasor_path):
                            import shutil
                            shutil.rmtree(ek_klasor_path)

                        st.success(f"🗑 {rapor_no} silindi.")
                        st.session_state[silme_key] = False
                        st.experimental_rerun()
                with col2:
                    if st.button("❌ Vazgeç", key=f"iptal_haz_{rapor_no}"):
                        st.session_state[silme_key] = False
