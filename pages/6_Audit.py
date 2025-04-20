import streamlit as st
from utils.auth import login_required
login_required()

st.set_page_config(page_title="SMS Audit", layout="wide")
st.title("📊 SMS Audit")