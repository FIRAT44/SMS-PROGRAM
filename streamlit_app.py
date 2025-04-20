from utils.auth import login_required  # Giriş kontrolü, her şeyden önce gelmeli
login_required()  # Giriş yapılmadıysa sayfa burada durur

# Giriş yapıldıysa aşağıdan sonrası görünür
import streamlit as st
from utils.db_setup import initialize_database

initialize_database()

st.set_page_config(page_title="Ayjet SMS Programı ✈️", layout="wide")

st.title("Ayjet Uçuş Okulu SMS Programı ✈️")
st.markdown("""
Bu uygulama, Emniyet Yönetim Sistemi kapsamındaki raporlar, denetimler ve takip süreçlerini kolaylaştırmak amacıyla geliştirilmiştir.

👈 Soldaki menüden bir sayfa seçerek başlayabilirsiniz.
""")