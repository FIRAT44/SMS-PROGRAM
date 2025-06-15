import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from streamlit_echarts import st_echarts




# — Yardımcı Fonksiyon —
def parse_date(val):
    try:
        return date.fromisoformat(val)
    except:
        return date.today()

# — Ortak Listeler —
REASONS    = ["Operasyonel Değişiklik", "Yeni Sistem", "Personel Değişikliği", "Yasal Değişiklik", "Diğer"]
STATUSES   = ["To Do", "In Progress", "Review", "Done", "Blocked"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

# — Veritabanı Bağlantısı & Migrate —
conn = sqlite3.connect("sms_database3.db", check_same_thread=False)
cursor = conn.cursor()

# 1) Değişiklik Talepleri
cursor.execute('''
CREATE TABLE IF NOT EXISTS dtf_kayitlari (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  degisiklik_basligi TEXT,
  talep_eden         TEXT,
  degisiklik_sebebi  TEXT,
  kapsam             TEXT,
  amac               TEXT,
  planlanan_surec    TEXT,
  etkilenen_sistemler TEXT,
  etkilenen_islevler TEXT,
  gerekli_dokumanlar TEXT,
  baslama_tarihi     TEXT,
  bitis_tarihi       TEXT,
  form_tarihi        TEXT,
  moc_sorumlusu      TEXT
)
''')

# 2) Risk Değerlendirmeleri
cursor.execute('''
CREATE TABLE IF NOT EXISTS dtf_riskler (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dtf_id INTEGER,
  olasi_risk TEXT,
  risk_azaltma_tedbirleri TEXT,
  FOREIGN KEY(dtf_id) REFERENCES dtf_kayitlari(id)
)
''')

# 3) Proje Takvimi
cursor.execute('''
CREATE TABLE IF NOT EXISTS proje_takvimi (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dtf_id INTEGER,
  step TEXT,
  faaliyet TEXT,
  planlanan_tarih TEXT,
  revize_tarih TEXT,
  aciklama TEXT,
  sorumlu_kisi TEXT,
  sorumlu_birim TEXT,
  kontrol_adimlari TEXT,
  status TEXT DEFAULT 'To Do',
  priority TEXT DEFAULT 'Medium',
  FOREIGN KEY(dtf_id) REFERENCES dtf_kayitlari(id)
)
''')

# migrate eksik kolonlar
cols = [r[1] for r in cursor.execute("PRAGMA table_info(proje_takvimi)").fetchall()]
if "status"   not in cols:
    cursor.execute("ALTER TABLE proje_takvimi ADD COLUMN status TEXT DEFAULT 'To Do'")
if "priority" not in cols:
    cursor.execute("ALTER TABLE proje_takvimi ADD COLUMN priority TEXT DEFAULT 'Medium'")
conn.commit()

# — Streamlit Konfigürasyonu —
st.set_page_config(page_title="📝 DTF & Proje Yönetimi", layout="wide")
st.title("📝 Değişiklik Talebi ve Proje Yönetimi")

tabs = st.tabs([
    "📌 Değişiklik Talebi",
    "⚠️ Risk Değerlendirmesi",
    "🗓️ Proje Takvimi",
    "📊 Görünümler"
])

# --- Tab 1: Değişiklik Talebi ---
with tabs[0]:
    mode = st.radio("İşlem seçin:", ["Yeni Talep","Güncelle/Sil"], horizontal=True, key="mode1")
    if mode == "Yeni Talep":
        with st.form("form1"):
            title     = st.text_input("Başlık (*)", key="f1_title")
            requester = st.text_input("Talep Eden (*)", key="f1_requester")
            reason    = st.selectbox("Sebep", options=REASONS, key="f1_reason")
            scope     = st.text_area("Kapsam", key="f1_scope")
            purpose   = st.text_area("Amaç", key="f1_purpose")
            process   = st.text_area("Planlanan Süreç", key="f1_process")
            systems   = st.text_area("Etkilenen Sistemler", key="f1_systems")
            functions = st.text_area("Etkilenen İşlevler", key="f1_functions")
            docs      = st.text_area("Gerekli Dökümanlar", key="f1_docs")
            c1, c2    = st.columns(2)
            with c1:
                start_date = st.date_input("Başlama Tarihi", key="f1_start")
            with c2:
                end_date   = st.date_input("Bitiş Tarihi", key="f1_end")
            st.markdown("---")
            form_date = st.date_input("Form Tarihi", value=date.today(), key="f1_formdate")
            moc_owner = st.text_input("MOC Sorumlusu", key="f1_moc")
            submit1   = st.form_submit_button("💾 Kaydet")
        if submit1 and title and requester:
            cursor.execute('''
                INSERT INTO dtf_kayitlari (
                  degisiklik_basligi, talep_eden, degisiklik_sebebi,
                  kapsam, amac, planlanan_surec, etkilenen_sistemler,
                  etkilenen_islevler, gerekli_dokumanlar,
                  baslama_tarihi, bitis_tarihi, form_tarihi, moc_sorumlusu
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                title, requester, reason,
                scope, purpose, process, systems,
                functions, docs,
                start_date.isoformat(), end_date.isoformat(),
                form_date.isoformat(), moc_owner
            ))
            conn.commit()
            st.success("✅ Talep kaydedildi")
    else:
        recs = cursor.execute("SELECT id,degisiklik_basligi FROM dtf_kayitlari").fetchall()
        sel  = st.selectbox("Güncellenecek Talep:", options=recs, format_func=lambda x:x[1], key="f1_select")
        if sel:
            rid = sel[0]
            rec = cursor.execute("SELECT * FROM dtf_kayitlari WHERE id=?", (rid,)).fetchone()
            with st.form("form1u"):
                u1 = st.text_input("Başlık", value=rec[1], key="u1")
                u2 = st.text_input("Talep Eden", value=rec[2], key="u2")
                u3 = st.selectbox("Sebep", options=REASONS, index=REASONS.index(rec[3]), key="u3")
                u4 = st.text_area("Kapsam", value=rec[4], key="u4")
                u5 = st.text_area("Amaç", value=rec[5], key="u5")
                u6 = st.text_area("Süreç", value=rec[6], key="u6")
                u7 = st.text_area("Sistemler", value=rec[7], key="u7")
                u8 = st.text_area("İşlevler", value=rec[8], key="u8")
                u9 = st.text_area("Dokümanlar", value=rec[9], key="u9")
                c1,c2 = st.columns(2)
                with c1:
                    ud1 = st.date_input("Başlama", value=parse_date(rec[10]), key="ud1")
                with c2:
                    ud2 = st.date_input("Bitiş", value=parse_date(rec[11]), key="ud2")
                st.markdown("---")
                ud3 = st.date_input("Form Tarihi", value=parse_date(rec[12]), key="ud3")
                u10 = st.text_input("MOC Sorumlusu", value=rec[13], key="u10")
                subu= st.form_submit_button("💾 Güncelle")
            if subu:
                cursor.execute('''
                    UPDATE dtf_kayitlari SET
                      degisiklik_basligi=?, talep_eden=?, degisiklik_sebebi=?,
                      kapsam=?, amac=?, planlanan_surec=?, etkilenen_sistemler=?,
                      etkilenen_islevler=?, gerekli_dokumanlar=?,
                      baslama_tarihi=?, bitis_tarihi=?, form_tarihi=?, moc_sorumlusu=?
                    WHERE id=?
                ''', (
                    u1,u2,u3,u4,u5,u6,u7,u8,u9,
                    ud1.isoformat(), ud2.isoformat(), ud3.isoformat(), u10,
                    rid
                ))
                conn.commit()
                st.success("✅ Talep güncellendi")
            if st.button("❌ Sil", key="f1_del"):
                cursor.execute("DELETE FROM dtf_kayitlari WHERE id=?", (rid,))
                conn.commit()
                st.success("✅ Silindi")

    st.markdown("### 📋 Mevcut Talepler")
    df1 = pd.read_sql("SELECT * FROM dtf_kayitlari ORDER BY id DESC", conn)
    st.dataframe(df1, use_container_width=True)

# --- Tab 2: Risk Değerlendirmesi ---
with tabs[1]:
    st.subheader("⚠️ Risk Değerlendirmesi")
    recs2 = cursor.execute("SELECT id,degisiklik_basligi FROM dtf_kayitlari").fetchall()
    if recs2:
        sel2 = st.selectbox("Talep Seç", options=recs2, format_func=lambda x:x[1], key="f2_select")
        with st.form("form2"):
            r1 = st.text_area("Olası Riskler", key="r1")
            r2 = st.text_area("Risk Azaltma Tedbirleri", key="r2")
            sub2 = st.form_submit_button("💾 Kaydet")
        if sub2:
            cursor.execute('INSERT INTO dtf_riskler VALUES(NULL,?,?,?)', (sel2[0], r1, r2))
            conn.commit()
            st.success("✅ Risk kaydedildi")
    else:
        st.info("Önce talep ekleyin")
    st.markdown("### 📋 Mevcut Riskler")
    df2 = pd.read_sql('''
        SELECT r.id, k.degisiklik_basligi AS baslik,
               r.olasi_risk, r.risk_azaltma_tedbirleri
        FROM dtf_riskler r JOIN dtf_kayitlari k ON r.dtf_id=k.id
        ORDER BY r.id DESC
    ''', conn)
    st.dataframe(df2, use_container_width=True)

# --- Tab 3: Proje Takvimi ---
with tabs[2]:
    st.subheader("🗓️ Proje Takvimi")
    recs3 = cursor.execute("SELECT id,degisiklik_basligi FROM dtf_kayitlari").fetchall()
    sel3 = st.selectbox("Talep Seç", options=recs3, format_func=lambda x:x[1], key="f3_select")
    if sel3:
        pid = sel3[0]
        with st.form("form3"):
            s1 = st.text_input("Step (Adım Adı)", key="s1")
            s2 = st.text_input("Faaliyet", key="s2")
            s3 = st.date_input("Planlanan Tarih", value=date.today(), key="s3")
            s4 = st.date_input("Revize Tarih", value=s3, key="s4")
            s5 = st.text_area("Açıklama", key="s5")
            s6 = st.text_input("Sorumlu Kişi", key="s6")
            s7 = st.text_input("Sorumlu Birim", key="s7")
            s8 = st.text_area("Kontrol Adımları", key="s8")
            s9 = st.selectbox("Status", options=STATUSES, key="s9")
            s10= st.selectbox("Priority", options=PRIORITIES, key="s10")
            sub3 = st.form_submit_button("💾 Ekle")
        if sub3:
            cursor.execute('''
                INSERT INTO proje_takvimi VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                pid, s1, s2,
                s3.isoformat(), s4.isoformat(), s5,
                s6, s7, s8, s9, s10
            ))
            conn.commit()
            st.success("✅ Adım eklendi")
        df3 = pd.read_sql(f"SELECT * FROM proje_takvimi WHERE dtf_id={pid} ORDER BY id", conn)
        st.markdown("### 📋 Tüm Adımlar")
        st.dataframe(df3, use_container_width=True)

# --- Tab 4: Görünümler ---
with tabs[3]:
    st.subheader("📊 Kanban & Gantt Görünümleri")
    recs4 = cursor.execute(
        "SELECT id, degisiklik_basligi FROM dtf_kayitlari"
    ).fetchall()
    sel4 = st.selectbox(
        "Talep Seç",
        options=recs4,
        format_func=lambda x: x[1],
        key="f4_select"
    )

    if sel4:
        did = sel4[0]
        df4 = pd.read_sql_query(
            f"SELECT * FROM proje_takvimi WHERE dtf_id={did} ORDER BY id", conn
        )

        if df4.empty:
            st.info("▶️ Bu talebe ait proje takvimi boş.")
        else:
            # — Kanban Tahtası (AgGrid) —
            st.markdown("### 📋 Kanban Tahtası")
            gb = GridOptionsBuilder.from_dataframe(df4)
            gb.configure_column("status", cellStyle={
                "function": """
                if (params.value=='To Do')       return {'backgroundColor':'#FFCCCC'};
                if (params.value=='In Progress') return {'backgroundColor':'#FFE599'};
                if (params.value=='Review')      return {'backgroundColor':'#9FC5E8'};
                if (params.value=='Done')        return {'backgroundColor':'#A2D39C'};
                return {'backgroundColor':'#E0E0E0'};
                """
            })
            gb.configure_column("priority", cellStyle={
                "function": """
                if (params.value=='Critical') return {'backgroundColor':'#B30000','color':'white'};
                if (params.value=='High')     return {'backgroundColor':'#E69138'};
                if (params.value=='Medium')   return {'backgroundColor':'#F9CB9C'};
                return {'backgroundColor':'#D9D9D9'};
                """
            })
            gb.configure_grid_options(domLayout='autoHeight')
            gb.configure_selection('single', use_checkbox=True)
            AgGrid(
                df4,
                gridOptions=gb.build(),
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode=GridUpdateMode.VALUE_CHANGED,
                fit_columns_on_grid_load=True
            )

            # — ECharts Gantt Çizelgesi —
            st.markdown("### 📅 ECharts Gantt Çizelgesi")
            categories = df4["step"].tolist()
            palette = px.colors.qualitative.Vivid
            tasks = [
                {
                    "name": row.step,
                    "value": [row.planlanan_tarih, row.revize_tarih, idx],
                    "itemStyle": {
                        "color": palette[idx % len(palette)],
                        "borderColor": "#333",
                        "borderWidth": 1
                    }
                }
                for idx, row in df4.iterrows()
            ]
            option = {
                "title": {"text": "Gantt Çizelgesi", "left": "center"},
                "tooltip": {
                    "trigger": "axis",
                    "formatter": """
                        function(params){
                          const v = params[0].value;
                          return `<b>${params[0].seriesName}</b><br/>
                                  Başlangıç: ${v[0]}<br/>Bitiş: ${v[1]}`;
                        }
                    """
                },
                "xAxis": {"type": "time", "axisLabel": {"formatter": "{yyyy}-{MM}-{dd}"}},
                "yAxis": {"type": "category", "data": categories, "inverse": True},
                "dataZoom": [{"type": "slider"}, {"type": "inside"}],
                "series": [{
                    "name": "Görevler",
                    "type": "custom",
                    "renderItem": """
                        function(params, api){
                          const i = api.value(2);
                          const s = api.coord([api.value(0), i]);
                          const e = api.coord([api.value(1), i]);
                          const h = api.size([0,1])[1] * 0.6;
                          return {
                            type: 'rect',
                            shape: { x: s[0], y: s[1]-h/2, width: e[0]-s[0], height: h },
                            style: api.style()
                          };
                        }
                    """,
                    "dimensions": ["start","end","stepIndex"],
                    "encode": {"x":[0,1],"y":2},
                    "data": tasks
                }]
            }
            st_echarts(option, height="500px")

            # — Plotly FigureFactory Gantt Çizelgesi —
            import plotly.figure_factory as ff

            st.markdown("### 📅 Plotly FigureFactory Gantt Çizelgesi")
            records = [
                dict(
                    Task=row.step,
                    Start=row.planlanan_tarih,
                    Finish=row.revize_tarih,
                    Resource=row.status
                )
                for _, row in df4.iterrows()
            ]
            colors = {
                "To Do": "#FF4C4C",
                "In Progress": "#FFA500",
                "Review": "#00BFFF",
                "Done": "#32CD32",
                "Blocked": "#8B0000"
            }
            fig_ff = ff.create_gantt(
                records,
                colors=colors,
                index_col='Resource',
                show_colorbar=True,
                group_tasks=True,
                title="Proje Zaman Çizelgesi"
            )
            fig_ff.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_ff, use_container_width=True)
    else:
        st.info("▶️ Önce bir talep seçin.")

