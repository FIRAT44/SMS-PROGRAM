import streamlit as st
from firebase_admin import firestore
import pandas as pd
import plotly.express as px
from utils.auth import goster_oturum_paneli
from utils.helpers import temiz_key  # ← bu fonksiyonu utils/helpers.py dosyasına eklemelisin

# 🔐 Oturum paneli
goster_oturum_paneli()

# 🔒 Sadece admin erişebilir
if st.session_state.get("rol") != "admin":
    st.warning("🚫 Bu sayfaya sadece admin kullanıcı erişebilir.")
    st.stop()

st.title("👥 Kullanıcı Yönetimi Paneli")

# Firestore bağlantısı
db = firestore.client()
kullanicilar_ref = db.collection("kullanicilar")

# -----------------------------------------------
# ➕ Yeni kullanıcı ekleme
st.subheader("➕ Yeni Kullanıcı Ekle")
with st.form("yeni_kullanici_form"):
    yeni_email = st.text_input("📧 E-posta")
    yeni_rol = st.selectbox("🎚 Rol", ["admin", "egitmen", "ogrenci"])
    ad_soyad = st.text_input("👤 Ad Soyad (opsiyonel)")
    birim = st.text_input("🏢 Birim (opsiyonel)")
    ekle = st.form_submit_button("💾 Kaydet")

    if ekle:
        if not yeni_email:
            st.warning("⚠️ E-posta boş olamaz.")
        else:
            kullanicilar_ref.document(yeni_email).set({
                "rol": yeni_rol,
                "ad_soyad": ad_soyad,
                "birim": birim
            })
            st.success(f"✅ {yeni_email} başarıyla eklendi.")
            st.rerun()

# -----------------------------------------------
# 📋 Kullanıcıları oku
docs = kullanicilar_ref.stream()
kullanici_listesi = []
for doc in docs:
    data = doc.to_dict()
    kullanici_listesi.append({
        "email": doc.id,
        "rol": data.get("rol", "ogrenci"),
        "ad_soyad": data.get("ad_soyad", "-"),
        "birim": data.get("birim", "-")
    })

if not kullanici_listesi:
    st.info("📭 Henüz kayıtlı kullanıcı yok.")
    st.stop()

# -----------------------------------------------
# 📊 Rol dağılımı grafiği
st.subheader("📊 Rol Dağılımı")
df_kullanicilar = pd.DataFrame(kullanici_listesi)
rol_sayim = df_kullanicilar["rol"].value_counts().reset_index()
rol_sayim.columns = ["Rol", "Kullanıcı Sayısı"]
fig = px.pie(rol_sayim, names="Rol", values="Kullanıcı Sayısı", title="Kullanıcı Rol Dağılımı", hole=0.3)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------
# 🛠️ Kullanıcı listesi + güncelle/sil
st.subheader("🧾 Kullanıcı Listesi ve İşlemler")

ADMIN_EMAILS = ["admin@ayjet.com"]  # Koruma listesi

for kullanici in kullanici_listesi:
    temiz_id = temiz_key(kullanici["email"])
    with st.expander(f"👤 {kullanici['email']}"):
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"**Ad Soyad:** {kullanici['ad_soyad']}")
            st.markdown(f"**Birim:** {kullanici['birim']}")

        if kullanici["email"] in ADMIN_EMAILS:
            with col2:
                st.markdown("🛡️ Ana admin. Rol değiştirilemez.")
            with col3:
                st.markdown("🔒 Silme engellendi.")
        else:
            with col2:
                yeni_rol = st.selectbox(
                    "Rol Seç", ["admin", "egitmen", "ogrenci"],
                    index=["admin", "egitmen", "ogrenci"].index(kullanici["rol"]),
                    key="rol_" + temiz_id
                )
                if st.button("💾 Güncelle", key="guncelle_" + temiz_id):
                    kullanicilar_ref.document(kullanici["email"]).update({"rol": yeni_rol})
                    st.success(f"✅ {kullanici['email']} rolü güncellendi → `{yeni_rol}`")
                    st.rerun()

            with col3:
                sil_onay = st.checkbox("⚠️ Sil?", key="onay_" + temiz_id)
                if sil_onay:
                    if st.button("🗑 Sil", key="sil_" + temiz_id):
                        kullanicilar_ref.document(kullanici["email"]).delete()
                        st.success(f"🗑 {kullanici['email']} silindi.")
                        st.rerun()
