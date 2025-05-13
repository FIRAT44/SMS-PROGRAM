import streamlit as st

if st.session_state.get("rol") != "admin":
    st.warning("🚫 Bu sayfaya erişiminiz yok.")
    st.stop()

st.title("🧑‍🎓 Öğrenci Paneli")
st.write("Kendi raporlarını görebileceğin ve yeni rapor ekleyebileceğin alan.")



# def plot_screen():
    
#     from pyvis.network import Network
#     import streamlit.components.v1 as components
#     import tempfile
#     import os
#     import base64

#     st.markdown("---")
#     st.subheader("🌳 Rapor Akış Görseli (Dinamik, Renkli, Açıklamalı)")

#     # Tablo kontrolü (önlem tablosu varsa oluştur)
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         report_number TEXT,
#         risk_id INTEGER,
#         onlem_aciklama TEXT,
#         sorumlu TEXT,
#         termin TEXT,
#         gerceklesen TEXT,
#         revize_risk TEXT,
#         etkinlik_kontrol TEXT,
#         etkinlik_sonrasi TEXT
#     )
#     """)
#     conn.commit()

#     # Veriler
#     riskler = pd.read_sql_query("""
#         SELECT id, tehlike_tanimi, mevcut_onlemler, raporlanan_risk 
#         FROM hazard_risk 
#         WHERE report_number = ?
#     """, conn, params=(rapor_no,))

#     onlemler = pd.read_sql_query("""
#         SELECT risk_id, onlem_aciklama, sorumlu, termin, etkinlik_kontrol 
#         FROM hazard_onlem_coklu 
#         WHERE report_number = ?
#     """, conn, params=(rapor_no,))

#     # Pyvis ağı
#     net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#000000", directed=True)
#     # Hierarchical düzeni için ayar
#     net.set_options("""
#     {
#     "layout": {
#         "hierarchical": {
#         "enabled": true,
#         "levelSeparation": 400,
#         "nodeSpacing": 500,
#         "direction": "UD",
#         "sortMethod": "directed"
#         }
#     },
#     "nodes": {
#         "shape": "box",
#         "font": {
#         "size": 20,
#         "face": "Arial",
#         "bold": true
#         }
#     },
#     "edges": {
#         "arrows": {
#         "to": { "enabled": true }
#         },
#         "smooth": {
#         "type": "cubicBezier",
#         "roundness": 0.4
#         }
#     },
#     "physics": {
#         "enabled": false
#     }
#     }
#     """)


#     net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#000000", directed=True)

#     # Temel düğümler
#     net.add_node("rapor", label="📄 Rapor", color="#b3d9ff", title="Hazard rapor kök noktası", level=0)
#     net.add_node("geribildirim", label="📤 Geri Bildirim", color="#d0c2f2", title="Originator'a Geri Bildirim ve Komite Yorumu", level=2)
#     net.add_node("kapanis", label="✅ Kapanış", color="#e6ffe6", title="Risk değerlendirme tamamlanma noktası", level=3)

#     # Risk renk/font haritaları
#     renk_map = {
#         "Low": "#fffac8",
#         "Medium": "#ffe599",
#         "High": "#ffb347",
#         "Extreme": "#ff6961"
#     }

#     font_map = {
#         "Low": 18,
#         "Medium": 20,
#         "High": 22,
#         "Extreme": 24
#     }

#     # Önlem etkinlik stil haritası
#     etkinlik_map = {
#         "Etkili": {"color": "#a1e3a1", "size": 18},
#         "Kısmen Etkili": {"color": "#fff1b5", "size": 20},
#         "Etkisiz": {"color": "#ff9999", "size": 22}
#     }

#     # Rapor > Risk > Önlem > Geri Bildirim > Kapanış
#     for _, risk in riskler.iterrows():
#         risk_id = f"risk_{risk['id']}"
#         risk_seviye = (risk["raporlanan_risk"] or "Low").strip()

#         net.add_node(
#             risk_id,
#             label=f"⚠️ {risk['tehlike_tanimi'][:30]}",
#             color=renk_map.get(risk_seviye, "#ffe599"),
#             title=f"{risk['tehlike_tanimi']} {risk_seviye} {risk['mevcut_onlemler'] or '-'}",
#             font={"size": font_map.get(risk_seviye, 20)}
#         )
#         net.add_edge("rapor", risk_id, label="Risk", width=1.5 if risk_seviye in ["High", "Extreme"] else 0.7)

#         ilgili_onlemler = onlemler[onlemler["risk_id"] == risk["id"]]
#         for j, onlem in ilgili_onlemler.iterrows():
#             onlem_id = f"onlem_{risk['id']}_{j}"
#             etkinlik = onlem.get("etkinlik_kontrol", "Kısmen Etkili")
#             stil = etkinlik_map.get(etkinlik, {"color": "#c2f0c2", "size": 18})

#             net.add_node(
#                 onlem_id,
#                 label=f"🧰 {onlem['onlem_aciklama'][:30]}" if onlem["onlem_aciklama"] else "🧰 Önlem",
#                 color=stil["color"],
#                 title=f"<b>Önlem:</b> {onlem['onlem_aciklama']}<br><b>Sorumlu:</b> {onlem['sorumlu']}<br><b>Termin:</b> {onlem['termin']}<br><b>Etkinlik:</b> {etkinlik}",
#                 font={"size": stil["size"]}
#             )
#             net.add_edge(risk_id, onlem_id, label="Önlem", width=0.5)
#             net.add_edge(onlem_id, "geribildirim", label="Geri Bildirim", width=0.7)

#     # Geri Bildirim → Kapanış
#     net.add_edge("geribildirim", "kapanis", label="Tamamlandı", width=1.0)

#     # HTML dosyasına yaz
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
#         net.save_graph(tmp_file.name)
#         html_path = tmp_file.name

#     # Gömülü görünüm
#     components.html(open(html_path, 'r', encoding='utf-8').read(), height=720)

#     # 🌐 Yeni sekmede açma
#     st.markdown("### 🌐 Diyagramı Yeni Sekmede Aç")
#     with open(html_path, "r", encoding="utf-8") as f:
#         html_content = f.read()
#         b64 = base64.b64encode(html_content.encode("utf-8")).decode()
#         href = f'<a href="data:text/html;base64,{b64}" download="rapor_akis.html" target="_blank">🖥️ Yeni Sekmede Aç (Tam Ekran)</a>'
#         st.markdown(href, unsafe_allow_html=True)
