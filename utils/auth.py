import streamlit as st
import requests
import json
import os
from firebase_admin import firestore
# 🔴 Firebase Admin SDK init için eklenenler
import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_API_KEY = "AIzaSyBwSH_tKCStmN1PJ3FC7IeUVOnWZb8r2LA"
USER_FILE = ".user_session.json"


# Tek seferlik init
def init_firebase():
    if not firebase_admin._apps:
        # 1) Lokal JSON anahtarıyla:
        cred = credentials.Certificate("service_account.json")
        firebase_admin.initialize_app(cred)
        
        # 🟢 Ya da Streamlit Cloud kullanıyorsan secrets.toml'dan oku:
        # cred_dict = st.secrets["firebase"]
        # cred = credentials.Certificate(cred_dict)
        # firebase_admin.initialize_app(cred)

    return firestore.client()

# db nesnemizi hazırla
db = init_firebase()

def kaydet_user(user_data):
    with open(USER_FILE, "w") as f:
        json.dump(user_data, f)

def yukle_user():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return None

def sil_user():
    if os.path.exists(USER_FILE):
        os.remove(USER_FILE)

def login_required():
    # Oturum dosyasını kontrol et
    if "user" not in st.session_state:
        user_data = yukle_user()
        if user_data:
            st.session_state["user"] = user_data

    # Giriş yapılmışsa göster
    if "user" in st.session_state:
        with st.sidebar.expander("⚙️ Oturum"):
            if st.button("🚪 Çıkış Yap"):
                sil_user()
                del st.session_state["user"]
                st.rerun()
        return st.session_state["user"]

    # Giriş formu
    st.sidebar.header("🔐 Giriş Yap")
    email = st.sidebar.text_input("E-posta", key="email")
    password = st.sidebar.text_input("Şifre", type="password", key="password")

    if st.sidebar.button("Giriş Yap"):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        data = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(url, json=data)

        if response.status_code == 200:
            user_data = response.json()
            st.session_state["user"] = user_data
            kaydet_user(user_data)  # Kalıcı oturum için dosyaya yaz
            st.success("✅ Giriş başarılı!")
            st.rerun()
        else:
            error = response.json().get("error", {}).get("message", "Bilinmeyen hata")
            st.error(f"❌ Giriş başarısız: {error}")

    return None
def require_login():
    if "user" not in st.session_state:
        st.sidebar.error("🔒 Lütfen önce giriş yapın")
        #st.stop()  # buradan itibaren sayfa render edilmez
        login_control()  


def login_control():
    # Giriş kontrolü
    user = login_required()
    if not user:
        st.stop()

    email = user["email"]
    rol = get_user_role(email)
    st.session_state["rol"] = rol

    st.sidebar.success(f"👋 {email}")


def goster_oturum_paneli():
    if "user" in st.session_state:
        email = st.session_state["user"].get("email", "Bilinmiyor")
        #rol = st.session_state.get("rol", "Tanımsız")

        with st.sidebar.expander("⚙️ Oturum", expanded=True):
            st.write(f"👤 **{email}**")
            #st.write(f"🛡️ Rol: `{rol}`")
            if st.button("🚪 Çıkış Yap"):
                sil_user()
                st.session_state.clear()
                st.rerun
    
              
def get_user_role(email):
    try:
        db = firestore.client()
        doc_ref = db.collection("kullanicilar").document(email)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("rol", "ogrenci")  # Varsayılan olarak "ogrenci"
        else:
            return "ogrenci"
    except Exception as e:
        print("Rol getirme hatası:", e)
        return "ogrenci"