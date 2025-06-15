import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime

# --- Ayarlar ---
DB_PATH = "sms_audit.db"
TABLE_AUDITS = "audits"
TABLE_AUDITORS = "auditors"
TABLE_ELEMENTS = "sms_elements"

# ICAO SMS Elementleri per Doc 9859
DEFAULT_ELEMENTS = [
    "Safety Policy and Objectives",
    "Safety Risk Management",
    "Safety Assurance",
    "Safety Promotion"
]

# Veritabanına bağlan ve tabloları oluştur
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
# Audit kayıtları
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_AUDITS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_no TEXT,
        audit_date TEXT,
        bolum TEXT,
        auditors TEXT,
        sms_elements TEXT,
        findings_json TEXT,
        risk_seviyesi TEXT,
        durum TEXT,
        created_at TEXT
    )
""" )
# Denetçi listesi
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_AUDITORS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
""" )
# SMS Elementleri listesi
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_ELEMENTS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        element TEXT UNIQUE
    )
""" )
conn.commit()

# Varsayılan SMS elementlerini ekle
existing = pd.read_sql_query(f"SELECT element FROM {TABLE_ELEMENTS}", conn)["element"].tolist()
for elem in DEFAULT_ELEMENTS:
    if elem not in existing:
        cursor.execute(f"INSERT INTO {TABLE_ELEMENTS}(element) VALUES(?)", (elem,))
conn.commit()

# Streamlit konfigürasyonu
st.set_page_config(page_title="SMS Audit - ICAO 9859", layout="wide")
st.title("📊 SMS Audit (ICAO 9859)")

# Mevcut denetçiler ve elementleri çek
auditors_df = pd.read_sql_query(f"SELECT name FROM {TABLE_AUDITORS} ORDER BY name", conn)
auditor_options = auditors_df["name"].tolist()
elements_df = pd.read_sql_query(f"SELECT element FROM {TABLE_ELEMENTS} ORDER BY element", conn)
element_options = elements_df["element"].tolist()

# Sekmeler oluştur
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Yeni Rapor Ekle",
    "📈 Dashboard & Filtre",
    "📋 Kayıtlı Raporlar",
    "⚙️ Ayarlar"
])

# 1️⃣ Yeni Rapor Ekle with optional findings
with tab1:
    st.subheader("➕ Yeni SMS Denetim Kaydı")
    with st.form("form_new_audit"):
        # Temel bilgiler
        col1, col2 = st.columns(2)
        with col1:
            audit_no = st.text_input("Denetim No", value=f"SMS-AUD-{datetime.now():%Y%m%d}-XX")
            audit_date = st.date_input("Denetim Tarihi", value=datetime.today())
            bolum = st.selectbox("Bölüm", ["Flight Ops", "Maintenance", "Training", "Administration"])
            auditors_sel = st.multiselect("Denetçi(ler)", options=auditor_options)
        with col2:
            sms_elems_sel = st.multiselect("SMS Element(ler)", options=element_options)
            risk_seviyesi = st.selectbox("Risk Seviyesi", ["Low", "Medium", "High"])
            durum = st.selectbox("Durum", ["Open", "In Progress", "Closed"])
        # Bulgular sayısı ve detaylar
        num_bulgular = st.number_input("Bulgu Sayısı", min_value=0, step=1)
        findings_list = []
        if num_bulgular > 0:
            for i in range(int(num_bulgular)):
                st.markdown(f"### Bulgu {i+1}")
                level = st.selectbox(f"Seviye (1/2/Observer) #{i+1}", options=["1", "2", "Observer"], key=f"level_{i}")
                desc = st.text_input(f"Bulgu Açıklaması #{i+1}", key=f"desc_{i}")
                root_cause = st.text_area(f"Kök Neden #{i+1}", key=f"root_{i}")
                corrective = st.text_area(f"Düzeltici Faaliyet #{i+1}", key=f"corr_{i}")
                findings_list.append({
                    "seviye": level,
                    "aciklama": desc,
                    "kok_neden": root_cause,
                    "duzeltici_faaliyet": corrective
                })
        else:
            st.info("📭 Herhangi bir bulgu girilmedi.")
        submitted = st.form_submit_button("Kaydet")
        if submitted:
            findings_json = json.dumps(findings_list, ensure_ascii=False)
            cursor.execute(
                f"INSERT INTO {TABLE_AUDITS} (audit_no,audit_date,bolum,auditors,sms_elements,findings_json,risk_seviyesi,durum,created_at) VALUES (?,?,?,?,?,?,?,?,?)", 
                (
                    audit_no,
                    audit_date.strftime("%Y-%m-%d"),
                    bolum,
                    ", ".join(auditors_sel),
                    ", ".join(sms_elems_sel),
                    findings_json,
                    risk_seviyesi,
                    durum,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            st.success("✅ SMS denetimi başarıyla kaydedildi.")

# 2️⃣ Dashboard & Filtre
with tab2:
    df_all = pd.read_sql_query(f"SELECT * FROM {TABLE_AUDITS}", conn)
    if not df_all.empty:
        df_all["audit_date"] = pd.to_datetime(df_all["audit_date"])
    # Sidebar filtreler
    with st.sidebar:
        st.header("🔍 Filtreler")
        tarih_araligi = st.date_input("Denetim Tarihi Aralığı", [])
        auditor_sel = st.multiselect("Denetçi Seç", options=df_all["auditors"].str.split(", ").explode().unique() if not df_all.empty else [])
        elem_sel = st.multiselect("SMS Elementi Seç", options=df_all["sms_elements"].str.split(", ").explode().unique() if not df_all.empty else [])
        st.markdown("---")
        if st.button("Sıfırla Filtreler"):
            tarih_araligi, auditor_sel, elem_sel = [], [], []
    # Filtre uygulama
    df = df_all.copy()
    if isinstance(tarih_araligi, list) and len(tarih_araligi) == 2:
        start, end = tarih_araligi
        df = df[(df["audit_date"] >= pd.to_datetime(start)) & (df["audit_date"] <= pd.to_datetime(end))]
    if auditor_sel:
        df = df[df["auditors"].apply(lambda x: any(a in x.split(", ") for a in auditor_sel))]
    if elem_sel:
        df = df[df["sms_elements"].apply(lambda x: any(e in x.split(", ") for e in elem_sel))]
    # Özet panosu
    st.subheader("📈 Genel Durum")
    total = len(df)
    closed = len(df[df["durum"] == "Closed"])
    open_ = len(df[df["durum"] == "Open"])
    high = len(df[df["risk_seviyesi"] == "High"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", total)
    c2.metric("Kapalı", f"{closed} ({(closed/total*100):.0f}%)" if total else "0 (0%)")
    c3.metric("Açık", open_)
    c4.metric("Yüksek Risk", high)
    # Bulgular tablosu
    st.subheader("📝 SMS Audit Bulguları")
    if df.empty:
        st.info("Veri bulunamadı.")
    else:
        all_findings = df["findings_json"].apply(lambda x: json.loads(x))
        levels = [f["seviye"] for lst in all_findings for f in lst]
        level_counts = pd.Series(levels).value_counts()
        st.write("**Seviye Bazlı Bulgular Sayısı**")
        st.bar_chart(level_counts)
        # Expanded table
        def expand_findings(row):
            items = json.loads(row)
            if not items:
                return ""
            return "; ".join([f"[{i+1}] {f['seviye']}: {f['aciklama']}" for i, f in enumerate(items)])
        df_show = df.copy()
        df_show["findings"] = df_show["findings_json"].apply(expand_findings)
        st.dataframe(df_show[["audit_no","audit_date","bolum","auditors","sms_elements","findings","risk_seviyesi","durum"]], use_container_width=True)

# 3️⃣ Kayıtlı Raporlar
with tab3:
    st.subheader("📋 Kayıtlı SMS Denetimleri")
    df_saved = pd.read_sql_query(f"SELECT * FROM {TABLE_AUDITS} ORDER BY created_at DESC", conn)
    if df_saved.empty:
        st.info("Henüz kayıt yok.")
    else:
        df_saved["audit_date"] = pd.to_datetime(df_saved["audit_date"])
        df_saved["created_at"] = pd.to_datetime(df_saved["created_at"])
        st.dataframe(df_saved, use_container_width=True)
        st.download_button("📥 CSV İndir", df_saved.to_csv(index=False), "sms_audit.csv", "text/csv")

# 4️⃣ Ayarlar
with tab4:
    st.subheader("⚙️ Ayarlar")
    # Denetçi ekleme
    with st.form("form_add_auditor"):
        new_aud = st.text_input("Yeni Denetçi Ekle")
        if st.form_submit_button("Ekle Denetçi") and new_aud:
            try:
                cursor.execute(f"INSERT INTO {TABLE_AUDITORS}(name) VALUES(?)", (new_aud,))
                conn.commit()
                st.success(f"Denetçi '{new_aud}' eklendi.")
            except sqlite3.IntegrityError:
                st.warning("Denetçi zaten mevcut.")
    # Element ekleme
    st.markdown("**SMS Elementleri:**")
    elems = pd.read_sql_query(f"SELECT element FROM {TABLE_ELEMENTS}", conn)["element"].tolist()
    for e in elems:
        st.write(f"- {e}")
    with st.form("form_add_element"):
        new_elem = st.text_input("Yeni SMS Elementi Ekle")
        if st.form_submit_button("Ekle Element") and new_elem:
            try:
                cursor.execute(f"INSERT INTO {TABLE_ELEMENTS}(element) VALUES(?)", (new_elem,))
                conn.commit()
                st.success(f"Element '{new_elem}' eklendi.")
            except sqlite3.IntegrityError:
                st.warning("Element zaten mevcut.")
