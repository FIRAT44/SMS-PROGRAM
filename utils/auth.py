import streamlit as st

def login_required():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.set_page_config(page_title="🔐 Giriş Yap", layout="centered")
        st.title("🔐 Ayjet SMS Giriş Ekranı")

        with st.form("login_form"):
            username = st.text_input("👤 Kullanıcı Adı")
            password = st.text_input("🔒 Şifre", type="password")
            submit = st.form_submit_button("Giriş")

            if submit:
                if username == "admin" and password == "1234":
                    st.session_state["authenticated"] = True
                    st.success("✅ Giriş başarılı.")
                    st.rerun()
                else:
                    st.error("❌ Hatalı kullanıcı adı veya şifre.")
        st.stop()