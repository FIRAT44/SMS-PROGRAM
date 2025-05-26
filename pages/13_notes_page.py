
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# 📝 Gelişmiş Notlar / OneNote Benzeri
st.set_page_config(page_title="📝 Gelişmiş Notlar", layout="wide")
st.title("📝 Gelişmiş Notlar / OneNote Benzeri")

# Veritabanı bağlantısı
conn = sqlite3.connect("sms_notes.db", check_same_thread=False)
cursor = conn.cursor()

# Notlar tablosu (varsa oluştur)
cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
""")
conn.commit()

# Sidebar: Arama ve filtreler
st.sidebar.header("🔍 Ara ve Filtreler")
search_query = st.sidebar.text_input("Ara (başlık veya içerik)")

# Tüm notları çek
notes_df = pd.read_sql_query("SELECT * FROM notes", conn)

# Tags sütunu yoksa ek olarak boş bir sütun oluştur
def ensure_tags_column(df):
    if 'tags' not in df.columns:
        df['tags'] = ""
    return df
notes_df = ensure_tags_column(notes_df)

# Tags sütununu listeye dönüştür
notes_df['tags_list'] = notes_df['tags'].fillna("").apply(lambda s: [t.strip() for t in s.split(",") if t.strip()])
all_tags = sorted({tag for tags in notes_df['tags_list'] for tag in tags})
selected_tags = st.sidebar.multiselect("Etiket Filtrele", all_tags)

# Sıralama seçenekleri
sort_option = st.sidebar.selectbox("Sırala", [
    "Güncellenme Tarihi (Yeniden) ▼",
    "Güncellenme Tarihi (Eski) ▲",
    "Başlık A-Z",
    "Başlık Z-A"
])

# Filtre uygula
df = notes_df.copy()
if search_query:
    df = df[df.apply(lambda row: search_query.lower() in row['title'].lower() or
                      search_query.lower() in row['content'].lower(), axis=1)]
if selected_tags:
    df = df[df['tags_list'].apply(lambda tags: any(tag in tags for tag in selected_tags))]

# Sıralama uygula
if sort_option == "Güncellenme Tarihi (Yeniden) ▼":
    df = df.sort_values('updated_at', ascending=False)
elif sort_option == "Güncellenme Tarihi (Eski) ▲":
    df = df.sort_values('updated_at', ascending=True)
elif sort_option == "Başlık A-Z":
    df = df.sort_values('title', ascending=True)
else:
    df = df.sort_values('title', ascending=False)

# Not listesi kısmı
with st.sidebar:
    st.header("📂 Notlar")
    note_options = {None: "🆕 Yeni Not"}
    for _, row in df.iterrows():
        note_options[row['id']] = f"{row['title']} ({row['created_at'][:10]})"
    selected_id = st.selectbox("Not Seç", options=list(note_options.keys()), format_func=lambda x: note_options[x])
    if selected_id:
        if st.button("🗑 Sil", key="delete"):
            cursor.execute("DELETE FROM notes WHERE id = ?", (selected_id,))
            conn.commit()
            st.experimental_rerun()

# Ana alan: Not düzenleme / oluşturma
if selected_id:
    rec = cursor.execute("SELECT * FROM notes WHERE id = ?", (selected_id,)).fetchone()
    _, title, content, tags, created_at, updated_at = rec
else:
    title, content, tags, created_at, updated_at = "", "", "", "", ""

st.subheader("✏️ Not Düzenle / Oluştur")
title_input = st.text_input("Başlık", value=title)
content_input = st.text_area("İçerik (Markdown destekli)", value=content, height=300)
tags_input = st.text_input("Etiketler (virgülle ayır)", value=tags if tags else "")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💾 Kaydet Not"):
        now = datetime.utcnow().isoformat()
        if selected_id:
            cursor.execute(
                """
                UPDATE notes SET title=?, content=?, tags=?, updated_at=? WHERE id=?
                """, (title_input, content_input, tags_input, now, selected_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO notes (title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """, (title_input, content_input, tags_input, now, now)
            )
        conn.commit()
        st.success("Not kaydedildi.")
        st.rerun()
with col2:
    if st.button("✏️ Yeni Not"):
        st.rerun()
with col3:
    if st.button("📄 PDF Olarak İndir") and title_input:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.multi_cell(0, 10, title_input)
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 8, content_input)
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        st.download_button(
            "📥 PDF İndir", buffer, file_name=f"{title_input}.pdf", mime="application/pdf"
        )

# Markdown önizleme
st.markdown("---")
st.subheader("🔍 Önizleme")
st.markdown(f"### {title_input}\n" + content_input)

# Alt kısım: Kayıtlı notlar tablosu
st.markdown("---")
st.subheader("📋 Tüm Notların Özeti")
df_summary = df[['id', 'title', 'tags', 'created_at', 'updated_at']].copy()
df_summary.columns = ['ID', 'Başlık', 'Etiketler', 'Oluşturma', 'Güncelleme']
st.dataframe(df_summary.reset_index(drop=True), use_container_width=True)

