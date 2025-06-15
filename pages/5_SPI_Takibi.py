import streamlit as st
import pandas as pd
import sqlite3
from utils.auth import login_required
#login_required()


st.set_page_config(page_title="📊 Olay Sayısı Girişi", layout="wide")
st.title("📊 Çeyrek Bazlı Olay Dağılımı")

DB_PATH = "sms_occurrence.db"

def get_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT term, indicator, count FROM occurrence_stats", conn)
    conn.close()
    return df

def update_or_insert(term, indicator, count):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM occurrence_stats WHERE term = ? AND indicator = ?", (term, indicator))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE occurrence_stats SET count = ? WHERE term = ? AND indicator = ?", (count, term, indicator))
    else:
        cursor.execute("INSERT INTO occurrence_stats (term, indicator, count) VALUES (?, ?, ?)", (term, indicator, count))
    conn.commit()
    conn.close()

def insert_empty_term(term, indicators):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for ind in indicators:
        cursor.execute("SELECT COUNT(*) FROM occurrence_stats WHERE term = ? AND indicator = ?", (term, ind))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO occurrence_stats (term, indicator, count) VALUES (?, ?, 0)", (term, ind))
    conn.commit()
    conn.close()

def delete_entry(term, indicator):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE occurrence_stats SET count = 0 WHERE term = ? AND indicator = ?", (term, indicator))
    cursor.execute("DELETE FROM occurrence_details WHERE term = ? AND indicator = ?", (term, indicator))
    conn.commit()
    conn.close()

def init_aircraft_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Uçak tipleri tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Uçaklar (tescil + tipi) tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircrafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg TEXT UNIQUE,
            type_id INTEGER,
            FOREIGN KEY (type_id) REFERENCES aircraft_types(id)
        )
    """)

    conn.commit()
    conn.close()
# Uygulama başlarken tabloyu oluştur
init_aircraft_tables()




# Veriyi al
df = get_data()
df["count"] = df["count"].fillna(0).astype(int)
all_indicators = sorted(df["indicator"].unique())

# TAB SİSTEMİ BAŞLANGICI
sekme1, sekme2, sekme3, sekme4, sekme5, sekme6 = st.tabs(["📋 Sayısal Özet", "📝 Veri Girişi", "📄 Detaylı Kayıtlar", "⚙️ Ayarlar","📈 Grafiksel Analiz", "📊 Uçuş Saati Oranı"])


with sekme1:
    st.subheader("📊 Term ve İndikatörlere Göre Olay Sayısı")
    pivot_df = df.pivot(index="term", columns="indicator", values="count").fillna(0).astype(int)
    st.dataframe(pivot_df, use_container_width=True)

    st.subheader("🗂️ Term Seç veya Yeni Term Ekle")
    terms = sorted(df["term"].unique(), reverse=True)
    term_choice = st.selectbox("📅 Var olan bir Term seçin veya yeni bir Term yazın:", terms + ["Yeni Term Ekle..."])

    if term_choice == "Yeni Term Ekle...":
        new_term = st.text_input("🆕 Yeni Term Girin (örn: 2025-2)")
        if new_term and new_term not in terms:
            insert_empty_term(new_term, all_indicators)
            st.success(f"✅ Yeni term '{new_term}' oluşturuldu ve tüm indikatörler 0 olarak eklendi.")
            selected_term = new_term
        else:
            selected_term = new_term
    else:
        selected_term = term_choice

    if selected_term:
        st.subheader(f"📄 {selected_term} dönemine ait olay verileri")
        filtered_df = df[df["term"] == selected_term]
        st.dataframe(filtered_df.pivot(index="term", columns="indicator", values="count").fillna(0).astype(int), use_container_width=True)

with sekme2:
    st.subheader("📝 Yeni Değer Gir veya Güncelle")
    selected_term = st.selectbox("📅 Term Seç", sorted(df["term"].unique(), reverse=True), key="giris_term")
    with st.form("entry_form"):
        indicator = st.selectbox("🛠️ İndikatör Seç", all_indicators)

        # Ayarlardan uçak tipi ve tescil listelerini al
        conn = sqlite3.connect(DB_PATH)
        types_df = pd.read_sql_query("SELECT deger FROM ayarlar WHERE kategori = 'tip'", conn)
        regs_df = pd.read_sql_query("SELECT deger FROM ayarlar WHERE kategori = 'tescil'", conn)
        conn.close()
        col1, col2, col3 = st.columns(3)
        with col1:
            olay_numarasi = st.text_input("📄 Olay Numarası")
            olay_tarihi = st.date_input("📆 Olay Tarihi")
            raporlayan = st.text_input("👤 Olayı Raporlayan")
            geri_besleme = st.text_area("💬 Geri Besleme")
        with col2:
            olay_grubu = st.text_input("🧩 Olay Grubu")
            olay_yeri = st.text_input("📍 Olay Yeri")
            ucak_tipi = st.selectbox("✈️ Uçak Tipi", types_df["deger"].tolist())
            ucak_tescili = st.selectbox("🔢 Uçak Tescili", regs_df["deger"].tolist())
        with col3:
            olay_ozeti = st.text_area("📝 Olay Özeti")
            bagli_rapor_no = st.text_input("🔗 Bağlantılı Rapor No")
            rapor_tipi = st.selectbox("📂 Rapor Tipi", ["", "hazard", "voluntary"])

        submitted = st.form_submit_button("💾 Kaydet / Güncelle")
        if submitted:
            # count hesaplama yapılacak
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM occurrence_details WHERE term = ? AND indicator = ?", (selected_term, indicator))
            yeni_count = cursor.fetchone()[0] + 1
            update_or_insert(selected_term, indicator, yeni_count)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO occurrence_details (
                    term, indicator, count, olay_numarasi, olay_tarihi, raporlayan, geri_besleme,
                    olay_grubu, olay_yeri, ucak_tipi, ucak_tescili, olay_ozeti,
                    bagli_rapor_no, rapor_tipi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                selected_term, indicator, yeni_count,
                olay_numarasi, olay_tarihi.strftime("%Y-%m-%d"), raporlayan, geri_besleme,
                olay_grubu, olay_yeri, ucak_tipi, ucak_tescili, olay_ozeti,
                bagli_rapor_no, rapor_tipi
            ))
            conn.commit()
            conn.close()
            st.success("✅ Kayıt başarıyla eklendi!")
            st.rerun()

    st.subheader("🗑️ Kayıt Sil")
    with st.form("silme_form"):
        sil_term = st.selectbox("📅 Term", sorted(df["term"].unique(), reverse=True), key="sil_term")
        sil_indicator = st.selectbox("🛠️ İndikatör", all_indicators, key="sil_indikator")

        # Olay numaraları alalım
        with sqlite3.connect(DB_PATH) as conn:
            query = "SELECT DISTINCT olay_numarasi FROM occurrence_details WHERE term = ? AND indicator = ? AND olay_numarasi IS NOT NULL ORDER BY olay_numarasi"
            olay_numaralari = pd.read_sql_query(query, conn, params=(sil_term, sil_indicator))["olay_numarasi"].dropna().tolist()

            query_count = "SELECT DISTINCT count FROM occurrence_details WHERE term = ? AND indicator = ? AND (olay_numarasi IS NULL OR olay_numarasi = '') ORDER BY count DESC"
            sil_count_list = pd.read_sql_query(query_count, conn, params=(sil_term, sil_indicator))["count"].tolist()

        sil_olay_no = st.selectbox("📄 Olay Numarası", olay_numaralari)

        confirm = st.checkbox("⚠️ Bu kaydı silmek istediğinizden emin misiniz?")
        sil = st.form_submit_button("❌ Sil")

        if sil and confirm:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM occurrence_details WHERE term = ? AND indicator = ? AND olay_numarasi = ?", (sil_term, sil_indicator, sil_olay_no))
                cursor.execute("SELECT COUNT(*) FROM occurrence_details WHERE term = ? AND indicator = ?", (sil_term, sil_indicator))
                guncel_count = cursor.fetchone()[0]
                cursor.execute("UPDATE occurrence_stats SET count = ? WHERE term = ? AND indicator = ?", (guncel_count, sil_term, sil_indicator))
                conn.commit()
            st.success("🗑️ Kayıt başarıyla silindi.")
            st.rerun()



with sekme3:
    st.subheader("📄 Girilen Detaylı Olay Kayıtları")
    try:
        conn = sqlite3.connect(DB_PATH)
        details_df = pd.read_sql_query("SELECT * FROM occurrence_details", conn)
        conn.close()
        if not details_df.empty:
            st.dataframe(details_df, use_container_width=True)
        else:
            st.info("📭 Henüz detaylı kayıt girilmemiş.")
    except Exception as e:
        st.error(f"Veri okunurken bir hata oluştu: {e}")



with sekme4:
    st.subheader("⚙️ Uçak Ayarları")
    kategori = st.selectbox("Kategori Seç", ["tip", "tescil"])
    yeni_deger = st.text_input("Yeni Değer Girin")

    if st.button("➕ Ekle"):
        if yeni_deger:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO ayarlar (kategori, deger) VALUES (?, ?)", (kategori, yeni_deger))
                conn.commit()
                st.success("✅ Değer eklendi.")
            except sqlite3.IntegrityError:
                st.warning("⚠️ Bu değer zaten mevcut.")
            conn.close()
        else:
            st.warning("Lütfen bir değer girin.")

    conn = sqlite3.connect(DB_PATH)
    ayar_df = pd.read_sql_query("SELECT * FROM ayarlar", conn)
    conn.close()

    st.markdown("### ✈️ Uçak Tipleri")
    st.dataframe(ayar_df[ayar_df["kategori"] == "tip"].reset_index(drop=True), use_container_width=True)

    st.markdown("### 🔢 Uçak Tescilleri")
    st.dataframe(ayar_df[ayar_df["kategori"] == "tescil"].reset_index(drop=True), use_container_width=True)

import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import tempfile
import os



with sekme5:
    st.header("📊 İndikatör Bazlı Ortalama ve Seviye Grafikleri")

    try:
        df_oran = pd.read_sql_query("SELECT * FROM occurrence_stats", sqlite3.connect(DB_PATH))
        df_oran["count"] = df_oran["count"].fillna(0).astype(float)
        df_oran["count"] = df_oran["count"].fillna(0).astype(float)

        selected_indicator = st.selectbox("İndikatör Seç", sorted(df_oran["indicator"].unique()))
        sub_df = df_oran[df_oran["indicator"] == selected_indicator].copy()
        sub_df = sub_df.sort_values(by="term")

        ortalama = sub_df["count"].mean()
        std = sub_df["count"].std()
        first = ortalama + std
        second = ortalama + 2 * std
        third = ortalama + 3 * std

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(sub_df["term"], sub_df["count"], marker='o', label=f"{selected_indicator} Değerleri", color='royalblue')
        ax.axhline(ortalama, color='gray', linestyle='--', label=f"Ortalama: {ortalama:.2f}")
        ax.axhline(first, color='green', linestyle='--', label=f"1. Seviye: {first:.2f}")
        ax.axhline(second, color='orange', linestyle='--', label=f"2. Seviye: {second:.2f}")
        ax.axhline(third, color='red', linestyle='--', label=f"3. Seviye: {third:.2f}")

        ax.set_title(f"{selected_indicator} - Ortalama ve Seviye Grafiği")
        ax.set_xlabel("Term")
        ax.set_xticklabels(sub_df["term"], rotation=90, fontsize=6)
        ax.set_ylabel("Olay Sayısı")
        ax.legend(fontsize=5, loc='upper right')
        ax.grid(True)

        # 📊 1., 2. ve 3. Seviye Eşik Aşımı Tabloları
        def build_threshold_table(df, lower, upper, label):
            temp = df[(df["count"] > lower) & (df["count"] <= upper)].copy()
            temp["Seviye"] = label
            return temp

        t1 = build_threshold_table(sub_df, first, second, "1. Seviye Aşımı")
        t2 = build_threshold_table(sub_df, second, third, "2. Seviye Aşımı")
        t3 = build_threshold_table(sub_df, third, float('inf'), "3. Seviye Aşımı")
        threshold_df = pd.concat([t1, t2, t3])[['term', 'count', 'Seviye']].reset_index(drop=True)

        if not threshold_df.empty:
            st.subheader("🚨 Eşik Aşımı Olayları")
            st.dataframe(threshold_df, use_container_width=True)
        else:
            st.success("Hiçbir term eşikleri aşmamış.")
        threshold_df = sub_df[sub_df["count"] > third].copy()
        threshold_df = threshold_df[["term", "count"]]
        threshold_df["Seviye"] = "3. Seviye Üzeri"

        if not threshold_df.empty:
            st.subheader("🚨 Eşik Aşımı Olayları")
            st.dataframe(threshold_df.reset_index(drop=True), use_container_width=True)
        else:
            st.success("Hiçbir term 3. seviyeyi aşmamış.")

        # Grafik indirme
        st.subheader("📥 Grafiği İndir")
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format="png", dpi=300)
        st.download_button(
            label="📷 PNG olarak indir",
            data=img_buffer.getvalue(),
            file_name=f"{selected_indicator}_grafik.png",
            mime="image/png"
        )

        st.pyplot(fig)
        df_oran = pd.read_sql_query("SELECT * FROM occurrence_stats", sqlite3.connect(DB_PATH))
        df_oran["count"] = df_oran["count"].fillna(0).astype(float)

        # Eşik aşımı noktalarını işaretle
        for i, row in sub_df.iterrows():
            if row["count"] > third:
                ax.annotate(f"{row['count']:.1f}", (i, row["count"]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=6, color='red')

    except Exception as e:
        st.error(f"Grafik çizilirken hata oluştu: {e}")


with sekme6:
    st.subheader("📊 1000 Uçuş Saatine Göre Olay Oranları")

    # Tüm Term ve Indicator sayıları
    olay_df = df.copy()

    # Uçuş saatlerini kullanıcıdan al
    st.markdown("### 🛫 Her Term için Uçuş Saatini Girin")
    unique_terms = sorted(olay_df["term"].unique())

    ucus_saatleri = {}
    for term in unique_terms:
        ucus_saatleri[term] = st.number_input(f"{term} için uçuş saati", min_value=1.0, step=1.0, key=f"ucus_{term}")

    # Uçuş saatlerini df'e ekle
    olay_df["ucus_saati"] = olay_df["term"].map(ucus_saatleri)

    # Oran hesapla
    olay_df["1000_saatte_oran"] = (olay_df["count"] / olay_df["ucus_saati"]) * 1000
    olay_df["1000_saatte_oran"] = olay_df["1000_saatte_oran"].round(3)

    st.markdown("### 📊 Oranlı Tablo")
    st.dataframe(
        olay_df[["term", "indicator", "count", "ucus_saati", "1000_saatte_oran"]],
        use_container_width=True
    )

    st.markdown("### 📉 İndikatör Bazında Ortalama (1000 Saat Başına)")

    ortalama_oran_df = (
        olay_df.groupby("indicator")["1000_saatte_oran"]
        .mean()
        .reset_index()
        .rename(columns={"1000_saatte_oran": "ortalama_oran"})
    )

    ortalama_oran_df["ortalama_oran"] = ortalama_oran_df["ortalama_oran"].round(3)

    st.dataframe(ortalama_oran_df, use_container_width=True)

    st.markdown("### 📉 İndikatör Bazında Ortalama ve Standart Sapma (1000 Saat Başına)")

    istatistik_df = (
        olay_df.groupby("indicator")["1000_saatte_oran"]
        .agg(ortalama_oran="mean", standart_sapma="std")
        .reset_index()
    )

    istatistik_df["ortalama_oran"] = istatistik_df["ortalama_oran"].round(3)
    istatistik_df["standart_sapma"] = istatistik_df["standart_sapma"].round(3)

    st.dataframe(istatistik_df, use_container_width=True)


    st.markdown("### 📊 Seviye Tabanlı Eşik Değerler (1000 Saat Başına)")

    istatistik_df = (
        olay_df.groupby("indicator")["1000_saatte_oran"]
        .agg(ortalama_oran="mean", standart_sapma="std")
        .reset_index()
    )

    istatistik_df["first_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 1
    istatistik_df["second_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 2
    istatistik_df["third_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 3

    istatistik_df = istatistik_df.round(3)

    st.dataframe(
        istatistik_df[[
            "indicator", "ortalama_oran", "standart_sapma",
            "first_level", "second_level", "third_level"
        ]],
        use_container_width=True
)
