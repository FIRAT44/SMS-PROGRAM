import streamlit as st

# ————— Sabit kullanıcı bilgileri —————
VALID_USERS = {"admin": "12345", "user1": "sifre1"}

# ————— Session state ile oturum takibi —————
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ————— CSS ile sidebar’ı gizleyen stil —————
HIDE_SIDEBAR_STYLE = """
    <style>
        /* Streamlit üst menü ve footer’ı gizle (isteğe bağlı) */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        /* Sidebar nav (sayfalar) tamamen gizlensin */
        [data-testid="stSidebarNav"] {display: none !important;}
        /* Eğer kendi selectbox’ınızla sayfa seçimi yapıyorsanız onu da gizleyin */
        .css-1lcbmhc {visibility: hidden;}
    </style>
"""

def show_login():
    st.markdown(HIDE_SIDEBAR_STYLE, unsafe_allow_html=True)
    st.title("🔐 Ayjet SMS Programı Giriş")
    st.write("Lütfen kullanıcı adı ve şifrenizi girin.")
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.authenticated = True
            st.rerun()  # Giriş başarılıysa sayfayı yenile
        else:
            st.error("‼️ Geçersiz kullanıcı adı veya şifre.")

# ————— Uygulama akışı —————
if not st.session_state.authenticated:
    show_login()
    st.stop()  # buradan sonrası, login olmadan hiçbir şey çalışmaz

# ————— Giriş yapıldıktan sonra gösterilecek kodlar —————
st.set_page_config(page_title="Ayjet SMS Programı ✈️", layout="wide")
st.title("Ayjet Uçuş Okulu SMS Programı ✈️")
st.sidebar.title("🔍 Menü")
# Örneğin kendi sekme seçiminiz:
page = st.sidebar.selectbox("Sayfa Seçin", ["Anasayfa", "Raporlar", "Denetimler", "Ayarlar"])
if page == "Anasayfa":
    st.write("🏠 Anasayfa içeriği...")
elif page == "Raporlar":
    st.write("📄 Raporlar içeriği...")
# … diğer sayfalar …

