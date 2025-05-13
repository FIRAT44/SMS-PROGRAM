import streamlit as st
import pandas as pd
import plotly.express as px
import io
from collections import Counter

from utils.auth import require_login, goster_oturum_paneli
from utils.firebase_db import db

#goster_oturum_paneli()

st.title("📊 Emniyet Yönetim Sistemi Dashboard")

tab1, tab2 = st.tabs(["📋 Voluntary Dashboard", "⚠️ Hazard Dashboard"])


def to_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Durumlar")
    writer.close()
    return output.getvalue()


# 📋 Voluntary Dashboard
with tab1:
    st.subheader("📋 Voluntary Bilgileri")

    # Koleksiyon isimleri
    VOL_COL = "voluntary_reports"
    VOL_KAP_COL = "voluntary_kapanis"
    VOL_PROG_COL = "voluntary_progress"

    # Metri̇kler
    vol_docs = list(db.collection(VOL_COL).stream())
    toplam = len(vol_docs)
    kapandi_docs = list(
    db.collection(VOL_KAP_COL)
      .where("durum", "==", "Kapandı")
      .stream())
    sonuc_docs = list(
    db.collection(VOL_KAP_COL)
      .where("durum", "==", "Kapandı")
      .stream())
    sonuc = len(sonuc_docs)
    islem_docs   = list(db.collection(VOL_KAP_COL)
                       .where("durum", "==", "İşlemde")
                       .stream())
    islem = len(islem_docs)

    c1, c2, c3 = st.columns(3)
    c1.metric("📝 Toplam Voluntary Rapor", toplam)
    c2.metric("✅ Sonuçlanan Voluntary Rapor", sonuc)
    c3.metric("🕐 İşlemde Olan Voluntary Rapor", islem)

    # Aylık Grafik
    st.subheader("📅 Aylık Voluntary Rapor Sayısı")
    tip = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="v_grafik")
    renk = st.color_picker("Grafik Rengi", "#3b82f6", key="v_renk")

    counter = Counter()
    for doc in db.collection(VOL_COL).stream():
        data = doc.to_dict()
        tarih = data.get("olay_tarihi", "")
        if isinstance(tarih, str) and len(tarih) >= 7:
            counter[tarih[:7]] += 1

    dfv = pd.DataFrame(sorted(counter.items()), columns=["Ay", "Adet"])
    if not dfv.empty:
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

    # Tablo: Kapanış & İlerleme
    # Tablo: Kapanış & İlerleme
    st.subheader("📋 Kapanış & Değerlendirme Durumu")

    # 1) voluntary_reports belgelerini liste olarak al
    vol_snaps = list(db.collection(VOL_COL).stream())

    # 2) Kapanış ve ilerleme koleksiyonlarını doküman ID → veri dict şeklinde al
    kap_map = {snap.id: snap.to_dict() for snap in db.collection(VOL_KAP_COL).stream()}
    prog_map = {snap.id: snap.to_dict() for snap in db.collection(VOL_PROG_COL).stream()}

    # 3) Her voluntary rapor için satır oluştur
    rows = []
    for snap in vol_snaps:
        doc = snap.to_dict()
        rn  = snap.id                          # doküman ID'si == report_number
        olay = doc.get("olay_tarihi", "")

        k = kap_map.get(rn, {})                # kapanış kaydı
        p = prog_map.get(rn, {})               # ilerleme kaydı

        rows.append({
            "Rapor No":             rn,
            "Olay Tarihi":          (olay[:10] if isinstance(olay, str) else "-"),
            "Durum":                k.get("durum", "Henüz Değerlendirilmedi"),
            "Değerlendirme Tarihi": k.get("degerlendirme_tarihi", "-"),
            "Kapanış Tarihi":       k.get("kapanis_tarihi", "-"),
            "İlerleme":             f"%{p.get('yuzde', 0)}"
        })

    # 4) DataFrame’e çevir ve göster
    dfv2 = pd.DataFrame(rows).sort_values("Olay Tarihi", ascending=False)

    if not dfv2.empty:
        st.dataframe(dfv2, use_container_width=True)
        st.download_button(
            "📥 Excel Olarak İndir",
            data=to_excel(dfv2),
            file_name="voluntary_kapanis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📭 Kayıt yok.")

    # Tarih filtresi (üniform şekilde)
    st.subheader("📅 Tarih Aralığına Göre Voluntary Rapor Sayısı")
    if not dfv2.empty:
        tarihler = pd.to_datetime(dfv2["Olay Tarihi"], errors="coerce")
        min_t, max_t = tarihler.min().date(), tarihler.max().date()
        bas_date, bit_date = st.date_input("Tarih Aralığı Seçin", [min_t, max_t], key="v_date")
        bas, bit = pd.to_datetime(bas_date), pd.to_datetime(bit_date)

        mask = (tarihler >= bas) & (tarihler <= bit)
        df_filtered = dfv2[mask]
        st.success(f"🔎 Seçilen tarihler arasında **{len(df_filtered)}** adet voluntary rapor bulundu.")
    else:
        st.info("📭 Tarih filtresi için veri yok.")

# ⚠️ Hazard Dashboard
with tab2:
    st.subheader("⚠️ Hazard Bilgileri")

    HAZ_COL = "hazard_reports"
    HAZ_KAP_COL = "hazard_kapanis"
    HAZ_PROG_COL = "hazard_progress"

    haz_docs = list(db.collection(HAZ_COL).stream())
    toplam_h = len(haz_docs)
    kapandi_docs = list(
    db.collection(HAZ_KAP_COL)
      .where("durum", "==", "Kapandı")
      .stream())
    sonuc_h = len(kapandi_docs)

    islemde_docs = list(
    db.collection(HAZ_KAP_COL)
      .where("durum", "==", "İşlemde")
      .stream())
    islem_h = len(islemde_docs)

    c1, c2, c3 = st.columns(3)
    c1.metric("📝 Toplam Hazard Rapor", toplam_h)
    c2.metric("✅ Sonuçlanan Hazard Rapor", sonuc_h)
    c3.metric("🕐 İşlemde Olan Hazard Rapor", islem_h)

    # Aylık Grafik
    st.subheader("📅 Aylık Hazard Rapor Sayısı")
    tip_h = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="h_grafik")
    renk_h = st.color_picker("Grafik Rengi", "#f97316", key="h_renk")

    counter_h = Counter()
    for doc in db.collection(HAZ_COL).stream():
        tarih = doc.to_dict().get("olay_tarihi", "")
        if isinstance(tarih, str) and len(tarih) >= 7:
            counter_h[tarih[:7]] += 1

    dfh = pd.DataFrame(sorted(counter_h.items()), columns=["Ay", "Adet"])
    if not dfh.empty:
        if tip_h == "Bar":
            fig = px.bar(dfh, x="Ay", y="Adet", text="Adet")
            fig.update_traces(marker_color=renk_h, textposition="outside")
        elif tip_h == "Line":
            fig = px.line(dfh, x="Ay", y="Adet", markers=True)
            fig.update_traces(line_color=renk_h, marker=dict(color=renk_h))
        else:
            fig = px.area(dfh, x="Ay", y="Adet")
            fig.update_traces(line_color=renk_h, fillcolor=renk_h)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Veri yok.")

    # Tablo: Kapanış & İlerleme
    kap_h_docs = [d.to_dict() for d in db.collection(HAZ_KAP_COL).stream()]
    prog_h_docs = [d.to_dict() for d in db.collection(HAZ_PROG_COL).stream()]

    rows_h = []
    for doc in haz_docs:
        r = doc.to_dict()
        rn = r.get("report_number")
        olay = r.get("olay_tarihi", "")
        kap = next((k for k in kap_h_docs if k.get("report_number") == rn), {})
        prog = next((p for p in prog_h_docs if p.get("report_number") == rn), {})
        rows_h.append({
            "Rapor No": rn,
            "Olay Tarihi": olay[:10] if isinstance(olay, str) else "-",
            "Durum": kap.get("durum", "Henüz Değerlendirilmedi"),
            "Değerlendirme Tarihi": kap.get("degerlendirme_tarihi", "-"),
            "Kapanış Tarihi": kap.get("kapanis_tarihi", "-"),
            "İlerleme": f"%{prog.get('yuzde', 0)}"
        })

    dfh2 = pd.DataFrame(rows_h).sort_values("Olay Tarihi", ascending=False)
    if not dfh2.empty:
        st.dataframe(dfh2, use_container_width=True)
        st.download_button(
            "📥 Excel Olarak İndir",
            data=to_excel(dfh2),
            file_name="hazard_kapanis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📭 Kayıt yok.")

    # Tarih filtresi
    # ⚠️ Hazard Tarih Filtre
    st.subheader("📅 Tarih Aralığına Göre Hazard Rapor Sayısı")
    if not dfh2.empty:
        tarihler_h = pd.to_datetime(dfh2["Olay Tarihi"], errors="coerce")
        min_h = tarihler_h.min().date()
        max_h = tarihler_h.max().date()
        bas_h_date, bit_h_date = st.date_input(
            "Tarih Aralığı Seçin",
            [min_h, max_h],
            key="h_date"
        )
        bas_h = pd.to_datetime(bas_h_date)
        bit_h = pd.to_datetime(bit_h_date)

        mask_h = (tarihler_h >= bas_h) & (tarihler_h <= bit_h)
        dfh_filtered = dfh2[mask_h]

        st.success(f"🔎 Seçilen tarihler arasında toplam **{len(dfh_filtered)}** hazard rapor bulundu.")
    else:
        st.info("📭 Tarih filtresi için görüntülenecek kayıt bulunamadı.")
































# import streamlit as st
# import sqlite3
# import pandas as pd
# import plotly.express as px
# import io

# from utils.auth import require_login
# from utils.auth import goster_oturum_paneli
# require_login()
# goster_oturum_paneli()


# st.title("📊 Emniyet Yönetim Sistemi Dashboard")

# conn = sqlite3.connect("sms_database2.db", check_same_thread=False)

# tab1, tab2 = st.tabs(["📋 Voluntary Dashboard", "⚠️ Hazard Dashboard"])

# # 📥 Ortak Excel fonksiyonu
# def to_excel(df):
#     output = io.BytesIO()
#     writer = pd.ExcelWriter(output, engine='xlsxwriter')
#     df.to_excel(writer, index=False, sheet_name='Durumlar')
#     writer.close()
#     return output.getvalue()

# # ✅ VOLUNTARY
# with tab1:
#     st.subheader("📋 Voluntary Bilgileri")

#     def cek(s): return conn.execute(s).fetchone()[0]
#     toplam = cek("SELECT COUNT(*) FROM voluntary_reports")
#     sonuc = cek("SELECT COUNT(*) FROM voluntary_kapanis WHERE durum = 'Kapandı'")
#     islem = cek("SELECT COUNT(*) FROM voluntary_kapanis WHERE durum = 'İşlemde'")

#     c1, c2, c3 = st.columns(3)
#     c1.metric("📝 Toplam Voluntary Rapor", toplam)
#     c2.metric("✅ Sonuçlanan Voluntary Rapor", sonuc)

#     # Grafik
#     st.subheader("📅 Aylık Voluntary Rapor Sayısı")
#     tip = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="v_grafik")
#     renk = st.color_picker("Grafik Rengi", "#3b82f6", key="v_renk")

#     dfv = pd.read_sql("""
#         SELECT substr(olay_tarihi,1,7) AS Ay, COUNT(*) AS Adet
#         FROM voluntary_reports WHERE olay_tarihi IS NOT NULL
#         GROUP BY Ay ORDER BY Ay
#     """, conn)

#     if not dfv.empty:
#         dfv["Adet"] = dfv["Adet"].astype(int)
#         if tip == "Bar":
#             fig = px.bar(dfv, x="Ay", y="Adet", text="Adet")
#             fig.update_traces(marker_color=renk, textposition="outside")
#         elif tip == "Line":
#             fig = px.line(dfv, x="Ay", y="Adet", markers=True)
#             fig.update_traces(line_color=renk, marker=dict(color=renk))
#         else:
#             fig = px.area(dfv, x="Ay", y="Adet")
#             fig.update_traces(line_color=renk, fillcolor=renk)
#         st.plotly_chart(fig, use_container_width=True)
#     else:
#         st.info("📭 Veri yok.")

#     # Tablo
#     st.subheader("📋 Kapanış & Değerlendirme Durumu")
#     dfv2 = pd.read_sql("""
#         SELECT vr.report_number, vr.olay_tarihi,
#                COALESCE(vk.durum, 'Henüz Değerlendirilmedi') AS durum,
#                COALESCE(vk.degerlendirme_tarihi, '-') AS degerlendirme,
#                COALESCE(vk.kapanis_tarihi, '-') AS kapanis,
#                COALESCE(vp.yuzde, 0) AS ilerleme
#         FROM voluntary_reports vr
#         LEFT JOIN voluntary_kapanis vk ON vr.report_number = vk.report_number
#         LEFT JOIN voluntary_progress vp ON vr.report_number = vp.report_number
#         ORDER BY olay_tarihi DESC
#     """, conn)

#     if not dfv2.empty:
#         dfv2["Olay Tarihi"] = pd.to_datetime(dfv2["olay_tarihi"]).dt.strftime("%Y-%m-%d")
#         dfv2["İlerleme"] = dfv2["ilerleme"].apply(lambda x: f"%{x}")
#         dfv2 = dfv2.rename(columns={
#             "report_number": "Rapor No", "durum": "Durum",
#             "degerlendirme": "Değerlendirme Tarihi", "kapanis": "Kapanış Tarihi"
#         })
#         st.dataframe(dfv2, use_container_width=True)

#         st.download_button("📥 Excel Olarak İndir", data=to_excel(dfv2),
#                            file_name="voluntary_kapanis.xlsx",
#                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
#     else:
#         st.info("📭 Kayıt yok.")

#     # 📅 VOLUNTARY TARİH FİLTRESİ
#     st.subheader("📅 Tarih Aralığına Göre Voluntary Rapor Sayısı")

#     if not dfv2.empty:
#         tarihler = pd.to_datetime(dfv2["Olay Tarihi"])
#         min_tarih, max_tarih = tarihler.min(), tarihler.max()

#         baslangic, bitis = st.date_input("Tarih Aralığı Seçin", [min_tarih, max_tarih], key="v_date")
#         mask = (tarihler >= pd.to_datetime(baslangic)) & (tarihler <= pd.to_datetime(bitis))
#         dfv_filtered = dfv2[mask]

#         st.success(f"🔎 Seçilen tarihler arasında toplam **{len(dfv_filtered)}** voluntary rapor bulundu.")
#     else:
#         st.info("📭 Tarih filtresi için görüntülenecek kayıt bulunamadı.")


# # ⚠️ HAZARD
# with tab2:
#     st.subheader("⚠️ Hazard Bilgileri")

#     def cek_h(s): return conn.execute(s).fetchone()[0]
#     toplam = cek_h("SELECT COUNT(*) FROM hazard_reports")
#     sonuc = cek_h("SELECT COUNT(*) FROM hazard_kapanis WHERE durum = 'Kapandı'")
#     islem = cek_h("SELECT COUNT(*) FROM hazard_kapanis WHERE durum = 'İşlemde'")

#     c1, c2, c3 = st.columns(3)
#     c1.metric("📝 Toplam Hazard Rapor", toplam)
#     c2.metric("✅ Sonuçlanan Hazard Rapor", sonuc)

#     # Grafik
#     st.subheader("📅 Aylık Hazard Rapor Sayısı")
#     tip = st.selectbox("Grafik türü", ["Bar", "Line", "Area"], key="h_grafik")
#     renk = st.color_picker("Grafik Rengi", "#f97316", key="h_renk")

#     dfh = pd.read_sql("""
#         SELECT substr(olay_tarihi,1,7) AS Ay, COUNT(*) AS Adet
#         FROM hazard_reports WHERE olay_tarihi IS NOT NULL
#         GROUP BY Ay ORDER BY Ay
#     """, conn)

#     if not dfh.empty:
#         dfh["Adet"] = dfh["Adet"].astype(int)
#         if tip == "Bar":
#             fig = px.bar(dfh, x="Ay", y="Adet", text="Adet")
#             fig.update_traces(marker_color=renk, textposition="outside")
#         elif tip == "Line":
#             fig = px.line(dfh, x="Ay", y="Adet", markers=True)
#             fig.update_traces(line_color=renk, marker=dict(color=renk))
#         else:
#             fig = px.area(dfh, x="Ay", y="Adet")
#             fig.update_traces(line_color=renk, fillcolor=renk)
#         st.plotly_chart(fig, use_container_width=True)
#     else:
#         st.info("📭 Veri yok.")

#     # Tablo
#     st.subheader("📋 Kapanış & Değerlendirme Durumu")
#     dfh2 = pd.read_sql("""
#         SELECT hr.report_number, hr.olay_tarihi,
#                COALESCE(hk.durum, 'Henüz Değerlendirilmedi') AS durum,
#                COALESCE(hk.degerlendirme_tarihi, '-') AS degerlendirme,
#                COALESCE(hk.kapanis_tarihi, '-') AS kapanis,
#                COALESCE(hp.yuzde, 0) AS ilerleme
#         FROM hazard_reports hr
#         LEFT JOIN hazard_kapanis hk ON hr.report_number = hk.report_number
#         LEFT JOIN hazard_progress hp ON hr.report_number = hp.report_number
#         ORDER BY olay_tarihi DESC
#     """, conn)

#     if not dfh2.empty:
#         dfh2["Olay Tarihi"] = pd.to_datetime(dfh2["olay_tarihi"]).dt.strftime("%Y-%m-%d")
#         dfh2["İlerleme"] = dfh2["ilerleme"].apply(lambda x: f"%{x}")
#         dfh2 = dfh2.rename(columns={
#             "report_number": "Rapor No", "durum": "Durum",
#             "degerlendirme": "Değerlendirme Tarihi", "kapanis": "Kapanış Tarihi"
#         })
#         st.dataframe(dfh2, use_container_width=True)

#         st.download_button("📥 Excel Olarak İndir", data=to_excel(dfh2),
#                            file_name="hazard_kapanis.xlsx",
#                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
#     else:
#         st.info("📭 Kayıt yok.")

#     # 📅 HAZARD TARİH FİLTRESİ
#     st.subheader("📅 Tarih Aralığına Göre Hazard Rapor Sayısı")

#     if not dfh2.empty:
#         tarihler_h = pd.to_datetime(dfh2["Olay Tarihi"])
#         min_t, max_t = tarihler_h.min(), tarihler_h.max()

#         baslangic_h, bitis_h = st.date_input("Tarih Aralığı Seçin", [min_t, max_t], key="h_date")
#         mask_h = (tarihler_h >= pd.to_datetime(baslangic_h)) & (tarihler_h <= pd.to_datetime(bitis_h))
#         dfh_filtered = dfh2[mask_h]

#         st.success(f"🔎 Seçilen tarihler arasında toplam **{len(dfh_filtered)}** hazard raporu bulundu.")
#     else:
#         st.info("📭 Tarih filtresi için görüntülenecek kayıt bulunamadı.")
