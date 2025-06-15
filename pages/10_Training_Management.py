import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- Veritabanı bağlantısı ve tablo oluşturma ---
conn = sqlite3.connect("sms_training.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS sms_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        type TEXT NOT NULL,
        training_date TEXT NOT NULL,
        expiry_date TEXT NOT NULL
    )
""")
conn.commit()

st.set_page_config(page_title="SMS Training Management", layout="wide")
st.title("📊 SMS Training Management")

# --- Yeni Kayıt Formu ---
with st.form("sms_training_form", clear_on_submit=True):
    st.subheader("📝 Yeni SMS Eğitimi Ekle")
    col1, col2 = st.columns(2)
    with col1:
        isim = st.text_input("Çalışan Adı ve Soyadı")
        training_type = st.selectbox("Eğitim Tipi", ["SMS Course", "SMS Briefing"])
    with col2:
        training_date = st.date_input("Eğitim Tarihi", value=datetime.today().date())
        expiry_date   = st.date_input(
            "Geçerlilik Bitiş Tarihi", 
            value=(datetime.today() + timedelta(days=365)).date()
        )
    if st.form_submit_button("➕ Kaydet"):
        cursor.execute(
            "INSERT INTO sms_training (isim, type, training_date, expiry_date) VALUES (?, ?, ?, ?)",
            (isim, training_type, training_date.isoformat(), expiry_date.isoformat())
        )
        conn.commit()
        st.success(f"{isim} için “{training_type}” kaydedildi.")

# --- Veritabanından kayıtları çek ---
df = pd.read_sql_query(
    "SELECT * FROM sms_training ORDER BY expiry_date ASC",
    conn,
    parse_dates=["training_date", "expiry_date"]
)

if not df.empty:
    today = datetime.today()

    # --- Yaklaşan Süre Dolum Uyarısı ---
    upcoming = df[
        (df["expiry_date"] >= today) & 
        (df["expiry_date"] <= today + timedelta(days=30))
    ]
    if not upcoming.empty:
        st.warning("🚨 Aşağıdaki eğitimlerin geçerliliği önümüzdeki 30 gün içinde sona erecek:")
        upcoming = upcoming.assign(
            days_left=(upcoming["expiry_date"] - today).dt.days
        ).loc[:, ["isim","type","expiry_date","days_left"]]
        st.table(upcoming.sort_values("days_left"))
    else:
        st.success("✅ Önümüzdeki 30 gün içinde süre dolacak SMS eğitimi yok.")

    st.markdown("---")

    # --- Tüm Kayıtların Tablosu ---
    st.subheader("📋 Tüm SMS Eğitim Kayıtları")
    display_df = df.copy()
    display_df["training_date"] = display_df["training_date"].dt.strftime("%Y-%m-%d")
    display_df["expiry_date"]   = display_df["expiry_date"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df[["id","isim","type","training_date","expiry_date"]], use_container_width=True)

    # --- Kayıt Düzenleme ---
    st.markdown("---")
    st.subheader("✏️ Kayıt Düzenle")
    edit_id = st.selectbox("Düzenlenecek Kayıt ID'si", [None] + df["id"].tolist())
    if edit_id:
        rec = df[df["id"] == edit_id].iloc[0]
        with st.form("edit_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Çalışan Adı ve Soyadı", value=rec["isim"])
                new_type = st.selectbox("Eğitim Tipi", ["SMS Course", "SMS Briefing"], index=["SMS Course", "SMS Briefing"].index(rec["type"]))
            with col2:
                new_train = st.date_input("Eğitim Tarihi", value=rec["training_date"].date())
                new_expiry = st.date_input("Geçerlilik Bitiş Tarihi", value=rec["expiry_date"].date())
            if st.form_submit_button("🔄 Güncelle"):
                cursor.execute("""
                    UPDATE sms_training 
                    SET isim=?, type=?, training_date=?, expiry_date=? 
                    WHERE id=?
                """, (
                    new_name, new_type, new_train.isoformat(), new_expiry.isoformat(), edit_id
                ))
                conn.commit()
                st.success("Kayıt güncellendi.")
                st.experimental_rerun()

    # --- Kayıt Silme ---
    st.markdown("---")
    st.subheader("🗑️ Kayıt Sil")
    delete_id = st.selectbox("Silinecek Kayıt ID'si", [None] + df["id"].tolist(), key="del")
    if delete_id and st.button("🗑️ Sil"):
        cursor.execute("DELETE FROM sms_training WHERE id=?", (delete_id,))
        conn.commit()
        st.success(f"ID {delete_id} silindi.")
        st.experimental_rerun()

    # --- Grafikler ---
    st.markdown("---")
    st.markdown("### 📊 Eğitim Tipine Göre Dağılım")
    type_counts = df["type"].value_counts()
    st.bar_chart(type_counts)

    st.markdown("### 📈 Aylık Eğitim Bitiş Sayısı")
    df["month"] = df["expiry_date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month").size().rename("Adet")
    st.line_chart(monthly)

else:
    st.info("ℹ️ Henüz kayıt yok. Lütfen formu kullanarak yeni bir eğitim ekleyin.")
