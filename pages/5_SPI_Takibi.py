import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from utils.auth import goster_oturum_paneli
from utils.firebase_db import db
from io import BytesIO
import numpy as np

# Kimlik doğrulama

goster_oturum_paneli()

st.title("📊 Çeyrek Bazlı Olay Dağılımı (Firebase)")

# --- Firestore CRUD Helper Functions ---
@st.cache_data(ttl=300)
def get_stats_df():
    records = []
    for snap in db.collection("occurrence_stats").stream():
        data = snap.to_dict()
        term = data.get("term")
        ind = data.get("indicator")
        if term is None or ind is None:
            try:
                term, ind = snap.id.split("__", 1)
            except ValueError:
                term, ind = None, None
        count = data.get("count", 0)
        records.append({"term": term, "indicator": ind, "count": count})
    df = pd.DataFrame(records)
    if not df.empty:
        df["count"] = df["count"].fillna(0).astype(int)
    return df

@st.cache_data(ttl=0)
def get_details_df():
    docs = db.collection("occurrence_details").stream()
    return pd.DataFrame([doc.to_dict() for doc in docs])

@st.cache_data(ttl=300)
def get_settings_df():
    docs = db.collection("ayarlar").stream()
    return pd.DataFrame([doc.to_dict() for doc in docs])


def update_or_insert_stat(term, indicator, count):
    doc_id = f"{term}__{indicator}"
    db.collection("occurrence_stats").document(doc_id).set({
        "term": term,
        "indicator": indicator,
        "count": count
    }, merge=True)


def add_detail_record(rec):
    try:
        db.collection("occurrence_details").add(rec)
        snaps = list(db.collection("occurrence_details")
                    .where("term", "==", rec["term"])
                    .where("indicator", "==", rec["indicator"]) 
                    .stream())
        update_or_insert_stat(rec["term"], rec["indicator"], len(snaps))
        st.success("✅ Detay kaydı eklendi.")
    except Exception as e:
        st.error(f"❌ Kayıt eklenirken hata: {e}")


def delete_detail(term, indicator, olay_no):
    try:
        snaps = db.collection("occurrence_details") \
                  .where("term", "==", term) \
                  .where("indicator", "==", indicator) \
                  .where("olay_numarasi", "==", olay_no) \
                  .stream()
        for snap in snaps:
            db.collection("occurrence_details").document(snap.id).delete()
        rem = len(list(db.collection("occurrence_details")
                      .where("term", "==", term)
                      .where("indicator", "==", indicator)
                      .stream()))
        update_or_insert_stat(term, indicator, rem)
        st.success(f"✅ {olay_no} numaralı kayıt silindi.")
    except Exception as e:
        st.error(f"❌ Silme sırasında hata: {e}")

# --- Grafik Fonksiyonu ---def plot_indicator_trend(df, indicator):
def plot_indicator_trend(df, indicator):
    fig, ax = plt.subplots(figsize=(6, 3))
    main_color = plt.cm.tab10(hash(indicator) % 10)
    ax.plot(df["term"], df["1000_saat_oran"], marker='o', label=f"{indicator} Değerleri", color=main_color)
    ort = df["1000_saat_oran"].mean()
    sd = df["1000_saat_oran"].std()
    levels = [ort, ort+sd, ort+2*sd, ort+3*sd]
    colors = {'ortalama':'gray','1. seviye':'green','2. seviye':'orange','3. seviye':'red'}
    ax.axhline(levels[0], linestyle='--', color=colors['ortalama'], label=f"Ortalama: {levels[0]:.2f}")
    ax.axhline(levels[1], linestyle='--', color=colors['1. seviye'], label=f"1. Seviye: {levels[1]:.2f}")
    ax.axhline(levels[2], linestyle='--', color=colors['2. seviye'], label=f"2. Seviye: {levels[2]:.2f}")
    ax.axhline(levels[3], linestyle='--', color=colors['3. seviye'], label=f"3. Seviye: {levels[3]:.2f}")
    ax.set_xlabel("Term")
    ax.set_ylabel("1000 Saat Oran")
    ax.set_title(f"{indicator} - Ortalama ve Seviye Grafiği")
    fig.autofmt_xdate(rotation=45)
    ax.legend(fontsize=6)
    ax.grid(True)
    return fig

def load_settings():
    """
    Firestore’dan ‘ayarlar’ koleksiyonundaki kayıtları çekip,
    kategori bazında listelere ayırır ve hem DataFrame hem de
    dört ayrı liste olarak döner.
    """
    # Tüm ayarları çek
    df = get_settings_df()
    # Her kategori için değerleri listele
    terms = df[df['kategori'] == 'term']['deger'].tolist()
    indicators = df[df['kategori'] == 'indicator']['deger'].tolist()
    types = df[df['kategori'] == 'tip']['deger'].tolist()
    regs = df[df['kategori'] == 'tescil']['deger'].tolist()
    # DataFrame ve listeleri geri döndür
    return df, terms, indicators, types, regs

# --- Data Load ---
stats_df = get_stats_df()
if stats_df.empty:
    stats_df = pd.DataFrame(columns=["term","indicator","count"] )

settings_df = get_settings_df()
details_df = get_details_df()

# Ayarlar listeleri
terms_list = settings_df[settings_df['kategori']=='term']['deger'].tolist()
indicator_list = settings_df[settings_df['kategori']=='indicator']['deger'].tolist()
types_list = settings_df[settings_df['kategori']=='tip']['deger'].tolist()
regs_list = settings_df[settings_df['kategori']=='tescil']['deger'].tolist()

# Pivot göstergeleri
pivot_indicators = sorted(stats_df['indicator'].dropna().unique())

# Sayfa sekmeleri
tabs = st.tabs([
    "📝 Veri Girişi",
    "📄 Detaylar",
    "⚙️ Ayarlar",
    "📊 Uçuş Saati Oranı",
    "📈 Grafiksel Analiz",
])

with tabs[0]:
    st.subheader("📝 Yeni Detay Kayıt Gir")
    if not terms_list or not indicator_list:
        st.info("📭 Ayarlar sekmesinden önce Term ve İndikatör ekleyin.")
    else:
        # Template hazırlama (Excel) - opsiyonel
        template_cols = ["term","indicator","olay_numarasi","olay_tarihi","raporlayan","geri_besleme","olay_grubu","olay_yeri","ucak_tipi","ucak_tescili","olay_ozeti","bagli_rapor_no","rapor_tipi"]
        template_df = pd.DataFrame(columns=template_cols)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            template_df.to_excel(writer, index=False, sheet_name='Template')
        data = output.getvalue()

        # Manuel giriş
        term_sel = st.selectbox("Term", terms_list, key="term_entry")
        ind_sel = st.selectbox("İndikatör Seç", indicator_list, key="ind_entry")
        existing = details_df[details_df['term']==term_sel]
        seq = len(existing) + 1
        olay_no_default = f"{term_sel}-{seq:02d}"
        with st.form("detail_form"):
            st.markdown(f"**Olay Numarası:** {olay_no_default}")
            olay_trh = st.date_input("📆 Olay Tarihi")
            raporlayan = st.text_input("👤 Raporlayan")
            geri_besle = st.text_area("💬 Geri Besleme")
            olay_grp = st.text_input("🧩 Olay Grubu")
            olay_yer = st.text_input("📍 Olay Yeri")
            ucak_tip = st.selectbox("✈️ Uçak Tipi", types_list)
            ucak_tesc = st.selectbox("🔢 Uçak Tescili", regs_list)
            olay_ozet = st.text_area("📝 Olay Özeti")
            bagli_no = st.text_input("🔗 Bağlı Rapor No")
            rapor_tip = st.selectbox("📂 Rapor Tipi", ["voluntary","hazard","N/A"])
            if st.form_submit_button("💾 Kaydet"):
                rec = {
                    "term": term_sel,
                    "indicator": ind_sel,
                    "olay_numarasi": olay_no_default,
                    "olay_tarihi": olay_trh.strftime("%Y-%m-%d"),
                    "raporlayan": raporlayan,
                    "geri_besleme": geri_besle,
                    "olay_grubu": olay_grp,
                    "olay_yeri": olay_yer,
                    "ucak_tipi": ucak_tip,
                    "ucak_tescili": ucak_tesc,
                    "olay_ozeti": olay_ozet,
                    "bagli_rapor_no": bagli_no,
                    "rapor_tipi": rapor_tip
                }
                add_detail_record(rec)
                # Cache temizle ve tüm verileri yeniden yükle
                get_stats_df.clear(); get_details_df.clear(); get_settings_df.clear()
                st.rerun()

with tabs[1]:
    st.subheader("📄 Detaylı Kayıtlar")
    # Ayarlar sekmesinden çekilen terim ve indikatör listelerini al
    settings_df, terms_list, indicator_list, types_list, regs_list = load_settings()
    # Güncel detay verilerini al
    details_df = get_details_df()
    if details_df.empty:
        st.info("📭 Detay kaydı yok.")
    else:
        # Filtre seçeneklerini hem detaylardan hem ayarlardan oluştur
        term_opts = sorted(
            set(details_df['term'].dropna().unique())
            | set(terms_list)
        )
        ind_opts = sorted(
            set(details_df['indicator'].dropna().unique())
            | set(indicator_list)
        )
        sel_terms = st.multiselect("🔍 Term Filtrele", term_opts, default=[])
        sel_inds  = st.multiselect("🔍 İndikatör Filtrele", ind_opts, default=[])
        df_filt = details_df[details_df['term'].isin(sel_terms) & details_df['indicator'].isin(sel_inds)].copy()
        # 2025 ile başlayanları üste al ve olay_numarasi ilk kolon olsun
        df_filt['priority'] = df_filt['olay_numarasi'].str.startswith('2025')
        df_sorted = df_filt.sort_values(by=['priority','olay_numarasi'], ascending=[False,True]).drop(columns='priority')
        cols = ['olay_numarasi'] + [c for c in df_sorted.columns if c!='olay_numarasi']
        df_sorted = df_sorted[cols]
        edited = st.data_editor(
            df_sorted,
            column_config={col: st.column_config.TextColumn(col) for col in df_sorted.columns},
            use_container_width=True,
            height=300
        )
        csv = df_sorted.to_csv(index=False)
        st.download_button("📥 CSV İndir", data=csv, file_name="detaylar.csv")
        st.markdown("---")
        st.subheader("🗑️ Kayıt Sil")
        to_delete = st.selectbox("Silinecek Olay Numarası", df_sorted['olay_numarasi'], key="delete_select")
        if st.button("❌ Sil", key="delete_button"):
            row = df_sorted[df_sorted['olay_numarasi']==to_delete].iloc[0]
            delete_detail(row['term'], row['indicator'], to_delete)
            get_details_df.clear()
            st.rerun()


with tabs[2]:
    st.subheader("⚙️ Ayarlar")
    settings_df = get_settings_df()
    kategori = st.selectbox("Kategori", ["term","indicator","tip","tescil"])
    yeni = st.text_input("Yeni Değer")
    if st.button("➕ Ekle") and yeni:
        try:
            db.collection("ayarlar").add({"kategori":kategori,"deger":yeni})
            st.success("✅ Eklendi.")
            get_settings_df.clear()
            settings_df, terms_list, indicator_list, types_list, regs_list = load_settings()
        except Exception as e:
            st.error(f"❌ Ekleme hatası: {e}")
        st.rerun()
    settings_df = get_settings_df()
    if not settings_df.empty:
        for cat, title in [("term","📅 Termler"),("indicator","📊 İndikatörler"),("tip","✈️ Uçak Tipleri"),("tescil","🔢 Uçak Tescilleri")]:
            subset = settings_df[settings_df['kategori']==cat]
            st.markdown(f"### {title}")
            if not subset.empty:
                st.dataframe(subset[['deger']], use_container_width=True)
            else:
                st.info(f"Henüz {title.lower()} eklenmedi.")
    else:
        st.info("Henüz ayar kaydı yok.")

with tabs[3]:
    st.subheader("📊 1000 Saat Başına Olay Oranları")
    if stats_df.empty:
        st.info("📭 Stats yok.")
    else:
        unique_terms = sorted(stats_df['term'].dropna().unique())
        init = []
        for term in unique_terms:
            doc = db.collection('ucus_saatleri').document(term).get()
            sa = doc.to_dict().get('ucus_saati', 0) if doc.exists else 0
            init.append({'term': term, 'ucus_saati': sa})
        df_ucus = pd.DataFrame(init)
        df_edit = st.data_editor(
            df_ucus,
            column_config={
                'term': st.column_config.TextColumn('Term', disabled=True),
                'ucus_saati': st.column_config.NumberColumn('Uçuş Saati', min_value=0)
            },
            num_rows='fixed',
            use_container_width=True
        )
        if st.button("💾 Uçuş Saatlerini Kaydet", key="save_ucus"):
            for _, row in df_edit.iterrows():
                db.collection('ucus_saatleri').document(row['term']).set(
                    {'ucus_saati': row['ucus_saati']}, merge=True
                )
            st.success("✅ Uçuş saatleri Firebase’e kaydedildi.")
            st.rerun()
        merged = stats_df.merge(df_edit, on='term', how='left')
        merged['ucus_saati'] = merged['ucus_saati'].fillna(0).astype(float)
        merged['1000_saat_oran'] = np.where(
            merged['ucus_saati'] == 0,
            0,
            merged['count'] / merged['ucus_saati'] * 1000
        ).round(3)
        st.markdown("### 📊 Oranlı Tablo")
        st.dataframe(
            merged[['term', 'indicator', 'count', 'ucus_saati', '1000_saat_oran']],
            use_container_width=True
        )
        st.markdown("### 📉 İndikatör Bazında Ortalama (1000 Saat Başına)")
        avg_df = merged.groupby('indicator', as_index=False)['1000_saat_oran'].mean().rename(columns={'1000_saat_oran':'ortalama'})
        st.dataframe(avg_df.round(3), use_container_width=True)
        st.markdown("### 📊 Seviye Tabanlı Eşik Değerler (1000 Saat Başına)")
        lvl_df = merged.groupby('indicator', as_index=False)['1000_saat_oran'].agg(ortalama='mean', std='std')
        lvl_df['std'] = lvl_df['std'].fillna(0)
        lvl_df['1. Seviye'] = (lvl_df['ortalama'] + lvl_df['std']).round(3)
        lvl_df['2. Seviye'] = (lvl_df['ortalama'] + 2 * lvl_df['std']).round(3)
        lvl_df['3. Seviye'] = (lvl_df['ortalama'] + 3 * lvl_df['std']).round(3)
        st.dataframe(lvl_df[['indicator','ortalama','std','1. Seviye','2. Seviye','3. Seviye']], use_container_width=True)

with tabs[4]:
    st.subheader("📈 Grafiksel Analiz")
    lvl_df = merged.groupby('indicator', as_index=False)['1000_saat_oran'].agg(ortalama='mean', std='std')
    lvl_df['std'] = lvl_df['std'].fillna(0)
    for i in range(1,4): lvl_df[f'{i}. Seviye'] = (lvl_df['ortalama'] + i*lvl_df['std']).round(3)
    st.dataframe(lvl_df[['indicator','ortalama','std','1. Seviye','2. Seviye','3. Seviye']], use_container_width=True)

    selected_indicator = st.selectbox("İndikatör Seç", sorted(lvl_df['indicator'].unique()))
    sub_df = merged[merged['indicator']==selected_indicator].sort_values('term')
    st.dataframe(sub_df, use_container_width=True)

    # Grafik çizimi ve renklendirme
    fig = plot_indicator_trend(sub_df, selected_indicator)
    st.pyplot(fig)

    # Grafik indirme
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    st.download_button("📥 Grafiği İndir", data=buf, file_name=f"{selected_indicator}_trend.png", mime="image/png")

    # Alarm: seviye aşımları
    ort = sub_df['1000_saat_oran'].mean()
    sd = sub_df['1000_saat_oran'].std()
    thresholds = {'1. Seviye': ort+sd, '2. Seviye': ort+2*sd, '3. Seviye': ort+3*sd}
    max_val = sub_df['1000_saat_oran'].max()
    exceeded = [name for name, th in thresholds.items() if max_val > th]
    if exceeded:
        st.warning(f"⚠️ {selected_indicator} için aşım tespit edildi: {', '.join(exceeded)}")

# import streamlit as st
# import pandas as pd
# import sqlite3

# from utils.auth import goster_oturum_paneli
# goster_oturum_paneli()



# st.title("📊 Çeyrek Bazlı Olay Dağılımı")

# DB_PATH = "sms_occurrence.db"

# def get_data():
#     conn = sqlite3.connect(DB_PATH)
#     df = pd.read_sql_query("SELECT term, indicator, count FROM occurrence_stats", conn)
#     conn.close()
#     return df

# def update_or_insert(term, indicator, count):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("SELECT count FROM occurrence_stats WHERE term = ? AND indicator = ?", (term, indicator))
#     row = cursor.fetchone()
#     if row:
#         cursor.execute("UPDATE occurrence_stats SET count = ? WHERE term = ? AND indicator = ?", (count, term, indicator))
#     else:
#         cursor.execute("INSERT INTO occurrence_stats (term, indicator, count) VALUES (?, ?, ?)", (term, indicator, count))
#     conn.commit()
#     conn.close()

# def insert_empty_term(term, indicators):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     for ind in indicators:
#         cursor.execute("SELECT COUNT(*) FROM occurrence_stats WHERE term = ? AND indicator = ?", (term, ind))
#         if cursor.fetchone()[0] == 0:
#             cursor.execute("INSERT INTO occurrence_stats (term, indicator, count) VALUES (?, ?, 0)", (term, ind))
#     conn.commit()
#     conn.close()

# def delete_entry(term, indicator):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("UPDATE occurrence_stats SET count = 0 WHERE term = ? AND indicator = ?", (term, indicator))
#     cursor.execute("DELETE FROM occurrence_details WHERE term = ? AND indicator = ?", (term, indicator))
#     conn.commit()
#     conn.close()

# def init_aircraft_tables():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     # Uçak tipleri tablosu
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS aircraft_types (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT UNIQUE
#         )
#     """)

#     # Uçaklar (tescil + tipi) tablosu
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS aircrafts (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             reg TEXT UNIQUE,
#             type_id INTEGER,
#             FOREIGN KEY (type_id) REFERENCES aircraft_types(id)
#         )
#     """)

#     conn.commit()
#     conn.close()
# # Uygulama başlarken tabloyu oluştur
# init_aircraft_tables()




# # Veriyi al
# df = get_data()
# df["count"] = df["count"].fillna(0).astype(int)
# all_indicators = sorted(df["indicator"].unique())

# # TAB SİSTEMİ BAŞLANGICI
# sekme1, sekme2, sekme3, sekme4, sekme5, sekme6 = st.tabs(["📋 Sayısal Özet", "📝 Veri Girişi", "📄 Detaylı Kayıtlar", "⚙️ Ayarlar","📈 Grafiksel Analiz", "📊 Uçuş Saati Oranı"])


# with sekme1:
#     st.subheader("📊 Term ve İndikatörlere Göre Olay Sayısı")
#     pivot_df = df.pivot(index="term", columns="indicator", values="count").fillna(0).astype(int)
#     st.dataframe(pivot_df, use_container_width=True)

#     st.subheader("🗂️ Term Seç veya Yeni Term Ekle")
#     terms = sorted(df["term"].unique(), reverse=True)
#     term_choice = st.selectbox("📅 Var olan bir Term seçin veya yeni bir Term yazın:", terms + ["Yeni Term Ekle..."])

#     if term_choice == "Yeni Term Ekle...":
#         new_term = st.text_input("🆕 Yeni Term Girin (örn: 2025-2)")
#         if new_term and new_term not in terms:
#             insert_empty_term(new_term, all_indicators)
#             st.success(f"✅ Yeni term '{new_term}' oluşturuldu ve tüm indikatörler 0 olarak eklendi.")
#             selected_term = new_term
#         else:
#             selected_term = new_term
#     else:
#         selected_term = term_choice

#     if selected_term:
#         st.subheader(f"📄 {selected_term} dönemine ait olay verileri")
#         filtered_df = df[df["term"] == selected_term]
#         st.dataframe(filtered_df.pivot(index="term", columns="indicator", values="count").fillna(0).astype(int), use_container_width=True)

# with sekme2:
#     st.subheader("📝 Yeni Değer Gir veya Güncelle")
#     selected_term = st.selectbox("📅 Term Seç", sorted(df["term"].unique(), reverse=True), key="giris_term")
#     with st.form("entry_form"):
#         indicator = st.selectbox("🛠️ İndikatör Seç", all_indicators)

#         # Ayarlardan uçak tipi ve tescil listelerini al
#         conn = sqlite3.connect(DB_PATH)
#         types_df = pd.read_sql_query("SELECT deger FROM ayarlar WHERE kategori = 'tip'", conn)
#         regs_df = pd.read_sql_query("SELECT deger FROM ayarlar WHERE kategori = 'tescil'", conn)
#         conn.close()
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             olay_numarasi = st.text_input("📄 Olay Numarası")
#             olay_tarihi = st.date_input("📆 Olay Tarihi")
#             raporlayan = st.text_input("👤 Olayı Raporlayan")
#             geri_besleme = st.text_area("💬 Geri Besleme")
#         with col2:
#             olay_grubu = st.text_input("🧩 Olay Grubu")
#             olay_yeri = st.text_input("📍 Olay Yeri")
#             ucak_tipi = st.selectbox("✈️ Uçak Tipi", types_df["deger"].tolist())
#             ucak_tescili = st.selectbox("🔢 Uçak Tescili", regs_df["deger"].tolist())
#         with col3:
#             olay_ozeti = st.text_area("📝 Olay Özeti")
#             bagli_rapor_no = st.text_input("🔗 Bağlantılı Rapor No")
#             rapor_tipi = st.selectbox("📂 Rapor Tipi", ["", "hazard", "voluntary"])

#         submitted = st.form_submit_button("💾 Kaydet / Güncelle")
#         if submitted:
#             # count hesaplama yapılacak
#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             cursor.execute("SELECT COUNT(*) FROM occurrence_details WHERE term = ? AND indicator = ?", (selected_term, indicator))
#             yeni_count = cursor.fetchone()[0] + 1
#             update_or_insert(selected_term, indicator, yeni_count)
#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             cursor.execute("""
#                 INSERT INTO occurrence_details (
#                     term, indicator, count, olay_numarasi, olay_tarihi, raporlayan, geri_besleme,
#                     olay_grubu, olay_yeri, ucak_tipi, ucak_tescili, olay_ozeti,
#                     bagli_rapor_no, rapor_tipi
#                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 selected_term, indicator, yeni_count,
#                 olay_numarasi, olay_tarihi.strftime("%Y-%m-%d"), raporlayan, geri_besleme,
#                 olay_grubu, olay_yeri, ucak_tipi, ucak_tescili, olay_ozeti,
#                 bagli_rapor_no, rapor_tipi
#             ))
#             conn.commit()
#             conn.close()
#             st.success("✅ Kayıt başarıyla eklendi!")
#             st.rerun()

#     st.subheader("🗑️ Kayıt Sil")
#     with st.form("silme_form"):
#         sil_term = st.selectbox("📅 Term", sorted(df["term"].unique(), reverse=True), key="sil_term")
#         sil_indicator = st.selectbox("🛠️ İndikatör", all_indicators, key="sil_indikator")

#         # Olay numaraları alalım
#         with sqlite3.connect(DB_PATH) as conn:
#             query = "SELECT DISTINCT olay_numarasi FROM occurrence_details WHERE term = ? AND indicator = ? AND olay_numarasi IS NOT NULL ORDER BY olay_numarasi"
#             olay_numaralari = pd.read_sql_query(query, conn, params=(sil_term, sil_indicator))["olay_numarasi"].dropna().tolist()

#             query_count = "SELECT DISTINCT count FROM occurrence_details WHERE term = ? AND indicator = ? AND (olay_numarasi IS NULL OR olay_numarasi = '') ORDER BY count DESC"
#             sil_count_list = pd.read_sql_query(query_count, conn, params=(sil_term, sil_indicator))["count"].tolist()

#         sil_olay_no = st.selectbox("📄 Olay Numarası", olay_numaralari)

#         confirm = st.checkbox("⚠️ Bu kaydı silmek istediğinizden emin misiniz?")
#         sil = st.form_submit_button("❌ Sil")

#         if sil and confirm:
#             with sqlite3.connect(DB_PATH) as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("DELETE FROM occurrence_details WHERE term = ? AND indicator = ? AND olay_numarasi = ?", (sil_term, sil_indicator, sil_olay_no))
#                 cursor.execute("SELECT COUNT(*) FROM occurrence_details WHERE term = ? AND indicator = ?", (sil_term, sil_indicator))
#                 guncel_count = cursor.fetchone()[0]
#                 cursor.execute("UPDATE occurrence_stats SET count = ? WHERE term = ? AND indicator = ?", (guncel_count, sil_term, sil_indicator))
#                 conn.commit()
#             st.success("🗑️ Kayıt başarıyla silindi.")
#             st.rerun()



# with sekme3:
#     st.subheader("📄 Girilen Detaylı Olay Kayıtları")
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         details_df = pd.read_sql_query("SELECT * FROM occurrence_details", conn)
#         conn.close()
#         if not details_df.empty:
#             st.dataframe(details_df, use_container_width=True)
#         else:
#             st.info("📭 Henüz detaylı kayıt girilmemiş.")
#     except Exception as e:
#         st.error(f"Veri okunurken bir hata oluştu: {e}")



# with sekme4:
#     st.subheader("⚙️ Uçak Ayarları")
#     kategori = st.selectbox("Kategori Seç", ["tip", "tescil"])
#     yeni_deger = st.text_input("Yeni Değer Girin")

#     if st.button("➕ Ekle"):
#         if yeni_deger:
#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             try:
#                 cursor.execute("INSERT INTO ayarlar (kategori, deger) VALUES (?, ?)", (kategori, yeni_deger))
#                 conn.commit()
#                 st.success("✅ Değer eklendi.")
#             except sqlite3.IntegrityError:
#                 st.warning("⚠️ Bu değer zaten mevcut.")
#             conn.close()
#         else:
#             st.warning("Lütfen bir değer girin.")

#     conn = sqlite3.connect(DB_PATH)
#     ayar_df = pd.read_sql_query("SELECT * FROM ayarlar", conn)
#     conn.close()

#     st.markdown("### ✈️ Uçak Tipleri")
#     st.dataframe(ayar_df[ayar_df["kategori"] == "tip"].reset_index(drop=True), use_container_width=True)

#     st.markdown("### 🔢 Uçak Tescilleri")
#     st.dataframe(ayar_df[ayar_df["kategori"] == "tescil"].reset_index(drop=True), use_container_width=True)

# import numpy as np
# import matplotlib.pyplot as plt
# from io import BytesIO
# from fpdf import FPDF
# import tempfile
# import os



# with sekme5:
#     st.header("📊 İndikatör Bazlı Ortalama ve Seviye Grafikleri")

#     try:
#         df_oran = pd.read_sql_query("SELECT * FROM occurrence_stats", sqlite3.connect(DB_PATH))
#         df_oran["count"] = df_oran["count"].fillna(0).astype(float)
#         df_oran["count"] = df_oran["count"].fillna(0).astype(float)

#         selected_indicator = st.selectbox("İndikatör Seç", sorted(df_oran["indicator"].unique()))
#         sub_df = df_oran[df_oran["indicator"] == selected_indicator].copy()
#         sub_df = sub_df.sort_values(by="term")

#         ortalama = sub_df["count"].mean()
#         std = sub_df["count"].std()
#         first = ortalama + std
#         second = ortalama + 2 * std
#         third = ortalama + 3 * std

#         fig, ax = plt.subplots(figsize=(6, 3))
#         ax.plot(sub_df["term"], sub_df["count"], marker='o', label=f"{selected_indicator} Değerleri", color='royalblue')
#         ax.axhline(ortalama, color='gray', linestyle='--', label=f"Ortalama: {ortalama:.2f}")
#         ax.axhline(first, color='green', linestyle='--', label=f"1. Seviye: {first:.2f}")
#         ax.axhline(second, color='orange', linestyle='--', label=f"2. Seviye: {second:.2f}")
#         ax.axhline(third, color='red', linestyle='--', label=f"3. Seviye: {third:.2f}")

#         ax.set_title(f"{selected_indicator} - Ortalama ve Seviye Grafiği")
#         ax.set_xlabel("Term")
#         ax.set_xticklabels(sub_df["term"], rotation=90, fontsize=6)
#         ax.set_ylabel("Olay Sayısı")
#         ax.legend(fontsize=5, loc='upper right')
#         ax.grid(True)

#         # 📊 1., 2. ve 3. Seviye Eşik Aşımı Tabloları
#         def build_threshold_table(df, lower, upper, label):
#             temp = df[(df["count"] > lower) & (df["count"] <= upper)].copy()
#             temp["Seviye"] = label
#             return temp

#         t1 = build_threshold_table(sub_df, first, second, "1. Seviye Aşımı")
#         t2 = build_threshold_table(sub_df, second, third, "2. Seviye Aşımı")
#         t3 = build_threshold_table(sub_df, third, float('inf'), "3. Seviye Aşımı")
#         threshold_df = pd.concat([t1, t2, t3])[['term', 'count', 'Seviye']].reset_index(drop=True)

#         if not threshold_df.empty:
#             st.subheader("🚨 Eşik Aşımı Olayları")
#             st.dataframe(threshold_df, use_container_width=True)
#         else:
#             st.success("Hiçbir term eşikleri aşmamış.")
#         threshold_df = sub_df[sub_df["count"] > third].copy()
#         threshold_df = threshold_df[["term", "count"]]
#         threshold_df["Seviye"] = "3. Seviye Üzeri"

#         if not threshold_df.empty:
#             st.subheader("🚨 Eşik Aşımı Olayları")
#             st.dataframe(threshold_df.reset_index(drop=True), use_container_width=True)
#         else:
#             st.success("Hiçbir term 3. seviyeyi aşmamış.")

#         # Grafik indirme
#         st.subheader("📥 Grafiği İndir")
#         img_buffer = BytesIO()
#         fig.savefig(img_buffer, format="png", dpi=300)
#         st.download_button(
#             label="📷 PNG olarak indir",
#             data=img_buffer.getvalue(),
#             file_name=f"{selected_indicator}_grafik.png",
#             mime="image/png"
#         )

#         st.pyplot(fig)
#         df_oran = pd.read_sql_query("SELECT * FROM occurrence_stats", sqlite3.connect(DB_PATH))
#         df_oran["count"] = df_oran["count"].fillna(0).astype(float)

#         # Eşik aşımı noktalarını işaretle
#         for i, row in sub_df.iterrows():
#             if row["count"] > third:
#                 ax.annotate(f"{row['count']:.1f}", (i, row["count"]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=6, color='red')

#     except Exception as e:
#         st.error(f"Grafik çizilirken hata oluştu: {e}")


# with sekme6:
#     st.subheader("📊 1000 Uçuş Saatine Göre Olay Oranları")

#     # Tüm Term ve Indicator sayıları
#     olay_df = df.copy()

#     # Uçuş saatlerini kullanıcıdan al
#     st.markdown("### 🛫 Her Term için Uçuş Saatini Girin")
#     unique_terms = sorted(olay_df["term"].unique())

#     ucus_saatleri = {}
#     for term in unique_terms:
#         ucus_saatleri[term] = st.number_input(f"{term} için uçuş saati", min_value=1.0, step=1.0, key=f"ucus_{term}")

#     # Uçuş saatlerini df'e ekle
#     olay_df["ucus_saati"] = olay_df["term"].map(ucus_saatleri)

#     # Oran hesapla
#     olay_df["1000_saatte_oran"] = (olay_df["count"] / olay_df["ucus_saati"]) * 1000
#     olay_df["1000_saatte_oran"] = olay_df["1000_saatte_oran"].round(3)

#     st.markdown("### 📊 Oranlı Tablo")
#     st.dataframe(
#         olay_df[["term", "indicator", "count", "ucus_saati", "1000_saatte_oran"]],
#         use_container_width=True
#     )

#     st.markdown("### 📉 İndikatör Bazında Ortalama (1000 Saat Başına)")

#     ortalama_oran_df = (
#         olay_df.groupby("indicator")["1000_saatte_oran"]
#         .mean()
#         .reset_index()
#         .rename(columns={"1000_saatte_oran": "ortalama_oran"})
#     )

#     ortalama_oran_df["ortalama_oran"] = ortalama_oran_df["ortalama_oran"].round(3)

#     st.dataframe(ortalama_oran_df, use_container_width=True)

#     st.markdown("### 📉 İndikatör Bazında Ortalama ve Standart Sapma (1000 Saat Başına)")

#     istatistik_df = (
#         olay_df.groupby("indicator")["1000_saatte_oran"]
#         .agg(ortalama_oran="mean", standart_sapma="std")
#         .reset_index()
#     )

#     istatistik_df["ortalama_oran"] = istatistik_df["ortalama_oran"].round(3)
#     istatistik_df["standart_sapma"] = istatistik_df["standart_sapma"].round(3)

#     st.dataframe(istatistik_df, use_container_width=True)


#     st.markdown("### 📊 Seviye Tabanlı Eşik Değerler (1000 Saat Başına)")

#     istatistik_df = (
#         olay_df.groupby("indicator")["1000_saatte_oran"]
#         .agg(ortalama_oran="mean", standart_sapma="std")
#         .reset_index()
#     )

#     istatistik_df["first_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 1
#     istatistik_df["second_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 2
#     istatistik_df["third_level"] = istatistik_df["ortalama_oran"] + istatistik_df["standart_sapma"] * 3

#     istatistik_df = istatistik_df.round(3)

#     st.dataframe(
#         istatistik_df[[
#             "indicator", "ortalama_oran", "standart_sapma",
#             "first_level", "second_level", "third_level"
#         ]],
#         use_container_width=True
# )