import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import tempfile
import plotly.express as px
import zipfile
import os

#st.set_page_config(page_title="📄 Emniyet ", layout="wide")
#st.title(" Emniyet Toplantı Takip Sistemi")


# Veritabanı bağlantısı
conn = sqlite3.connect("sms_database.db")
cursor = conn.cursor()



def ensure_column_exists(conn, table_name, column_name, column_type="TEXT"):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [col[1] for col in c.fetchall()]
    if column_name not in existing_columns:
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS emniyet_toplantilari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    toplanti_tipi TEXT,
    tarih TEXT,
    konu TEXT,
    katilimcilar TEXT,
    kararlar TEXT,
    durum TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS karar_takip (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    toplantino TEXT,
    karar_no TEXT,
    toplanti_karari TEXT,
    sorumlu_makam TEXT,
    termin DATE,
    uygulama_durumu TEXT,
    notlar TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS katilimcilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isim TEXT,
    gorev TEXT
)
""")


def karar_silme():
    cursor.execute("""
    DELETE FROM karar_takip
    WHERE toplantino NOT IN (
        SELECT toplantino FROM emniyet_toplantilari
    )
    """)
    conn.commit()


import os

# Karar ekleri için tablo oluştur
cursor.execute("""
CREATE TABLE IF NOT EXISTS karar_ekler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    karar_no TEXT,
    dosya_adi TEXT,
    yol TEXT
)
""")





conn.commit()


# Karar ek klasörü (varsayılan)
os.makedirs("uploads/karar_ekleri", exist_ok=True)





for col in ["toplantino", "karar_no", "toplanti_karari", "sorumlu_makam", "termin", "uygulama_durumu", "notlar"]:
    ensure_column_exists(conn, "karar_takip", col)

def sonraki_karar_no(toplantino):
    cursor.execute("SELECT COUNT(*) FROM karar_takip WHERE toplantino = ?", (toplantino,))
    sirano = cursor.fetchone()[0] + 1
    return f"{toplantino}-{sirano:02}"

def durum_rozet(durum):
    renkler = {
        "Planlandı": "gray",
        "İşlemde": "orange",
        "Tamamlandı": "green"
    }
    return f"<span style='background-color:{renkler.get(durum, 'black')}; color:white; padding:4px 8px; border-radius:6px'>{durum}</span>"

def tutanak_formatla(toplanti):
    return f"""
    TOPLANTI TUTANAĞI

    Toplantı Tipi: {toplanti['toplanti_tipi']}
    Tarih: {toplanti['tarih'].strftime('%Y-%m-%d')}
    Konu: {toplanti['konu']}
    Katılımcılar: {toplanti['katilimcilar']}
    Alınan Kararlar:
    {toplanti['kararlar']}
    Durum: {toplanti['durum']}
    """

def karar_pdf_olustur( atanan, durum, konu):
    pdf = FPDF()
    pdf.add_page()
    font_path = os.path.join("fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)
    pdf.cell(0, 10, "Toplantı Kararı Raporu", ln=True, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, f" Atanan Kişi: {atanan}")
    pdf.multi_cell(0, 10, f" Durum: {durum}")
    pdf.multi_cell(0, 10, f" Toplantı Konusu: {konu}")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    return tmp.name

conn.commit()

st.set_page_config(page_title="🗕️ Emniyet Toplantı Takibi", layout="wide")
st.title(":calendar: Emniyet Toplantı Takip Sistemi")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Toplantı Yönetimi", "📝 Karar Ekleme","📎Karar Takibi", "📅 Takvim ve Tutanaklar", "⚙️ Ayarlar"])


# Toplantı numarası sütununu oluşturun (eğer yoksa)
ensure_column_exists(conn, "emniyet_toplantilari", "toplantino", "TEXT")

with tab1:
    st.subheader(":heavy_plus_sign: Yeni Toplantı Kaydı Ekle")
    
    # Kayıtlı katılımcıları getir
    cursor.execute("SELECT gorev, isim FROM katilimcilar")
    kayitli_katilimcilar = cursor.fetchall()
    katilimci_secenekleri = [f"{gorev} - {isim}" for gorev, isim in kayitli_katilimcilar]
    
    with st.form("toplanti_formu"):
        col1, col2 = st.columns(2)
        with col1:
            toplanti_tipi = st.selectbox("Toplantı Tipi", ["SRB - Emniyet Gözden Geçirme Toplantılası", "SAG - Emniyet Eylem Grubu Toplantısı"])
            tarih = st.date_input("Toplantı Tarihi", value=datetime.today())
        with col2:
            konu = st.text_input("Toplantı Konusu")
             # Kayıtlı katılımcılar çoklu seçim
            secilen_katilimcilar = st.multiselect("Katılımcılar (listeden seçin)",katilimci_secenekleri)
            durum = st.selectbox("Durum", ["Planlandı", "Tamamlandı", "İptal Edildi"])

        if st.form_submit_button(":floppy_disk: Kaydet"):
            # Tarih bileşenlerini al
            yil_kisa = tarih.strftime("%y")
            ay = tarih.strftime("%m")
            gun = tarih.strftime("%d")

            # Seçilen toplantı tipinin kısaltmasını al
            toplanti_kisaltma = toplanti_tipi.split(" - ")[0]

            # Aynı tarih ve tip için sonraki sıra numarasını hesapla
            cursor.execute("""
                SELECT COUNT(*) FROM emniyet_toplantilari 
                WHERE tarih = ? AND toplanti_tipi = ?
            """, (str(tarih), toplanti_tipi))
            sirano = cursor.fetchone()[0] + 1

            # Toplantı numarasını oluştur
            toplanti_no = f"{toplanti_kisaltma}-{yil_kisa}-{ay}-{gun}-{sirano:02}"

            # Katılımcıları virgül ile ayırarak kaydet
            katilimcilar_str = ", ".join(secilen_katilimcilar)

            # Toplantıyı kaydet
            cursor.execute("""
                INSERT INTO emniyet_toplantilari (toplanti_tipi, tarih, konu, katilimcilar, durum, toplantino)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (toplanti_tipi, str(tarih), konu, katilimcilar_str, durum, toplanti_no))
            conn.commit()
            st.success(f":white_check_mark: Toplantı başarıyla eklendi! Toplantı No: {toplanti_no}")

    df_toplanti = pd.read_sql_query("SELECT * FROM emniyet_toplantilari ORDER BY tarih DESC", conn)
    if not df_toplanti.empty:
        df_toplanti["tarih"] = pd.to_datetime(df_toplanti["tarih"])
        st.dataframe(df_toplanti.drop(columns=["id","kararlar","termin"], errors='ignore'))
         
            
        with st.expander("🗑️ Toplantı Sil"):
            # Toplantı numarasına göre seçim yap
            if not df_toplanti.empty:
                secilen_silinecek_no = st.selectbox(
                    "Silinecek toplantıyı seçin (Toplantı No):",
                    df_toplanti["toplantino"].dropna().tolist()
                )

                # Seçilen toplantının konusunu getir (kullanıcıya bilgi amaçlı)
                secilen_konu = df_toplanti[df_toplanti["toplantino"] == secilen_silinecek_no]["konu"].values[0]

                onay = st.radio(
                    f"'{secilen_silinecek_no}' toplantısını silmek istediğinizden emin misiniz?",
                    ["Hayır", "Evet"],
                    horizontal=True
                )

                if st.button("Toplantıyı Sil") and onay == "Evet":
                    cursor.execute("DELETE FROM emniyet_toplantilari WHERE toplantino = ?", (secilen_silinecek_no,))
                    karar_silme()
                    conn.commit()
                    st.success(f"'{secilen_silinecek_no}' numaralı toplantı başarıyla silindi!")
    else:
        st.info("📭 Henüz toplantı kaydı bulunmuyor.")

with tab2:
    st.subheader(":memo: Toplantı Kararı Ekle")

    df_toplanti = pd.read_sql_query("SELECT * FROM emniyet_toplantilari ORDER BY tarih DESC", conn)

    if not df_toplanti.empty:
        toplantino_sec = st.selectbox(
            "Karar eklemek için toplantı seçin:",
            df_toplanti["toplantino"].tolist()
        )

        with st.form("karar_ekle_formu"):
            col1, col2 = st.columns(2)
            with col1:
                toplanti_karari = st.text_area("Toplantı Kararı")
                sorumlu_makam = st.text_input("Sorumlu Makam")
            with col2:
                termin = st.date_input("Termin", datetime.today())
                uygulama_durumu = st.selectbox("Karar Uygulama Durumu", ["Planlandı", "İşlemde", "Tamamlandı"])
                notlar = st.text_area("Notlar")

            if st.form_submit_button("Kararı Kaydet"):
                karar_no = sonraki_karar_no(toplantino_sec)
                cursor.execute("""
                    INSERT INTO karar_takip (toplantino, karar_no, toplanti_karari, sorumlu_makam, termin, uygulama_durumu, notlar)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (toplantino_sec, karar_no, toplanti_karari, sorumlu_makam, str(termin), uygulama_durumu, notlar))
                conn.commit()
                st.success(f"Karar başarıyla eklendi! Karar No: {karar_no}")

    # Seçili toplantıya ait kararları görüntüleme
    st.subheader("📋 Toplantıya Ait Kararlar")

    secilen_toplantino_kararlar = st.selectbox(
        "Kararlarını görmek istediğiniz toplantıyı seçin:",
        df_toplanti["toplantino"].tolist(),
        key="karar_goster_toplantino"
    )

    df_kararlar = pd.read_sql_query("SELECT * FROM karar_takip WHERE toplantino = ?", conn, params=(secilen_toplantino_kararlar,))
    if not df_kararlar.empty:
        df_kararlar = df_kararlar[["karar_no", "toplanti_karari", "sorumlu_makam", "termin", "uygulama_durumu", "notlar"]]
        df_kararlar.columns = ["Karar No", "Toplantı Kararı", "Sorumlu Makam", "Termin", "Uygulama Durumu", "Notlar"]
        st.dataframe(df_kararlar, use_container_width=True)

        # Karar güncelleme/silme alanı
        st.markdown("### 🛠️ Karar Güncelleme ve Silme")
        karar_sec = st.selectbox("Karar seçiniz:", df_kararlar["Karar No"].tolist())

        secilen_karar = df_kararlar[df_kararlar["Karar No"] == karar_sec].iloc[0]

        yeni_durum = st.selectbox("Yeni Uygulama Durumu", ["Planlandı", "İşlemde", "Tamamlandı"], index=["Planlandı", "İşlemde", "Tamamlandı"].index(secilen_karar["Uygulama Durumu"]))
        yeni_not = st.text_area("Yeni Notlar", secilen_karar["Notlar"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Kararı Güncelle"):
                cursor.execute("""
                    UPDATE karar_takip SET uygulama_durumu = ?, notlar = ? WHERE karar_no = ?
                """, (yeni_durum, yeni_not, karar_sec))
                conn.commit()
                st.success("Karar güncellendi.")
        with col2:
            if st.button("Kararı Sil"):
                cursor.execute("DELETE FROM karar_takip WHERE karar_no = ?", (karar_sec,))
                conn.commit()
                st.warning("Karar silindi.")
    else:
        st.info("Bu toplantıya ait karar bulunmamaktadır.")


import calendar as cal
from datetime import date, timedelta
from fpdf import FPDF
import tempfile
import zipfile



with tab3:

    


    st.header("📎 Karar Takibi ve Ekler")

    df_karar = pd.read_sql_query("SELECT * FROM karar_takip", conn)
    if df_karar.empty:
        st.info("Henüz karar girilmemiş.")
    else:
        # 1. Toplantı numaralarını getir
        toplantilar = sorted(df_karar["toplantino"].dropna().unique().tolist())
        secilen_toplantino = st.selectbox("📌 Toplantı Numarası Seçin", toplantilar)

        # 2. Seçilen toplantıya ait kararları getir
        ilgili_kararlar = df_karar[df_karar["toplantino"] == secilen_toplantino]
        kararlar = ilgili_kararlar["karar_no"].tolist()

        if kararlar:
            secilen_karar_no = st.selectbox("📄 Karar Numarası Seçin", kararlar)

            secilen_karar = ilgili_kararlar[ilgili_kararlar["karar_no"] == secilen_karar_no]
            if not secilen_karar.empty:
                secilen_karar = secilen_karar.iloc[0]
                st.markdown(f"**Toplantı Kararı:** {secilen_karar['toplanti_karari']}")
                st.markdown(f"**Sorumlu Makam:** {secilen_karar['sorumlu_makam']}")
                st.markdown(f"**Termin:** {secilen_karar['termin']}")
                st.markdown(f"**Durum:** {secilen_karar['uygulama_durumu']}")
                st.markdown(f"**Notlar:** {secilen_karar['notlar']}")
            else:
                st.warning("Karar bulunamadı.")
        else:
            st.info("Bu toplantıya ait karar bulunmamaktadır.")






        st.subheader("📎 Karar Ekleri")

        if kararlar and "secilen_karar_no" in locals():
            

            with st.form("ek_yukle_formu"):
                uploaded_file = st.file_uploader("Ek Dosyayı Yükle", type=["pdf", "docx", "png", "jpg"])
                if st.form_submit_button("Yükle") and uploaded_file:
                    save_path = f"uploads/karar_ekleri/{uploaded_file.name}"
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    cursor.execute("INSERT INTO karar_ekler (karar_no, dosya_adi, yol) VALUES (?, ?, ?)",
                                (secilen_karar_no, uploaded_file.name, save_path))
                    conn.commit()
                    st.success("Dosya yüklendi.")

            # Ekleri göster
            df_ekler = pd.read_sql_query("SELECT * FROM karar_ekler WHERE karar_no = ?", conn, params=(secilen_karar_no,))
            if not df_ekler.empty:
                for _, row in df_ekler.iterrows():
                    st.markdown(f"📄 {row['dosya_adi']}")
                    with open(row["yol"], "rb") as f:
                        st.download_button(
                            label="📥 İndir",
                            data=f.read(),
                            file_name=row["dosya_adi"],
                            mime="application/octet-stream"
                        )
                    if st.button(f"❌ Sil ({row['dosya_adi']})", key=row["id"]):
                        try:
                            os.remove(row["yol"])
                        except FileNotFoundError:
                            pass
                        cursor.execute("DELETE FROM karar_ekler WHERE id = ?", (row["id"],))
                        conn.commit()
                        st.warning(f"{row['dosya_adi']} silindi.")
            else:
                st.info("Bu karara ait ek dosya yok.")

        st.subheader("📅 Karar Takvimi (Termin Tarihlerine Göre)")

        df_karar["termin"] = pd.to_datetime(df_karar["termin"])

        if not df_karar.empty:
            karar_takvim_df = df_karar.copy()
            karar_takvim_df["Etiket"] = karar_takvim_df["karar_no"] + " | " + karar_takvim_df["sorumlu_makam"]
            karar_takvim_df["termin_son"] = karar_takvim_df["termin"] + timedelta(hours=2)  # bitiş için dummy saat

            renk_harita = {
                "Planlandı": "orange",
                "İşlemde": "blue",
                "Tamamlandı": "green"
            }

            fig = px.timeline(
                karar_takvim_df,
                x_start="termin",
                x_end="termin_son",
                y="Etiket",
                color="uygulama_durumu",
                color_discrete_map=renk_harita,
                title="Karar Termin Takvimi"
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Henüz termin tarihi içeren karar girilmemiş.")

        # ---------------------------------------

        st.subheader("⏳ Yaklaşan Kararlar (7 gün içinde ve tamamlanmamış)")

        bugun = datetime.today()
        yedi_gun_sonra = bugun + timedelta(days=7)

        df_yaklasan = df_karar[
            (df_karar["uygulama_durumu"] != "Tamamlandı") &
            (df_karar["termin"] >= bugun) &
            (df_karar["termin"] <= yedi_gun_sonra)
        ]

        if not df_yaklasan.empty:
            df_yaklasan_goster = df_yaklasan[["karar_no", "sorumlu_makam", "termin", "uygulama_durumu", "notlar"]]
            df_yaklasan_goster.columns = ["Karar No", "Sorumlu Makam", "Termin", "Durum", "Notlar"]
            st.dataframe(df_yaklasan_goster, use_container_width=True)
        else:
            st.success("🎉 Önümüzdeki 7 gün içinde tamamlanmamış karar bulunmamaktadır.")

        st.subheader("📂 Tüm Kararlar ve Filtreleme")

        # Tarih filtreleme için min/max değerleri
        min_tarih = df_karar["termin"].min()
        max_tarih = df_karar["termin"].max()

        col1, col2, col3 = st.columns(3)
        with col1:
            sorumlu_filtre = st.multiselect("Sorumlu Makam", options=sorted(df_karar["sorumlu_makam"].dropna().unique().tolist()))
        with col2:
            durum_filtre = st.multiselect("Uygulama Durumu", options=["Planlandı", "İşlemde", "Tamamlandı"], default=["Planlandı", "İşlemde", "Tamamlandı"])
        with col3:
            tarih_aralik = st.date_input("Termin Tarih Aralığı", value=(min_tarih.date(), max_tarih.date()))

        # Filtreleme işlemleri
        df_filt = df_karar.copy()

        if sorumlu_filtre:
            df_filt = df_filt[df_filt["sorumlu_makam"].isin(sorumlu_filtre)]

        if durum_filtre:
            df_filt = df_filt[df_filt["uygulama_durumu"].isin(durum_filtre)]

        if tarih_aralik:
            baslangic, bitis = tarih_aralik
            df_filt = df_filt[
                (df_filt["termin"] >= pd.Timestamp(baslangic)) &
                (df_filt["termin"] <= pd.Timestamp(bitis))
            ]

        if not df_filt.empty:
            df_goster = df_filt[["karar_no", "toplanti_karari", "sorumlu_makam", "termin", "uygulama_durumu", "notlar"]]
            df_goster.columns = ["Karar No", "Toplantı Kararı", "Sorumlu Makam", "Termin", "Durum", "Notlar"]
            st.dataframe(df_goster, use_container_width=True)

            st.download_button(
                "📥 Filtrelenmiş Kararları Excel Olarak İndir",
                data=df_goster.to_csv(index=False).encode("utf-8-sig"),
                file_name="filtrelenmis_kararlar.csv",
                mime="text/csv"
            )
        else:
            st.warning("Seçilen filtrelere uyan karar bulunamadı.")


       
        


with tab4:
    st.subheader(":spiral_calendar_pad: Toplantı Detayları ve Takvim")

    df_toplanti = pd.read_sql_query("SELECT * FROM emniyet_toplantilari ORDER BY tarih DESC", conn)
    if not df_toplanti.empty:


        df_toplanti["tarih"] = pd.to_datetime(df_toplanti["tarih"])

        # Toplantı numarası ile seçim yapma
        secilen_toplanti_no = st.selectbox(
            "📌 Detaylarını görmek istediğiniz toplantıyı seçin (Toplantı No):",
            df_toplanti["toplantino"].tolist()
        )

        secilen_toplanti = df_toplanti[df_toplanti["toplantino"] == secilen_toplanti_no].iloc[0]

        st.markdown("## 📑 Seçilen Toplantı Detayları")
        st.markdown(f"**Toplantı Tipi:** {secilen_toplanti['toplanti_tipi']}")
        st.markdown(f"**Tarih:** {secilen_toplanti['tarih'].strftime('%Y-%m-%d')}")
        st.markdown(f"**Konu:** {secilen_toplanti['konu']}")
        st.markdown(f"**Katılımcılar:** {secilen_toplanti['katilimcilar']}")
        st.markdown(f"**Durum:** {durum_rozet(secilen_toplanti['durum'])}", unsafe_allow_html=True)

        st.divider()

    

        # Aylık Takvim Gösterimi
        st.subheader("📈 Toplantı İstatistikleri")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            toplam_toplanti = len(df_toplanti)
            st.metric("Toplam Toplantı", toplam_toplanti)

        with col2:
            tamamlanan_toplanti = len(df_toplanti[df_toplanti["durum"] == "Tamamlandı"])
            st.metric("✅ Tamamlanan", tamamlanan_toplanti)

        with col3:
            planlanan_toplanti = len(df_toplanti[df_toplanti["durum"] == "Planlandı"])
            st.metric("🗓️ Planlanan", planlanan_toplanti)

        with col4:
            iptal_toplanti = len(df_toplanti[df_toplanti["durum"] == "İptal Edildi"])
            st.metric("❌ İptal Edilen", iptal_toplanti)

        # Sonraki yaklaşan toplantı
        gelecek_toplantilar = df_toplanti[df_toplanti["tarih"] >= pd.Timestamp("today")].sort_values(by="tarih")
        if not gelecek_toplantilar.empty:
            sonraki_toplanti = gelecek_toplantilar.iloc[0]
            st.info(f"⏳ **Sonraki Yaklaşan Toplantı:** {sonraki_toplanti['toplantino']} - {sonraki_toplanti['konu']} ({sonraki_toplanti['tarih'].strftime('%Y-%m-%d')})")
        else:
            st.success("🎉 Yaklaşan toplantı yok!")



        from streamlit_calendar import calendar


        st.subheader("📅 Aylık Toplantı Takvimi")

        durum_renk_map = {
            "Planlandı": "#facc15",
            "Tamamlandı": "#10b981",
            "İptal Edildi": "#ef4444"
        }

        events = []

        for _, row in df_toplanti.iterrows():
            events.append({
                "title": row["toplantino"],
                "start": row["tarih"].strftime("%Y-%m-%d"),
                "end": row["tarih"].strftime("%Y-%m-%d"),
                "color": durum_renk_map.get(row["durum"], "#d1d5db"),
                "extendedProps": {
                    "tip": row["toplanti_tipi"],
                    "konu": row["konu"],
                    "katilimcilar": row["katilimcilar"],
                    "durum": row["durum"]
                }
            })

        calendar_options = {
            "initialView": "dayGridMonth",
            "locale": "tr",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": ""
            },
            "height": 600
        }

        selected_event = calendar(events=events, options=calendar_options)

        event = selected_event.get("event", {})
        props = event.get("extendedProps", {})
        toplanti_no = event.get("title", "")

        if event:
            with st.expander(f"📋 {event['title']} | {event['extendedProps']['konu']}", expanded=True):
                st.markdown(f"**📅 Tarih:** {event['start']}")
                st.markdown(f"**🏷️ Toplantı Tipi:** {event['extendedProps']['tip']}")
                st.markdown(f"**🗂️ Konu:** {event['extendedProps']['konu']}")
                st.markdown(f"**👥 Katılımcılar:** {event['extendedProps']['katilimcilar']}")
                st.markdown(f"**📊 Durum:** `{event['extendedProps']['durum']}`")

        


        # # Toplantı zip dosyasını indirme
        # st.divider()
        # st.subheader("📤 Toplantıyı Tüm Karar ve Ekleriyle ZIP Olarak İndir")

        # df_toplanti_all = pd.read_sql_query("SELECT * FROM emniyet_toplantilari", conn)
        # df_karar_all = pd.read_sql_query("SELECT * FROM karar_takip", conn)
        # df_ek_all = pd.read_sql_query("SELECT * FROM karar_ekler", conn)

        # if not df_toplanti_all.empty:
        #     secilen_toplantino_zip = st.selectbox("ZIP için toplantı numarası seçin:", df_toplanti_all["toplantino"].tolist(), key="toplanti_zip_secimi")

        #     # 1. Toplantı bilgileri PDF oluştur
        #     sec_top = df_toplanti_all[df_toplanti_all["toplantino"] == secilen_toplantino_zip].iloc[0]

        #     top_pdf = FPDF()
        #     top_pdf.add_page()
        #     font_path = os.path.join("fonts", "DejaVuSans.ttf")
        #     top_pdf.add_font("DejaVu", "", font_path, uni=True)
        #     top_pdf.set_font("DejaVu", size=12)
        #     top_pdf.cell(0, 10, "Toplantı Bilgileri", ln=True, align='C')
        #     top_pdf.ln(10)
        #     for etiket, deger in [
        #         ("Toplantı No", sec_top["toplantino"]),
        #         ("Tarih", sec_top["tarih"]),
        #         ("Tip", sec_top["toplanti_tipi"]),
        #         ("Konu", sec_top["konu"]),
        #         ("Katılımcılar", sec_top["katilimcilar"]),
        #         ("Durum", sec_top["durum"]),
        #         ("Alınan Kararlar", sec_top.get("kararlar", ""))
        #     ]:
        #         from textwrap import wrap
        #         def sanitize_text_for_pdf(text, pdf, font='Arial', size=10):
        #             pdf.set_font(font, size=size)
        #             clean_text = ''
        #             for char in text:
        #                 try:
        #                     # FPDF'nin metrik hesaplaması, render edilebilir mi test etmek için
        #                     pdf.get_string_width(char)
        #                     clean_text += char
        #                 except Exception:
        #                     clean_text += '□'  # render edilemeyen karakter yerine boş kare
        #             return clean_text

        #         top_pdf.set_font("Arial", size=10)  # Mutlaka önce font tanımla!
        #         raw_text = f"{etiket}: {deger}"
        #         safe_text = sanitize_text_for_pdf(raw_text, top_pdf)
        #         top_pdf.multi_cell(0, 10, safe_text)


             

        #     top_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        #     top_pdf.output(top_pdf_path)

        #     # 2. Karar PDF'lerini hazırla
        #     kararlar = df_karar_all[df_karar_all["toplantino"] == secilen_toplantino_zip]
        #     karar_pdf_paths = []
        #     karar_ek_dict = {}

        #     for _, karar in kararlar.iterrows():
        #         karar_pdf = FPDF()
        #         karar_pdf.add_page()
        #         font_path = os.path.join("fonts", "DejaVuSans.ttf")
        #         karar_pdf.add_font("DejaVu", "", font_path, uni=True)
        #         karar_pdf.set_font("DejaVu", size=12)
        #         karar_pdf.cell(0, 10, f"Karar: {karar['karar_no']}", ln=True, align='C')
        #         karar_pdf.ln(10)
        #         for etiket, deger in [
        #             ("Toplantı Kararı", karar["toplanti_karari"]),
        #             ("Sorumlu Makam", karar["sorumlu_makam"]),
        #             ("Termin", karar["termin"]),
        #             ("Durum", karar["uygulama_durumu"]),
        #             ("Notlar", karar["notlar"])
        #         ]:
        #             karar_pdf.multi_cell(0, 10, f"{etiket}: {deger}")
        #         karar_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        #         karar_pdf.output(karar_path)
        #         karar_pdf_paths.append((karar["karar_no"], karar_path))

        #         # Ekleri topla
        #         karar_ekleri = df_ek_all[df_ek_all["karar_no"] == karar["karar_no"]]
        #         karar_ek_dict[karar["karar_no"]] = [row["yol"] for _, row in karar_ekleri.iterrows()]

        #     # 3. ZIP oluştur
        #     zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name

        #     with zipfile.ZipFile(zip_path, 'w') as zipf:
        #         zipf.write(top_pdf_path, arcname="Toplanti_Bilgisi.pdf")
        #         for karar_no, pdf_path in karar_pdf_paths:
        #             zipf.write(pdf_path, arcname=f"Kararlar/{karar_no}.pdf")
        #             for idx, ek_yol in enumerate(karar_ek_dict.get(karar_no, [])):
        #                 if os.path.exists(ek_yol):
        #                     dosya_adi = os.path.basename(ek_yol)
        #                     zipf.write(ek_yol, arcname=f"Ekler/{karar_no}/{dosya_adi}")

        #     with open(zip_path, "rb") as f:
        #         st.download_button("Toplantıyı ZIP Olarak İndir", f.read(), file_name=f"{secilen_toplantino_zip}_toplanti_raporu.zip", mime="application/zip")
        # else:
        #     st.info("Toplantı verisi bulunamadı.")




    else:
        st.info(":mailbox_closed: Henüz toplantı kaydı bulunmamaktadır.")


with tab5:
    st.header("⚙️ Ayarlar")

    st.subheader("👥 Katılımcı Yönetimi")

    # Yeni katılımcı ekleme formu
    with st.form("katilimci_ekle_formu"):
        yeni_gorev = st.text_input("Görev / Title")
        yeni_isim = st.text_input("Katılımcı Adı ve Soyadı")
        if st.form_submit_button("➕ Katılımcı Ekle"):
            cursor.execute("INSERT INTO katilimcilar (gorev, isim) VALUES (?, ?)", (yeni_gorev, yeni_isim))
            conn.commit()
            st.success(f"✅ {yeni_gorev} - {yeni_isim} eklendi.")

    # Mevcut katılımcıları gösterme ve silme
    st.subheader("🗂️ Kayıtlı Katılımcılar")
    df_katilimcilar = pd.read_sql_query("SELECT * FROM katilimcilar", conn)

    if not df_katilimcilar.empty:
        df_katilimcilar_display = df_katilimcilar[["gorev", "isim"]]
        st.dataframe(df_katilimcilar_display, use_container_width=True)

        silinecek_katilimci = st.selectbox(
            "Silinecek katılımcıyı seçin:",
            df_katilimcilar.apply(lambda row: f"{row['gorev']} - {row['isim']}", axis=1).tolist()
        )

        if st.button("🗑️ Katılımcıyı Sil"):
            gorev, isim = silinecek_katilimci.split(" - ", 1)
            cursor.execute("DELETE FROM katilimcilar WHERE gorev=? AND isim=?", (gorev, isim))
            conn.commit()
            st.warning(f"🗑️ {silinecek_katilimci} silindi.")
    else:
        st.info("📭 Henüz katılımcı eklenmemiş.")






conn.close()
