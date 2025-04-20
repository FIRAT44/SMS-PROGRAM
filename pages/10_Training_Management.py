import streamlit as st
from utils.auth import login_required
login_required()

st.set_page_config(page_title="Training Management", layout="wide")
st.title("📊 Training Management")