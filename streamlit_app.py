import streamlit as st

st.set_page_config(page_title="Ayjet SMS Programı ✈️", layout="wide")

from utils.auth import login_required, get_user_role

# Giriş kontrolü
user = login_required()
if not user:
    st.stop()

email = user["email"]
rol = get_user_role(email)
st.session_state["rol"] = rol

st.sidebar.success(f"👋 {email}")



