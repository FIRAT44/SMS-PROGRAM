import time
import streamlit as st
import sqlite3
import os
from datetime import datetime
import pandas as pd
import re  # slugify yerine kullanılacak
from utils.auth import login_required
login_required()

st.set_page_config(page_title="⚠️ ICAO Hazard Yönetimi", layout="wide")
st.title("⚠️ ICAO 9859 - Hazard Rapor Yönetimi")

# Veritabanı
conn = sqlite3.connect("sms_database2.db", check_same_thread=False)
cursor = conn.cursor()

# Upload klasörü
HAZARD_EKLER_DIR = "uploads/hazard_ekler"
os.makedirs(HAZARD_EKLER_DIR, exist_ok=True)



# Gerekli tablolar
cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_risk (
    report_number TEXT PRIMARY KEY,
    tehlike_alani TEXT,
    tehlike_tanimi TEXT,
    riskli_olaylar TEXT,
    mevcut_onlemler TEXT,
    siddet_etkisi TEXT,
    olasilik TEXT,
    raporlanan_risk TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_onlemler (
    report_number TEXT PRIMARY KEY,
    kontrol_onlemleri TEXT,
    sorumlu_kisi TEXT,
    termin TEXT,
    gerceklesen_faaliyet TEXT,
    revize_risk TEXT,
    etkinlik_kontrol TEXT,
    etkinlik_sonrasi_risk TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_kapanis (
    report_number TEXT PRIMARY KEY,
    durum TEXT,
    degerlendirme_tarihi TEXT,
    kapanis_tarihi TEXT,
    sonuc_durumu TEXT,
    atama_durumu TEXT,
    geri_bildirim_durumu TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_progress (
    report_number TEXT PRIMARY KEY,
    tamamlanan INTEGER,
    toplam INTEGER,
    yuzde INTEGER,
    eksikler TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_ekler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_number TEXT,
    dosya_adi TEXT,
    yol TEXT,
    tarih TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
# Çoklu önlem tablosu (eğer yoksa oluştur)
# Veritabanı bağlantısından sonra çalıştırılmalı
cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        risk_id INTEGER,
        onlem_aciklama TEXT,
        sorumlu TEXT,
        termin TEXT,
        gerceklesen TEXT,
        revize_risk TEXT,
        revize_siddet TEXT,
        revize_olasilik TEXT,
        etkinlik_kontrol TEXT,
        etkinlik_sonrasi TEXT,
        etkinlik_sonrasi_siddet TEXT,
        etkinlik_sonrasi_olasilik TEXT
    )
""")

# ✅ report_number + risk_id için UNIQUE INDEX oluştur
cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_onlem_unique
    ON hazard_onlem_coklu (report_number, risk_id)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS hazard_geri_izleme (
    report_number TEXT PRIMARY KEY,
    geri_bildirim TEXT,
    bildiren_kisi TEXT,
    komite_yorumu TEXT,
    tekrar_gz_tarihi TEXT
)
""")
conn.commit()



def plot_screen():
    
    from pyvis.network import Network
    import streamlit.components.v1 as components
    import tempfile
    import os
    import base64

    st.markdown("---")
    st.subheader("🌳 Rapor Akış Görseli (Dinamik, Renkli, Açıklamalı)")

    # Tablo kontrolü (önlem tablosu varsa oluştur)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        risk_id INTEGER,
        onlem_aciklama TEXT,
        sorumlu TEXT,
        termin TEXT,
        gerceklesen TEXT,
        revize_risk TEXT,
        etkinlik_kontrol TEXT,
        etkinlik_sonrasi TEXT
    )
    """)
    conn.commit()

    # Veriler
    riskler = pd.read_sql_query("""
        SELECT id, tehlike_tanimi, mevcut_onlemler, raporlanan_risk 
        FROM hazard_risk 
        WHERE report_number = ?
    """, conn, params=(rapor_no,))

    onlemler = pd.read_sql_query("""
        SELECT risk_id, onlem_aciklama, sorumlu, termin, etkinlik_kontrol 
        FROM hazard_onlem_coklu 
        WHERE report_number = ?
    """, conn, params=(rapor_no,))

    # Pyvis ağı
    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#000000", directed=True)
    # Hierarchical düzeni için ayar
    net.set_options("""
    {
    "layout": {
        "hierarchical": {
        "enabled": true,
        "levelSeparation": 400,
        "nodeSpacing": 500,
        "direction": "UD",
        "sortMethod": "directed"
        }
    },
    "nodes": {
        "shape": "box",
        "font": {
        "size": 20,
        "face": "Arial",
        "bold": true
        }
    },
    "edges": {
        "arrows": {
        "to": { "enabled": true }
        },
        "smooth": {
        "type": "cubicBezier",
        "roundness": 0.4
        }
    },
    "physics": {
        "enabled": false
    }
    }
    """)


    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#000000", directed=True)

    # Temel düğümler
    net.add_node("rapor", label="📄 Rapor", color="#b3d9ff", title="Hazard rapor kök noktası", level=0)
    net.add_node("geribildirim", label="📤 Geri Bildirim", color="#d0c2f2", title="Originator'a Geri Bildirim ve Komite Yorumu", level=2)
    net.add_node("kapanis", label="✅ Kapanış", color="#e6ffe6", title="Risk değerlendirme tamamlanma noktası", level=3)

    # Risk renk/font haritaları
    renk_map = {
        "Low": "#fffac8",
        "Medium": "#ffe599",
        "High": "#ffb347",
        "Extreme": "#ff6961"
    }

    font_map = {
        "Low": 18,
        "Medium": 20,
        "High": 22,
        "Extreme": 24
    }

    # Önlem etkinlik stil haritası
    etkinlik_map = {
        "Etkili": {"color": "#a1e3a1", "size": 18},
        "Kısmen Etkili": {"color": "#fff1b5", "size": 20},
        "Etkisiz": {"color": "#ff9999", "size": 22}
    }

    # Rapor > Risk > Önlem > Geri Bildirim > Kapanış
    for _, risk in riskler.iterrows():
        risk_id = f"risk_{risk['id']}"
        risk_seviye = (risk["raporlanan_risk"] or "Low").strip()

        net.add_node(
            risk_id,
            label=f"⚠️ {risk['tehlike_tanimi'][:30]}",
            color=renk_map.get(risk_seviye, "#ffe599"),
            title=f"{risk['tehlike_tanimi']} {risk_seviye} {risk['mevcut_onlemler'] or '-'}",
            font={"size": font_map.get(risk_seviye, 20)}
        )
        net.add_edge("rapor", risk_id, label="Risk", width=1.5 if risk_seviye in ["High", "Extreme"] else 0.7)

        ilgili_onlemler = onlemler[onlemler["risk_id"] == risk["id"]]
        for j, onlem in ilgili_onlemler.iterrows():
            onlem_id = f"onlem_{risk['id']}_{j}"
            etkinlik = onlem.get("etkinlik_kontrol", "Kısmen Etkili")
            stil = etkinlik_map.get(etkinlik, {"color": "#c2f0c2", "size": 18})

            net.add_node(
                onlem_id,
                label=f"🧰 {onlem['onlem_aciklama'][:30]}" if onlem["onlem_aciklama"] else "🧰 Önlem",
                color=stil["color"],
                title=f"<b>Önlem:</b> {onlem['onlem_aciklama']}<br><b>Sorumlu:</b> {onlem['sorumlu']}<br><b>Termin:</b> {onlem['termin']}<br><b>Etkinlik:</b> {etkinlik}",
                font={"size": stil["size"]}
            )
            net.add_edge(risk_id, onlem_id, label="Önlem", width=0.5)
            net.add_edge(onlem_id, "geribildirim", label="Geri Bildirim", width=0.7)

    # Geri Bildirim → Kapanış
    net.add_edge("geribildirim", "kapanis", label="Tamamlandı", width=1.0)

    # HTML dosyasına yaz
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        html_path = tmp_file.name

    # Gömülü görünüm
    components.html(open(html_path, 'r', encoding='utf-8').read(), height=720)

    # 🌐 Yeni sekmede açma
    st.markdown("### 🌐 Diyagramı Yeni Sekmede Aç")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        b64 = base64.b64encode(html_content.encode("utf-8")).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="rapor_akis.html" target="_blank">🖥️ Yeni Sekmede Aç (Tam Ekran)</a>'
        st.markdown(href, unsafe_allow_html=True)


# Eksik sütunları kontrol edip ekleyelim
def ensure_column_exists(table_name, column_name, column_type="TEXT"):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()



# Güncellenmiş tekli hazard rapor ZIP + tüm detaylı Excel içeren versiyon
import os
import zipfile
import io
import pandas as pd
import sqlite3
import base64

# ZIP fonksiyonu yeniden: tüm ek dosyaları dahil edilerek güncellenmiş hali
# Tüm ek dosyaları doğru klasörden alarak ekleyen güncel final fonksiyon
# Genişletilmiş versiyon: hem klasör bazlı hem de isim bazlı ekleri ekleyen final fonksiyon
def detayli_hazard_rapor_zip_uret_final_genis(report_number, conn):
    import os, zipfile, io, pandas as pd, base64

    # Tüm verileri çek
    rapor_df = pd.read_sql_query("SELECT * FROM hazard_reports WHERE report_number = ?", conn, params=(report_number,))
    durum_df = pd.read_sql_query("SELECT * FROM hazard_kapanis WHERE report_number = ?", conn, params=(report_number,))
    geri_df = pd.read_sql_query("SELECT * FROM hazard_geri_izleme WHERE report_number = ?", conn, params=(report_number,))
    progress_df = pd.read_sql_query("SELECT * FROM hazard_progress WHERE report_number = ?", conn, params=(report_number,))
    risk_df = pd.read_sql_query("SELECT * FROM hazard_risk WHERE report_number = ?", conn, params=(report_number,))
    onlem_df = pd.read_sql_query("SELECT * FROM hazard_onlem_coklu WHERE report_number = ?", conn, params=(report_number,))

    # Özet verisi
    ozet_df = pd.DataFrame([{
        "Rapor No": report_number,
        "Durum": durum_df["durum"].iloc[0] if not durum_df.empty else "-",
        "Rapor Türü": rapor_df["rapor_turu"].iloc[0] if not rapor_df.empty else "-",
        "Rapor Konusu": rapor_df["rapor_konusu"].iloc[0] if not rapor_df.empty else "-",
        "Risk Sayısı": len(risk_df),
        "Önlem Sayısı": len(onlem_df),
        "Tamamlanma Yüzdesi": progress_df["yuzde"].iloc[0] if not progress_df.empty else "-",
        "Gözden Geçirme Tarihi": geri_df["tekrar_gz_tarihi"].iloc[0] if not geri_df.empty else "-"
    }])

    # Excel oluştur
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine="openpyxl") as writer:
        ozet_df.to_excel(writer, index=False, sheet_name="🧾 Ozet")
        if not rapor_df.empty:
            rapor_df.to_excel(writer, index=False, sheet_name="📄 Rapor")
        if not risk_df.empty:
            risk_df.to_excel(writer, index=False, sheet_name="⚠️ Riskler")
        if not onlem_df.empty:
            onlem_df.to_excel(writer, index=False, sheet_name="🧰 Onlemler")
        if not geri_df.empty:
            geri_df.to_excel(writer, index=False, sheet_name="🔁 Geri Bildirim")
        if not progress_df.empty:
            progress_df.to_excel(writer, index=False, sheet_name="📈 Tamamlanma")
        if not durum_df.empty:
            durum_df.to_excel(writer, index=False, sheet_name="📋 Kapanış")
    excel_io.seek(0)

    # ZIP belleğe yaz
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(f"{report_number}/rapor_dosyasi.xlsx", excel_io.read())

        # Klasör olarak ekler varsa
        ekler_klasor = f"uploads/hazard_ekler/{report_number}"
        if os.path.exists(ekler_klasor):
            for root, _, files in os.walk(ekler_klasor):
                for file in files:
                    full_path = os.path.join(root, file)
                    zipf.write(full_path, arcname=f"{report_number}/ekler/{file}")

        # Tek dizin içinde varsa ve adı rapor_no içeriyorsa
        ekler_root = f"uploads/hazard_ekler"
        if os.path.exists(ekler_root):
            for root, _, files in os.walk(ekler_root):
                for file in files:
                    if report_number in file:
                        full_path = os.path.join(root, file)
                        zipf.write(full_path, arcname=f"{report_number}/ekler/{file}")

    zip_io.seek(0)
    b64_zip = base64.b64encode(zip_io.read()).decode()
    href = f'<a href="data:application/zip;base64,{b64_zip}" download="rapor_{report_number}.zip">📥 ZIP Dosyasını İndir</a>'
    return href





# Gerekli tüm alanları kontrol et
columns_needed = [
    ("durum", "TEXT"),
    ("degerlendirme_tarihi", "TEXT"),
    ("kapanis_tarihi", "TEXT"),
    ("sonuc_durumu", "TEXT"),
    ("atama_durumu", "TEXT"),
    ("geri_bildirim_durumu", "TEXT")
]

for col_name, col_type in columns_needed:
    ensure_column_exists("hazard_kapanis", col_name, col_type)



# Risk matrisi tanımı
siddet_list = ["1 - Az", "2 - Küçük", "3 - Orta", "4 - Ciddi", "5 - Felaket"]
olasilik_list = ["1 - Nadir", "2 - Düşük", "3 - Orta", "4 - Yüksek", "5 - Sık"]

risk_matrix_df = pd.DataFrame(
    [
        ["Low", "Low", "Medium", "High", "High"],
        ["Low", "Medium", "Medium", "High", "Extreme"],
        ["Medium", "Medium", "High", "High", "Extreme"],
        ["Medium", "High", "High", "Extreme", "Extreme"],
        ["High", "High", "Extreme", "Extreme", "Extreme"]
    ],
    columns=siddet_list,
    index=olasilik_list
)

# Renkleme için stil fonksiyonu
def renkli_goster(val):
    renk_map = {
        "Low": "#b7f0ad",       # yeşil
        "Medium": "#f9f871",    # sarı
        "High": "#fdb36b",      # turuncu
        "Extreme": "#f77f7f"    # kırmızı
    }
    arka_renk = renk_map.get(val, "white")
    return f"background-color: {arka_renk}; color: black; text-align: center; font-weight: bold;"




# Sidebar'da hazard_reports'tan numara çek
st.sidebar.header("🔍 Rapor Seçimi")

raporlar_df = pd.read_sql_query("SELECT report_number FROM hazard_reports ORDER BY report_number DESC", conn)

if not raporlar_df.empty:
    rapor_no = st.sidebar.selectbox("Rapor Numarası", raporlar_df["report_number"].tolist())

    if rapor_no:
        progress = cursor.execute("SELECT * FROM hazard_progress WHERE report_number = ?", (rapor_no,)).fetchone()
        if progress:
            yuzde = progress[3]
            eksik_listesi = progress[4]

            st.sidebar.markdown("### 📊 Bu Raporun Durumu")
            st.sidebar.progress(yuzde / 100)
            st.sidebar.caption(f"Tamamlanma: %{yuzde}")
            if eksik_listesi:
                st.sidebar.warning(f"🧩 Eksik: {eksik_listesi}")
            else:
                st.sidebar.success("✅ Tüm bölümler tamamlanmış!")
        else:
            st.sidebar.info("ℹ️ Henüz değerlendirme yapılmadı.")
else:
    st.sidebar.warning("📭 Henüz hazard raporu bulunmamaktadır.")
    rapor_no = None


    
def coklu_destek_funksiyonu():
    if st.sidebar.button("🛠️ Çoklu Risk Desteğini Aktif Et"):
        try:
            cursor.execute("ALTER TABLE hazard_risk RENAME TO hazard_risk_old")
            conn.commit()
            st.sidebar.success("✅ Eski hazard_risk tablosu yeniden adlandırıldı.")

            cursor.execute("""
                CREATE TABLE hazard_risk (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_number TEXT,
                    tehlike_alani TEXT,
                    tehlike_tanimi TEXT,
                    riskli_olaylar TEXT,
                    mevcut_onlemler TEXT,
                    siddet_etkisi TEXT,
                    olasilik TEXT,
                    raporlanan_risk TEXT
                )
            """)
            conn.commit()
            st.sidebar.success("✅ Yeni hazard_risk tablosu oluşturuldu.")



            # Çoklu önlem tablosu varsa oluştur
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT,
            risk_id INTEGER,
            onlem_aciklama TEXT,
            sorumlu TEXT,
            termin TEXT,
            gerceklesen TEXT,
            revize_risk TEXT,
            revize_siddet TEXT,
            revize_olasilik TEXT,
            etkinlik_kontrol TEXT,
            etkinlik_sonrasi TEXT,
            etkinlik_sonrasi_siddet TEXT,
            etkinlik_sonrasi_olasilik TEXT)
            """)
            conn.commit()

            cursor.execute("""
                INSERT INTO hazard_risk (
                    report_number, tehlike_alani, tehlike_tanimi, riskli_olaylar,
                    mevcut_onlemler, siddet_etkisi, olasilik, raporlanan_risk
                )
                SELECT
                    report_number, tehlike_alani, tehlike_tanimi, riskli_olaylar,
                    mevcut_onlemler, siddet_etkisi, olasilik, raporlanan_risk
                FROM hazard_risk_old
            """)
            conn.commit()
            st.sidebar.success("✅ Veriler yeni tabloya aktarıldı.")

            cursor.execute("DROP TABLE hazard_risk_old")
            conn.commit()
            st.sidebar.success("✅ Geçici tablo silindi. Artık çoklu risk desteği aktif!")
        except Exception as e:
            st.sidebar.error(f"❌ Geçiş sırasında hata oluştu: {e}")


def slugify(value):
    value = str(value).strip().lower()
    value = re.sub(r'[^a-zA-Z0-9\-_]', '_', value)
    return value

def guncelle_hazard_progress(report_number):
    # Kayıt kontrolü yap
    risk_kayit = cursor.execute("SELECT 1 FROM hazard_risk WHERE report_number = ?", (report_number,)).fetchone()
    onlem_kayit = cursor.execute("SELECT 1 FROM hazard_onlem_coklu WHERE report_number = ?", (report_number,)).fetchone()
    geri_kayit = cursor.execute("SELECT 1 FROM hazard_geri_izleme WHERE report_number = ?", (report_number,)).fetchone()
    kapanis_kayit = cursor.execute("SELECT 1 FROM hazard_kapanis WHERE report_number = ?", (report_number,)).fetchone()

    bolumler = {
        "Risk": bool(risk_kayit),
        "Önlem": bool(onlem_kayit),
        "Geri Bildirim": bool(geri_kayit),
        "Kapanış": bool(kapanis_kayit)
    }

    tamamlanan = sum(1 for v in bolumler.values() if v)
    toplam = len(bolumler)
    yuzde = int((tamamlanan / toplam) * 100)
    eksikler = ", ".join([k for k, v in bolumler.items() if not v])

    cursor.execute("""
        INSERT INTO hazard_progress (report_number, tamamlanan, toplam, yuzde, eksikler)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(report_number) DO UPDATE SET
            tamamlanan=excluded.tamamlanan,
            toplam=excluded.toplam,
            yuzde=excluded.yuzde,
            eksikler=excluded.eksikler
    """, (report_number, tamamlanan, toplam, yuzde, eksikler))
    conn.commit()


if rapor_no:
    tabs = st.tabs(["📄 Rapor Özeti","🛠️ ICAO Risk Değerlendirme", "✅ Önlem Takibi", "📤 Geri Bildirim ve İzleme","📈 Kapanış ve Değerlendirme", "📋 Durum Takibi", "📊 Dashboard & Arama"])

# Raporları getir
df = pd.read_sql_query("SELECT * FROM hazard_reports ORDER BY olay_tarihi DESC", conn)
if df.empty:
    st.info("📭 Henüz kayıtlı hazard raporu bulunmamaktadır.")
    st.stop()
else:
    
    secili_rapor_no = rapor_no

    UPLOAD_KLASORU = "uploads/hazard_ekler"
    os.makedirs(UPLOAD_KLASORU, exist_ok=True)



    with tabs[0]:
        # Seçilen raporu getir
        secili_rapor = df[df["report_number"] == secili_rapor_no].iloc[0]

        st.markdown(f"### 🧾 Rapor Numarası: `{secili_rapor['report_number']}`")
        st.markdown(f"**Rapor Türü:** {secili_rapor['rapor_turu']}")
        st.markdown(f"**Rapor Konusu:** {secili_rapor['rapor_konusu']}")
        st.markdown(f"**Olay Tarihi:** {secili_rapor['olay_tarihi']}")
        st.markdown(f"**Veri Giriş Tarihi:** {secili_rapor['veri_giris_tarihi']}")


        st.markdown("---")
        st.warning("🛑 Bu raporu sistemden kalıcı olarak silmek üzeresiniz.")

        if "silme_onay" not in st.session_state:
            st.session_state["silme_onay"] = False

        if not st.session_state["silme_onay"]:
            if st.button("🗑 Raporu Sil"):
                st.session_state["silme_onay"] = True
                st.rerun()
        else:
            st.error("⚠️ Emin misiniz? Bu işlem geri alınamaz.")
            col_onay, col_vazgec = st.columns(2)

            with col_onay:
                if st.button("✅ Evet, Sil"):
                    try:
                        cursor.execute("DELETE FROM hazard_reports WHERE report_number = ?", (secili_rapor_no,))
                        cursor.execute("DELETE FROM hazard_risk WHERE report_number = ?", (secili_rapor_no,))
                        cursor.execute("DELETE FROM hazard_onlem_coklu WHERE report_number = ?", (secili_rapor_no,))
                        cursor.execute("DELETE FROM hazard_progress WHERE report_number = ?", (secili_rapor_no,))
                        cursor.execute("DELETE FROM hazard_geri_izleme WHERE report_number = ?", (secili_rapor_no,))
                        cursor.execute("DELETE FROM hazard_kapanis WHERE report_number = ?", (secili_rapor_no,))
                        conn.commit()

                        # Ekleri sil
                        ek_klasor_path = os.path.join("uploads/hazard_ekler", secili_rapor_no)
                        if os.path.exists(ek_klasor_path):
                            import shutil
                            shutil.rmtree(ek_klasor_path)

                        st.success("✅ Rapor ve tüm ilişkili veriler başarıyla silindi.")
                        st.session_state["silme_onay"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata oluştu: {e}")
                        st.session_state["silme_onay"] = False

            with col_vazgec:
                if st.button("❌ Vazgeç"):
                    st.session_state["silme_onay"] = False

        # Ozel cevaplar
        ozel_cevaplar = secili_rapor.get("ozel_cevaplar")
        if ozel_cevaplar:
            try:
                cevap_dict = eval(ozel_cevaplar) if isinstance(ozel_cevaplar, str) else ozel_cevaplar
                st.markdown("---")
                st.subheader("📝 Form Cevapları")
                for soru, cevap in cevap_dict.items():
                    st.markdown(f"**{soru}**: {cevap if cevap else '-'}")
            except Exception as e:
                st.error("❌ Cevaplar ayrıştırılamadı.")
                st.text(ozel_cevaplar)
        else:
            st.info("ℹ️ Bu rapora özel form cevabı girilmemiş.")

        # Ek dosya yükleme bölümü
        st.markdown("---")
        st.subheader("📎 Ek Dosya Yükle")
        ek_dosya = st.file_uploader("Bir ek dosya yükleyin (PDF, Görsel, Belge vb.)", type=None, key="upload_hazard")

        ek_kayit_klasoru = os.path.join(UPLOAD_KLASORU, secili_rapor_no)
        os.makedirs(ek_kayit_klasoru, exist_ok=True)

        if ek_dosya:
            dosya_yolu = os.path.join(ek_kayit_klasoru, ek_dosya.name)
            with open(dosya_yolu, "wb") as f:
                f.write(ek_dosya.read())
            st.success(f"✅ Dosya yüklendi: {ek_dosya.name}")
            guncelle_hazard_progress(secili_rapor_no)
            time.sleep(1)
            #st.rerun()

        st.markdown("### 📂 Bu Rapora Ait Ekler")
        ekli_dosyalar = os.listdir(ek_kayit_klasoru)

        if ekli_dosyalar:
            for dosya in ekli_dosyalar:
                dosya_yolu = os.path.join(ek_kayit_klasoru, dosya)
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(f"📄 {dosya}")
                with col2:
                    if st.button("🗑 Sil", key=f"sil_hazard_{dosya}"):
                        os.remove(dosya_yolu)
                        st.success(f"🗑 {dosya} silindi.")
                        guncelle_hazard_progress(secili_rapor_no)
                        time.sleep(1)
                        #st.rerun()
        else:
            st.info("ℹ️ Bu rapora henüz dosya eklenmemiş.")
        
        plot_screen()


    with tabs[1]:
        aktif_seceme = 2
        st.subheader("🛠️ ICAO Risk Değerlendirme (Çoklu ve Güncellenebilir)")

        # 📋 Risk Tablosu Başta Gösterilsin
        st.markdown("### 📋 Kayıtlı Riskler (Hızlı Liste)")
        riskler_df = pd.read_sql_query("""
            SELECT rowid AS risk_rowid, id, tehlike_alani, tehlike_tanimi, raporlanan_risk 
            FROM hazard_risk 
            WHERE report_number = ?
        """, conn, params=(rapor_no,))

        if not riskler_df.empty:
            st.dataframe(riskler_df[["tehlike_alani", "tehlike_tanimi", "raporlanan_risk"]], use_container_width=True)
        else:
            st.info("📭 Bu rapora ait henüz risk girilmemiş.")

        # Mevcut riskleri veritabanından çek
        risk_kayitlari = pd.read_sql_query("""
            SELECT id, tehlike_alani, tehlike_tanimi, riskli_olaylar, mevcut_onlemler,
                siddet_etkisi, olasilik, raporlanan_risk
            FROM hazard_risk
            WHERE report_number = ?
            ORDER BY id ASC
        """, conn, params=(rapor_no,))

        st.markdown(f"### 🌿 Toplam Risk Dalı: {len(risk_kayitlari)}")

        for i, row in risk_kayitlari.iterrows():
            with st.expander(f"📌 Risk Dalı #{i+1} — {row['tehlike_tanimi'][:40]}...", expanded=(i == 0)):
                with st.form(f"risk_update_form_{row['id']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        tehlike_alani = st.text_input("Tehlike Alanı", value=row["tehlike_alani"], key=f"ta_{row['id']}")
                        tehlike_tanimi = st.text_area("Tehlike Tanımı", value=row["tehlike_tanimi"], key=f"tt_{row['id']}")
                        riskli_olaylar = st.text_area("Tehlikeye Bağlı Riskli Olaylar", value=row["riskli_olaylar"], key=f"ro_{row['id']}")
                        mevcut_onlemler = st.text_area("Mevcut Önlemler", value=row["mevcut_onlemler"], key=f"mo_{row['id']}")

                    with col2:
                        siddet_etkisi = st.selectbox(
                                                        "Şiddet Etkisi",
                                                        siddet_list,
                                                        index=siddet_list.index(row["siddet_etkisi"]) if row["siddet_etkisi"] in siddet_list else 0,
                                                        key=f"sid_{row['id']}"
                                                    )
                        olasilik = st.selectbox(
                                                        "Olasılık",
                                                        olasilik_list,
                                                        index=olasilik_list.index(row["olasilik"]) if row["olasilik"] in olasilik_list else 0,
                                                        key=f"ola_{row['id']}"
                                                    )

                        # Otomatik hesapla
                        raporlanan_risk = risk_matrix_df.loc[olasilik, siddet_etkisi]
                        st.markdown(f"### 🧮 Otomatik Hesaplanan Raporlanan Risk: **{raporlanan_risk}**")

                    if st.form_submit_button("💾 Güncelle"):
                        cursor.execute("""
                            UPDATE hazard_risk SET
                                tehlike_alani = ?, tehlike_tanimi = ?, riskli_olaylar = ?, mevcut_onlemler = ?,
                                siddet_etkisi = ?, olasilik = ?, raporlanan_risk = ?
                            WHERE id = ?
                        """, (
                            tehlike_alani, tehlike_tanimi, riskli_olaylar, mevcut_onlemler,
                            siddet_etkisi, olasilik, raporlanan_risk, row["id"]
                        ))
                        conn.commit()
                        st.success("✅ Güncellendi!")
                        guncelle_hazard_progress(secili_rapor_no)
                        st.rerun()
        st.markdown("### 🔢 Risk Matrisi Simülasyonu")
        st.dataframe(risk_matrix_df.style.applymap(renkli_goster), use_container_width=True)
        st.markdown("---")
        st.markdown("### ➕ Yeni Risk Dalı Ekle")

        with st.form("yeni_risk_form"):
            col1, col2 = st.columns(2)
            with col1:
                yeni_tehlike_alani = st.text_input("Tehlike Alanı")
                yeni_tehlike_tanimi = st.text_area("Tehlike Tanımı")
                yeni_riskli_olaylar = st.text_area("Tehlikeye Bağlı Riskli Olaylar")
                yeni_mevcut_onlemler = st.text_area("Mevcut Önlemler")

            with col2:
                yeni_siddet_etkisi = st.selectbox("Şiddet Etkisi", siddet_list)
                yeni_olasilik = st.selectbox("Olasılık", olasilik_list)
                yeni_risk_seviyesi = risk_matrix_df.loc[yeni_olasilik, yeni_siddet_etkisi]
                st.markdown(f"### 🧮 Hesaplanan Raporlanan Risk: **{yeni_risk_seviyesi}**")

            if st.form_submit_button("➕ Yeni Risk Ekle"):
                cursor.execute("""
                            INSERT INTO hazard_risk (
                                report_number, tehlike_alani, tehlike_tanimi, riskli_olaylar,
                                mevcut_onlemler, siddet_etkisi, olasilik, raporlanan_risk
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            rapor_no, yeni_tehlike_alani, yeni_tehlike_tanimi, yeni_riskli_olaylar,
                            yeni_mevcut_onlemler, yeni_siddet_etkisi, yeni_olasilik, yeni_risk_seviyesi
                            ))
                conn.commit()
                st.success("✅ Yeni risk dalı başarıyla eklendi.")
                guncelle_hazard_progress(secili_rapor_no)
                st.rerun()
            
        plot_screen()



    with tabs[2]:
        aktif_seceme = 2
        st.subheader("✅ Önlem Takibi")
        st.markdown("### 📋 Tüm Tanımlı Önlemler (Tablo Görünümü)")

        pd.set_option("display.max_colwidth", None)

        tum_onlemler_df = pd.read_sql_query("""
            SELECT r.tehlike_tanimi AS Risk, o.onlem_aciklama AS Önlem, o.sorumlu AS Sorumlu,
                o.termin AS Termin, o.revize_risk AS RevizeRisk, o.etkinlik_sonrasi AS EtkinlikSonrasi
            FROM hazard_onlem_coklu o
            LEFT JOIN hazard_risk r ON o.risk_id = r.id
            WHERE o.report_number = ?
            ORDER BY o.termin ASC
        """, conn, params=(secili_rapor_no,))

        if not tum_onlemler_df.empty:
            st.dataframe(tum_onlemler_df.style.set_properties(**{'white-space': 'pre-wrap'}), use_container_width=True)
        else:
            st.info("ℹ️ Bu rapora ait tablo görünümünde önlem bulunmamaktadır.")





        st.markdown("Her bir risk için ayrı önlem tanımlayın:")

        risk_kayitlari = pd.read_sql_query(
                "SELECT id, tehlike_tanimi FROM hazard_risk WHERE report_number = ?",
                conn, params=(secili_rapor_no,)
            )
        if risk_kayitlari.empty:
            st.warning("⚠️ Bu rapora ait henüz risk tanımı yapılmamış. Önlem tanımlayabilmek için önce risk girmelisiniz.")
        else:
            for _, risk_row in risk_kayitlari.iterrows():
                with st.expander(f"🛠️ Önlem Girişi - {risk_row['tehlike_tanimi'][:40]}", expanded=True):
                    # İlgili risk için tek bir önlem getir (varsa)
                    row_df = pd.read_sql_query("""
                        SELECT * FROM hazard_onlem_coklu
                        WHERE report_number = ? AND risk_id = ?
                    """, conn, params=(secili_rapor_no, risk_row['id']))

                    row = row_df.iloc[0].to_dict() if not row_df.empty else {}

                    with st.form(f"onlem_form_{risk_row['id']}"):
                        onlem_aciklama = st.text_area("Risk Kontrol Önlemleri", value=row.get("onlem_aciklama", ""))
                        sorumlu = st.text_input("Sorumlu", value=row.get("sorumlu", ""))
                        termin = st.date_input("Termin", value=pd.to_datetime(row.get("termin", datetime.today())))
                        gerceklesen = st.text_area("Gerçekleşen", value=row.get("gerceklesen", ""))

                        siddet_listesi = ["1 - Az", "2 - Küçük", "3 - Orta", "4 - Ciddi", "5 - Felaket"]
                        olasilik_listesi = ["1 - Nadir", "2 - Düşük", "3 - Orta", "4 - Yüksek", "5 - Sık"]

                        revize_siddet_deger = row.get("revize_siddet") or "1 - Az"
                        if revize_siddet_deger not in siddet_listesi:
                            revize_siddet_deger = "1 - Az"

                        revize_siddet = st.selectbox("Revize Şiddet", siddet_listesi,
                            index=siddet_listesi.index(revize_siddet_deger),
                            key=f"rev_s_{risk_row['id']}")
                        



                        revize_olasilik_deger = row.get("revize_olasilik") or "1 - Nadir"
                        if revize_olasilik_deger not in olasilik_listesi:
                            revize_olasilik_deger = "1 - Nadir"

                        revize_olasilik = st.selectbox("Revize Olasılık", olasilik_listesi,
                            index=olasilik_listesi.index(revize_olasilik_deger),
                            key=f"rev_o_{risk_row['id']}")



                        # Revize Risk (otomatik hesapla)
                        revize_risk = risk_matrix_df.loc[revize_olasilik, revize_siddet]
                        st.markdown(f"📊 Revize Risk: **{revize_risk}**")




                        etkinlik_kontrol = st.text_area("Etkinlik Kontrol", value=row.get("etkinlik_kontrol", ""))





                        etkinlik_sonrasi_siddet_deger = row.get("etkinlik_sonrasi_siddet") or "1 - Az"
                        if etkinlik_sonrasi_siddet_deger not in siddet_listesi:
                            etkinlik_sonrasi_siddet_deger = "1 - Az"

                        etkinlik_sonrasi_siddet = st.selectbox("Etkinlik Sonrası Şiddet", siddet_listesi,
                            index=siddet_listesi.index(etkinlik_sonrasi_siddet_deger),
                            key=f"etk_s_{risk_row['id']}")
                        




                        etkinlik_sonrasi_olasilik_deger = row.get("etkinlik_sonrasi_olasilik") or "1 - Nadir"
                        if etkinlik_sonrasi_olasilik_deger not in olasilik_listesi:
                            etkinlik_sonrasi_olasilik_deger = "1 - Nadir"

                        etkinlik_sonrasi_olasilik = st.selectbox("Etkinlik Sonrası Olasılık", olasilik_listesi,
                            index=olasilik_listesi.index(etkinlik_sonrasi_olasilik_deger),
                            key=f"etk_o_{risk_row['id']}")
                        







                        etkinlik_sonrasi = risk_matrix_df.loc[etkinlik_sonrasi_olasilik, etkinlik_sonrasi_siddet]
                        st.markdown(f"📊 Etkinlik Sonrası Risk: **{etkinlik_sonrasi}**")

                        kaydet = st.form_submit_button("💾 Kaydet")
                        

                    if kaydet:
                        # INSERT or UPDATE: Tekil kayıt garantili
                        cursor.execute("""
                            INSERT INTO hazard_onlem_coklu (
                                report_number, risk_id, onlem_aciklama, sorumlu, termin,
                                gerceklesen, revize_risk, revize_siddet, revize_olasilik,
                                etkinlik_kontrol, etkinlik_sonrasi, etkinlik_sonrasi_siddet, etkinlik_sonrasi_olasilik
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(report_number, risk_id) DO UPDATE SET
                                onlem_aciklama=excluded.onlem_aciklama,
                                sorumlu=excluded.sorumlu,
                                termin=excluded.termin,
                                gerceklesen=excluded.gerceklesen,
                                revize_risk=excluded.revize_risk,
                                revize_siddet=excluded.revize_siddet,
                                revize_olasilik=excluded.revize_olasilik,
                                etkinlik_kontrol=excluded.etkinlik_kontrol,
                                etkinlik_sonrasi=excluded.etkinlik_sonrasi,
                                etkinlik_sonrasi_siddet=excluded.etkinlik_sonrasi_siddet,
                                etkinlik_sonrasi_olasilik=excluded.etkinlik_sonrasi_olasilik
                        """, (
                            secili_rapor_no, risk_row['id'], onlem_aciklama, sorumlu, str(termin),
                            gerceklesen, revize_risk, revize_siddet, revize_olasilik,
                            etkinlik_kontrol, etkinlik_sonrasi, etkinlik_sonrasi_siddet, etkinlik_sonrasi_olasilik
                        ))
                        conn.commit()
                        st.success("✅ Önlem kaydedildi veya güncellendi.")
                        guncelle_hazard_progress(secili_rapor_no)
                        st.rerun()

        plot_screen()               

                        # with col2:
                        #     if st.form_submit_button("🗑 Sil"):
                        #         cursor.execute("DELETE FROM hazard_onlem_coklu WHERE id = ?", (row['id'],))
                        #         conn.commit()
                        #         st.success("🗑 Silindi")
                        #         st.rerun()

                    # if st.button(f"➕ Yeni Önlem Ekle ({risk_row['tehlike_tanimi'][:30]}...)", key=f"btn_ekle_{risk_row['id']}"):
                    #     with st.form(f"onlem_form_{risk_row['id']}"):
                    #         st.markdown("### ➕ Yeni Önlem Ekle")
                    #         st.info("Lütfen bu formu yalnızca yeni bir önlem eklemeniz gerekiyorsa doldurun. Mevcut önlemler yukarıda listelenmiştir.")
                    #         onlem_aciklama = st.text_area("Kontrol/Önleyici Faaliyet", key=f"onlem_{risk_row['id']}_aciklama")
                    #         sorumlu = st.text_input("Sorumlu Kişi", key=f"onlem_{risk_row['id']}_sorumlu")
                    #         termin = st.date_input("Termin Tarihi", key=f"onlem_{risk_row['id']}_termin")
                    #         gerceklesen = st.text_area("Gerçekleşen Faaliyet", key=f"onlem_{risk_row['id']}_gerceklesen")
                    #         revize_siddet = st.selectbox("Revize Şiddet Etkisi", ["1 - Az", "2 - Küçük", "3 - Orta", "4 - Ciddi", "5 - Felaket"], key=f"revize_siddet_yeni_{risk_row['id']}")
                    #         revize_olasilik = st.selectbox(
                    #                             "Revize Olasılık",
                    #                             ["1 - Nadir", "2 - Düşük", "3 - Orta", "4 - Yüksek", "5 - Sık"],
                    #                             index=["1 - Nadir", "2 - Düşük", "3 - Orta", "4 - Yüksek", "5 - Sık"].index(row.get("revize_olasilik", "1 - Nadir")),
                    #                             key=f"revize_olasilik_yeni_{risk_row['id']}" )
                                                
                    #         revize_risk = risk_matrix_df.loc[revize_olasilik, revize_siddet]
                    #         st.markdown(f"📊 Hesaplanan Revize Risk: **{revize_risk}**")
                    #         etkinlik_kontrol = st.text_area("Etkinlik Kontrolü", key=f"onlem_{risk_row['id']}_etkinlik")
                    #         etkinlik_sonrasi_siddet = st.selectbox("Etkinlik Sonrası Şiddet", ["1 - Az", "2 - Küçük", "3 - Orta", "4 - Ciddi", "5 - Felaket"], key=f"sonrasi_siddet_yeni_{risk_row['id']}")
                    #         etkinlik_sonrasi_olasilik = st.selectbox("Etkinlik Sonrası Olasılık", ["1 - Nadir", "2 - Düşük", "3 - Orta", "4 - Yüksek", "5 - Sık"], key=f"sonrasi_olasilik_yeni_{risk_row['id']}")
                    #         etkinlik_sonrasi = risk_matrix_df.loc[etkinlik_sonrasi_olasilik, etkinlik_sonrasi_siddet]
                    #         st.markdown(f"📊 Hesaplanan Etkinlik Sonrası Risk: **{etkinlik_sonrasi}**")
                    #         kaydet = st.form_submit_button("💾 Kaydet")

                    #         if kaydet:
                    #             cursor.execute("""
                    #                 CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
                    #                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                    #                     report_number TEXT,
                    #                     risk_id INTEGER,
                    #                     onlem_aciklama TEXT,
                    #                     sorumlu TEXT,
                    #                     termin TEXT,
                    #                     gerceklesen TEXT,
                    #                     revize_risk TEXT,
                    #                     etkinlik_kontrol TEXT,
                    #                     etkinlik_sonrasi TEXT
                    #                 )
                    #             """)
                    #             cursor.execute("""
                    #             INSERT INTO hazard_onlem_coklu (
                    #                 report_number, risk_id, onlem_aciklama, sorumlu, termin,
                    #                 gerceklesen, revize_risk, revize_siddet, revize_olasilik,
                    #                 etkinlik_kontrol, etkinlik_sonrasi, etkinlik_sonrasi_siddet, etkinlik_sonrasi_olasilik
                    #             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    #         """, (
                    #             secili_rapor_no, risk_row['id'], onlem_aciklama, sorumlu, str(termin),
                    #             gerceklesen, revize_risk, revize_siddet, revize_olasilik,
                    #             etkinlik_kontrol, etkinlik_sonrasi, etkinlik_sonrasi_siddet, etkinlik_sonrasi_olasilik
                    #         ))
                    #             conn.commit()
                    #             st.success("✅ Önlem başarıyla kaydedildi.")
                    #             st.rerun()





    with tabs[3]:
        aktif_seceme = 2
        st.subheader("📤 Geri Bildirim ve İzleme")

        st.markdown("### 📋 Bu Rapora Ait Geri Bildirimler")

        geri_df = pd.read_sql_query("""
            SELECT report_number AS 'Rapor No', bildiren_kisi AS 'Bildiren Kişi',
                geri_bildirim AS 'Geri Bildirim', komite_yorumu AS 'Komite Yorumu',
                tekrar_gz_tarihi AS 'Gözden Geçirme Tarihi'
            FROM hazard_geri_izleme
            WHERE report_number = ?
            ORDER BY tekrar_gz_tarihi ASC
        """, conn, params=(rapor_no,))

        if not geri_df.empty:
            st.dataframe(geri_df.style.set_properties(**{'white-space': 'pre-wrap'}), use_container_width=True)
        else:
            st.info("📭 Bu rapora ait herhangi bir geri bildirim kaydı bulunmamaktadır.")

        # Önceki kayıt varsa çek
        geri_data = cursor.execute("SELECT * FROM hazard_geri_izleme WHERE report_number = ?", (rapor_no,)).fetchone()

        # Varsayılan değerler
        geri_bildirim = geri_data[1] if geri_data else ""
        bildiren_kisi = geri_data[2] if geri_data else ""
        komite_yorumu = geri_data[3] if geri_data else ""
        if geri_data and geri_data[4] not in (None, "", "None"):
            try:
                tekrar_gz_tarihi = pd.to_datetime(geri_data[4]).date()
            except:
                tekrar_gz_tarihi = None
        else:
            tekrar_gz_tarihi = None

        with st.form("geri_izleme_form"):
            st.markdown("### 🔁 Originator'a Geri Bildirim")
            bildiren_kisi = st.text_input("Geri Bildirimi Yapan", value=bildiren_kisi)
            geri_bildirim = st.text_area("Geri Bildirim İçeriği", value=geri_bildirim)

            st.markdown("### 🧭 Komite Gözden Geçirme (Opsiyonel)")
            komite_yorumu = st.text_area("Komite Yorumu", value=komite_yorumu)

            gozden_gecirilecek_mi = st.checkbox("🔁 Gözden Geçirme Tarihi Belirlemek İstiyorum", value=bool(tekrar_gz_tarihi))

            if gozden_gecirilecek_mi:
                tekrar_gz_tarihi = st.date_input("📅 Sonraki Gözden Geçirme Tarihi", value=tekrar_gz_tarihi)
            else:
                tekrar_gz_tarihi = None  # boş geçilsin

            if st.form_submit_button("💾 Kaydet / Güncelle"):
                cursor.execute("""
                    INSERT INTO hazard_geri_izleme (report_number, geri_bildirim, bildiren_kisi, komite_yorumu, tekrar_gz_tarihi)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(report_number) DO UPDATE SET
                        geri_bildirim=excluded.geri_bildirim,
                        bildiren_kisi=excluded.bildiren_kisi,
                        komite_yorumu=excluded.komite_yorumu,
                        tekrar_gz_tarihi=excluded.tekrar_gz_tarihi
                """, (rapor_no, geri_bildirim, bildiren_kisi, komite_yorumu, str(tekrar_gz_tarihi) if tekrar_gz_tarihi else None))

                conn.commit()
                st.success("✅ Geri bildirim ve izleme bilgileri kaydedildi.")
                guncelle_hazard_progress(secili_rapor_no)
                st.rerun()
        
        plot_screen()




    from datetime import date


    with tabs[4]:
        aktif_seceme = 2
       # Örnek rapor numarası seçimi (gelişmiş uygulamada dinamik gelir)
        st.markdown("### 📈 Kapanış ve Değerlendirme Paneli")

        # Rapor numaralarını al
        rapor_numaralari = rapor_no
        secili_rapor_no = st.selectbox("🆔 Rapor Numarası Seçin", rapor_numaralari)

        # Üstte rapor detaylarını göster
        df_rapor = pd.read_sql_query("SELECT * FROM hazard_reports WHERE report_number = ?", conn, params=(secili_rapor_no,))
        if not df_rapor.empty:
            st.markdown("#### 📄 Seçilen Raporun Detayları")
            st.dataframe(df_rapor, use_container_width=True)

        # hazard_kapanis tablosundan mevcut kayıt var mı kontrol et
        cursor.execute("SELECT * FROM hazard_kapanis WHERE report_number = ?", (secili_rapor_no,))
        mevcut_kayit = cursor.fetchone()

        # Form alanları (varsa varsayılan değerle dolu)
        durum = st.selectbox("Durum", ["Açık", "İşlemde", "Kapandı"], 
                            index=0 if not mevcut_kayit else ["Açık", "İşlemde", "Kapandı"].index(mevcut_kayit[1]))
        degerlendirme_tarihi = st.date_input("Değerlendirme Tarihi", 
                            value=date.today() if not mevcut_kayit else pd.to_datetime(mevcut_kayit[2]).date())
        kapanis_tarihi = st.date_input("Kapanış Tarihi", 
                            value=date.today() if not mevcut_kayit else pd.to_datetime(mevcut_kayit[3]).date())
        sonuc_durumu = st.text_input("Sonuç Durumu", value="" if not mevcut_kayit else mevcut_kayit[4])
        atama_durumu = st.text_input("Atama Durumu", value="" if not mevcut_kayit else mevcut_kayit[5])
        geri_bildirim_durumu = st.text_area("Geri Bildirim Durumu", value="" if not mevcut_kayit else mevcut_kayit[6])

        if st.button("💾 Kaydet", key="kapanis_kaydet"):
            cursor.execute("""
                INSERT INTO hazard_kapanis (
                    report_number, durum, degerlendirme_tarihi, kapanis_tarihi,
                    sonuc_durumu, atama_durumu, geri_bildirim_durumu
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_number) DO UPDATE SET
                    durum=excluded.durum,
                    degerlendirme_tarihi=excluded.degerlendirme_tarihi,
                    kapanis_tarihi=excluded.kapanis_tarihi,
                    sonuc_durumu=excluded.sonuc_durumu,
                    atama_durumu=excluded.atama_durumu,
                    geri_bildirim_durumu=excluded.geri_bildirim_durumu
            """, (
                secili_rapor_no, durum, degerlendirme_tarihi.strftime("%Y-%m-%d"),
                kapanis_tarihi.strftime("%Y-%m-%d"), sonuc_durumu,
                atama_durumu, geri_bildirim_durumu
            ))
            conn.commit()
            st.success("✅ Kapanış bilgileri kaydedildi.")
            guncelle_hazard_progress(secili_rapor_no)
            st.rerun()
        
        plot_screen()



    with tabs[5]:
        
        from datetime import datetime, timedelta

        st.markdown("### 📅 Tüm Raporlar İçin Termin Alarm Sistemi")

        # Tüm raporlardaki önlemleri çek
        onlem_df = pd.read_sql_query("""
            SELECT hr.report_number, hr.tehlike_tanimi, hoc.termin, hoc.onlem_aciklama
            FROM hazard_risk hr
            JOIN hazard_onlem_coklu hoc ON hr.id = hoc.risk_id
        """, conn)

        if not onlem_df.empty:
            today = datetime.today().date()
            yaklasan = []
            gecmis = []

            for _, row in onlem_df.iterrows():
                try:
                    termin_tarih = datetime.strptime(row["termin"], "%Y-%m-%d").date()
                    fark = (termin_tarih - today).days
                    if fark < 0:
                        gecmis.append((row["report_number"], row["tehlike_tanimi"], termin_tarih, row["onlem_aciklama"]))
                    elif fark <= 3:
                        yaklasan.append((row["report_number"], row["tehlike_tanimi"], termin_tarih, row["onlem_aciklama"]))
                except:
                    continue

            if yaklasan:
                st.warning("🟡 Yaklaşan Terminler (3 gün içinde):")
                for r, t, d, o in yaklasan:
                    st.markdown(f"- **{r}** → *{t[:30]}* → 📅 {d} → 🧰 {o[:40]}")

            if gecmis:
                st.error("🔴 Geçmiş Terminler:")
                for r, t, d, o in gecmis:
                    st.markdown(f"- **{r}** → *{t[:30]}* → 📅 {d} → 🧰 {o[:40]}")

            if not yaklasan and not gecmis:
                st.success("✅ Tüm önlemler zamanında veya termin tarihi uzak görünüyor.")
        else:
            st.info("📭 Henüz terminli önlem kaydı bulunmuyor.")

        
        st.markdown("### 📋 Raporların Durum Dağılımı")

        durum_df = pd.read_sql_query("""
            SELECT report_number AS 'Rapor No',
                   durum AS 'Durum',
                   degerlendirme_tarihi AS 'Değerlendirme Tarihi',
                   kapanis_tarihi AS 'Kapanış Tarihi',
                   sonuc_durumu AS 'Sonuç Durumu',
                   atama_durumu AS 'Atama Durumu',
                   geri_bildirim_durumu AS 'Geri Bildirim'
            FROM hazard_kapanis
        """, conn)

        durum_sira = {"Açık": 0, "İşlemde": 1, "Kapandı": 2}
        renk_map = {"Açık": "#f8d7da", "İşlemde": "#fff3cd", "Kapandı": "#d4edda"}

        durum_df["sira"] = durum_df["Durum"].map(durum_sira)
        durum_df = durum_df.sort_values(by="sira").drop(columns=["sira"])

        def stil_uygula(satir):
            renk = renk_map.get(satir["Durum"], "white")
            return [
                f'background-color: {renk}; color: black; font-weight: 900; font-size: 15px;'
                for _ in satir
            ]

        st.dataframe(durum_df.style.apply(stil_uygula, axis=1), height=400, use_container_width=True)


            
                
                
        st.markdown("### 📤 Gözden Geçirme Hatırlatmaları")

        geri_df = pd.read_sql_query("""
            SELECT report_number, tekrar_gz_tarihi
            FROM hazard_geri_izleme
            WHERE tekrar_gz_tarihi IS NOT NULL AND tekrar_gz_tarihi <> ''
        """, conn)

        if not geri_df.empty:
            geri_df["tekrar_gz_tarihi"] = pd.to_datetime(geri_df["tekrar_gz_tarihi"], errors='coerce')
            geri_df["Gün Farkı"] = (geri_df["tekrar_gz_tarihi"] - datetime.today()).dt.days

            # Durum sütunu oluştur
            geri_df["Durum"] = geri_df["Gün Farkı"].apply(
                lambda x: f"⏳ {x} gün kaldı" if x >= 0 else f"⚠️ {-x} gün gecikti"
            )

            geri_df = geri_df.rename(columns={
                "report_number": "Rapor No",
                "tekrar_gz_tarihi": "Gözden Geçirme Tarihi"
            })

            st.dataframe(geri_df[["Rapor No", "Gözden Geçirme Tarihi", "Durum"]], height=400, use_container_width=True)

        else:
            st.info("🔕 Gözden geçirme tarihi atanmış rapor bulunmuyor.")

        
        st.markdown("### 📈 Raporların Tamamlanma Yüzdesi")

        # Tüm hazard raporlarını çek
        tum_raporlar_df = pd.read_sql_query("SELECT report_number FROM hazard_reports", conn)

        # Tamamlanmış kayıtları al
        progress_df = pd.read_sql_query("SELECT * FROM hazard_progress", conn)
        progress_dict = {row["report_number"]: row["yuzde"] for _, row in progress_df.iterrows()}

        # Listeyi oluştur
        tablo_verisi = []
        for _, row in tum_raporlar_df.iterrows():
            rapor_no = row["report_number"]
            yuzde = progress_dict.get(rapor_no, 0)
            durum = "🚫 Henüz değerlendirme yapılmamış." if yuzde == 0 else "✅ Değerlendirme var"
            tablo_verisi.append({
                "Rapor No": rapor_no,
                "Tamamlanma (%)": yuzde,
                "Durum": durum
            })

        tablo_df = pd.DataFrame(tablo_verisi).sort_values(by="Tamamlanma (%)", ascending=True)

        # Kaydırmalı DataFrame göster
        st.dataframe(tablo_df, height=400, use_container_width=True)


    
      




    with tabs[6]:
        
        import plotly.express as px

        st.markdown("### 🧮 Gelişmiş Risk Verisi Analiz Paneli")

        # 📌 Mevcut sütunlar
        risk_df = pd.read_sql_query("SELECT * FROM hazard_risk", conn)
        mevcut_sutunlar = risk_df.columns.tolist()

        # 🎯 Kullanıcının seçimleri
        secili_sutun = st.selectbox("📊 Analiz Edilecek Sütunu Seçin", mevcut_sutunlar, index=mevcut_sutunlar.index("raporlanan_risk") if "raporlanan_risk" in mevcut_sutunlar else 0)
        grafik_turu = st.selectbox("📈 Grafik Türü Seçin", ["Pie", "Donut", "Bar"])
        renk_paleti = st.selectbox("🎨 Renk Paleti", ["Pastel", "Plotly", "Viridis", "RdBu", "Blues", "Inferno"])

        # 🔍 Sayım ve filtre
        if not risk_df.empty and secili_sutun in risk_df.columns:
            sayim_df = risk_df[secili_sutun].value_counts(dropna=False).reset_index()
            sayim_df.columns = [secili_sutun, "Sayı"]

            # Palet seçimi
            palette_dict = {
                "Pastel": px.colors.qualitative.Pastel,
                "Plotly": px.colors.qualitative.Plotly,
                "Viridis": px.colors.sequential.Viridis,
                "RdBu": px.colors.sequential.RdBu,
                "Blues": px.colors.sequential.Blues,
                "Inferno": px.colors.sequential.Inferno
            }

            secili_palette = palette_dict.get(renk_paleti, px.colors.qualitative.Plotly)

            # 🎨 Grafik çizimi
            if grafik_turu == "Pie":
                fig = px.pie(sayim_df, names=secili_sutun, values="Sayı", color_discrete_sequence=secili_palette)
            elif grafik_turu == "Donut":
                fig = px.pie(sayim_df, names=secili_sutun, values="Sayı", hole=0.4, color_discrete_sequence=secili_palette)
            else:
                fig = px.bar(sayim_df, x=secili_sutun, y="Sayı", color=secili_sutun, color_discrete_sequence=secili_palette)

            fig.update_layout(title=f"📊 {secili_sutun} Dağılımı ({grafik_turu})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 Görüntülenecek veri bulunamadı.")


        

            st.markdown("## 📊 Raporların Durum Analiz Paneli")

            durum_df = pd.read_sql_query("""
                SELECT report_number AS 'Rapor No',
                    durum AS 'Durum',
                    degerlendirme_tarihi AS 'Değerlendirme Tarihi',
                    kapanis_tarihi AS 'Kapanış Tarihi',
                    sonuc_durumu AS 'Sonuç Durumu',
                    atama_durumu AS 'Atama Durumu',
                    geri_bildirim_durumu AS 'Geri Bildirim'
                FROM hazard_kapanis
            """, conn)

        # 🔍 Arama kutusu
        arama = st.text_input("🔍 Rapor No veya Durum ara")

        if arama:
            filtreli_df = durum_df[durum_df.apply(lambda row: arama.lower() in str(row).lower(), axis=1)]
        else:
            filtreli_df = durum_df

        st.dataframe(filtreli_df, use_container_width=True, height=400)

        import io
        import base64
        import plotly.express as px

        st.markdown("### 📥 Excel'e Aktarma ve 📊 Durum Dağılımı Grafiği")
        
        if not durum_df.empty:
            # 🔽 Excel çıktısı hazırla (openpyxl ile uyumlu)
            excel_io = io.BytesIO()
            with pd.ExcelWriter(excel_io, engine="openpyxl") as writer:
                durum_df.to_excel(writer, index=False, sheet_name="Durumlar")
            excel_io.seek(0)

            # 📤 Base64 encode et ve indirme bağlantısı oluştur
            b64 = base64.b64encode(excel_io.read()).decode()
            download_link = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="rapor_durumlari.xlsx" style="font-size:16px;">📁 <b>Excel Olarak İndir</b></a>'
            st.markdown(download_link, unsafe_allow_html=True)

            # 📈 Pie chart oluştur (durum sayısı)
            durum_sayim = durum_df["Durum"].value_counts().reset_index()
            durum_sayim.columns = ["Durum", "Sayı"]

            if not durum_sayim.empty:
                fig = px.pie(durum_sayim,
                            names="Durum",
                            values="Sayı",
                            title="📊 Rapor Durumu Dağılımı",
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textinfo='percent+label', textfont_size=14)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📭 Durum bilgileri grafik için yeterli değil.")
        else:
            st.warning("⚠️ Henüz durum verisi bulunamadı. Excel çıktısı veya grafik oluşturulamadı.")

        
        if st.button("📦 Bu Raporu ZIP Olarak İndir"):
            href = detayli_hazard_rapor_zip_uret_final_genis(secili_rapor_no, conn)
            st.markdown(href, unsafe_allow_html=True)
                



