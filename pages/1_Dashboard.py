import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import io
from utils.auth import login_required
login_required()

st.set_page_config(page_title="📊 SMS Dashboard", layout="wide")
st.title("📊 Emniyet Yönetim Sistemi Dashboard")

conn = sqlite3.connect("sms_database2.db", check_same_thread=False)

tab1, tab2 = st.tabs(["📋 Voluntary Dashboard", "⚠️ Hazard Dashboard"])

# 📥 Ortak Excel fonksiyonu
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Durumlar')
    writer.close()
    return output.getvalue()

# ✅ VOLUNTARY
with tab1:
    st.subheader("📋 Voluntary Bilgileri")

    def cek(s): return conn.execute(s).fetchone()[0]
    toplam = cek("SELECT COUNT(*) FROM voluntary_reports")
    sonuc = cek("SELECT COUNT(*) FROM voluntary_kapanis WHERE durum = 'Kapandı'")
    islem = cek("SELECT COUNT(*) FROM voluntary_kapanis WHERE durum = 'İşlemde'")

    c1, c2, c3 = st.columns(3)
    c1.metric("📝 Toplam Voluntary Rapor", toplam)
    c2.metric("✅ Sonuçlanan Voluntary Rapor", sonuc)

    # Grafik
    st.subheader("📅 Aylık Voluntary Rapor Sayısı")
    tip = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="v_grafik")
    renk = st.color_picker("Grafik Rengi", "#3b82f6", key="v_renk")

    dfv = pd.read_sql("""
        SELECT substr(olay_tarihi,1,7) AS Ay, COUNT(*) AS Adet
        FROM voluntary_reports WHERE olay_tarihi IS NOT NULL
        GROUP BY Ay ORDER BY Ay
    """, conn)

    if not dfv.empty:
        dfv["Adet"] = dfv["Adet"].astype(int)
        if tip == "Bar":
            fig = px.bar(dfv, x="Ay", y="Adet", text="Adet")
            fig.update_traces(marker_color=renk, textposition="outside")
        elif tip == "Line":
            fig = px.line(dfv, x="Ay", y="Adet", markers=True)
            fig.update_traces(line_color=renk, marker=dict(color=renk))
        else:
            fig = px.area(dfv, x="Ay", y="Adet")
            fig.update_traces(line_color=renk, fillcolor=renk)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Veri yok.")

    # Tablo
    st.subheader("📋 Kapanış & Değerlendirme Durumu")
    dfv2 = pd.read_sql("""
        SELECT vr.report_number, vr.olay_tarihi,
               COALESCE(vk.durum, 'Henüz Değerlendirilmedi') AS durum,
               COALESCE(vk.degerlendirme_tarihi, '-') AS degerlendirme,
               COALESCE(vk.kapanis_tarihi, '-') AS kapanis,
               COALESCE(vp.yuzde, 0) AS ilerleme
        FROM voluntary_reports vr
        LEFT JOIN voluntary_kapanis vk ON vr.report_number = vk.report_number
        LEFT JOIN voluntary_progress vp ON vr.report_number = vp.report_number
        ORDER BY olay_tarihi DESC
    """, conn)

    if not dfv2.empty:
        dfv2["Olay Tarihi"] = pd.to_datetime(dfv2["olay_tarihi"]).dt.strftime("%Y-%m-%d")
        dfv2["İlerleme"] = dfv2["ilerleme"].apply(lambda x: f"%{x}")
        dfv2 = dfv2.rename(columns={
            "report_number": "Rapor No", "durum": "Durum",
            "degerlendirme": "Değerlendirme Tarihi", "kapanis": "Kapanış Tarihi"
        })
        st.dataframe(dfv2, use_container_width=True)

        st.download_button("📥 Excel Olarak İndir", data=to_excel(dfv2),
                           file_name="voluntary_kapanis.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("📭 Kayıt yok.")

    # 📅 VOLUNTARY TARİH FİLTRESİ
    st.subheader("📅 Tarih Aralığına Göre Voluntary Rapor Sayısı")

    if not dfv2.empty:
        tarihler = pd.to_datetime(dfv2["Olay Tarihi"])
        min_tarih, max_tarih = tarihler.min(), tarihler.max()

        baslangic, bitis = st.date_input("Tarih Aralığı Seçin", [min_tarih, max_tarih], key="v_date")
        mask = (tarihler >= pd.to_datetime(baslangic)) & (tarihler <= pd.to_datetime(bitis))
        dfv_filtered = dfv2[mask]

        st.success(f"🔎 Seçilen tarihler arasında toplam **{len(dfv_filtered)}** voluntary rapor bulundu.")
    else:
        st.info("📭 Tarih filtresi için görüntülenecek kayıt bulunamadı.")


# ⚠️ HAZARD
with tab2:
    st.subheader("⚠️ Hazard Bilgileri")

    def cek_h(s): return conn.execute(s).fetchone()[0]
    toplam = cek_h("SELECT COUNT(*) FROM hazard_reports")
    sonuc = cek_h("SELECT COUNT(*) FROM hazard_kapanis WHERE durum = 'Kapandı'")
    islem = cek_h("SELECT COUNT(*) FROM hazard_kapanis WHERE durum = 'İşlemde'")

    c1, c2, c3 = st.columns(3)
    c1.metric("📝 Toplam Hazard Rapor", toplam)
    c2.metric("✅ Sonuçlanan Hazard Rapor", sonuc)

    # Grafik
    st.subheader("📅 Aylık Hazard Rapor Sayısı")
    tip = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="h_grafik")
    renk = st.color_picker("Grafik Rengi", "#f97316", key="h_renk")

    dfh = pd.read_sql("""
        SELECT substr(olay_tarihi,1,7) AS Ay, COUNT(*) AS Adet
        FROM hazard_reports WHERE olay_tarihi IS NOT NULL
        GROUP BY Ay ORDER BY Ay
    """, conn)

    if not dfh.empty:
        dfh["Adet"] = dfh["Adet"].astype(int)
        if tip == "Bar":
            fig = px.bar(dfh, x="Ay", y="Adet", text="Adet")
            fig.update_traces(marker_color=renk, textposition="outside")
        elif tip == "Line":
            fig = px.line(dfh, x="Ay", y="Adet", markers=True)
            fig.update_traces(line_color=renk, marker=dict(color=renk))
        else:
            fig = px.area(dfh, x="Ay", y="Adet")
            fig.update_traces(line_color=renk, fillcolor=renk)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Veri yok.")

    # Tablo
    st.subheader("📋 Kapanış & Değerlendirme Durumu")
    dfh2 = pd.read_sql("""
        SELECT hr.report_number, hr.olay_tarihi,
               COALESCE(hk.durum, 'Henüz Değerlendirilmedi') AS durum,
               COALESCE(hk.degerlendirme_tarihi, '-') AS degerlendirme,
               COALESCE(hk.kapanis_tarihi, '-') AS kapanis,
               COALESCE(hp.yuzde, 0) AS ilerleme
        FROM hazard_reports hr
        LEFT JOIN hazard_kapanis hk ON hr.report_number = hk.report_number
        LEFT JOIN hazard_progress hp ON hr.report_number = hp.report_number
        ORDER BY olay_tarihi DESC
    """, conn)

    if not dfh2.empty:
        dfh2["Olay Tarihi"] = pd.to_datetime(dfh2["olay_tarihi"]).dt.strftime("%Y-%m-%d")
        dfh2["İlerleme"] = dfh2["ilerleme"].apply(lambda x: f"%{x}")
        dfh2 = dfh2.rename(columns={
            "report_number": "Rapor No", "durum": "Durum",
            "degerlendirme": "Değerlendirme Tarihi", "kapanis": "Kapanış Tarihi"
        })
        st.dataframe(dfh2, use_container_width=True)

        st.download_button("📥 Excel Olarak İndir", data=to_excel(dfh2),
                           file_name="hazard_kapanis.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("📭 Kayıt yok.")

    # 📅 HAZARD TARİH FİLTRESİ
    st.subheader("📅 Tarih Aralığına Göre Hazard Rapor Sayısı")

    if not dfh2.empty:
        tarihler_h = pd.to_datetime(dfh2["Olay Tarihi"])
        min_t, max_t = tarihler_h.min(), tarihler_h.max()

        baslangic_h, bitis_h = st.date_input("Tarih Aralığı Seçin", [min_t, max_t], key="h_date")
        mask_h = (tarihler_h >= pd.to_datetime(baslangic_h)) & (tarihler_h <= pd.to_datetime(bitis_h))
        dfh_filtered = dfh2[mask_h]

        st.success(f"🔎 Seçilen tarihler arasında toplam **{len(dfh_filtered)}** hazard raporu bulundu.")
    else:
        st.info("📭 Tarih filtresi için görüntülenecek kayıt bulunamadı.")
