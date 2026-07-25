import os
# --- INSTALACIÓN DE NAVEGADOR PARA LA NUBE ---
os.system("playwright install chromium")
# ---------------------------------------------

import streamlit as st
import json
import re
import ast
import base64
import time
import requests
import pandas as pd
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image
from openai import OpenAI
from duckduckgo_search import DDGS

# === 🎨 CONFIGURACIÓN DE ESTILOS Y COLORES VELOVE ===
COLOR_FONDO = "#e4d2c2"
COLOR_TEXTO = "#001c19"
COLOR_BOTON = "#ff1d4e"
COLOR_BOTON_HOVER = "#e01742"
# ===================================================

st.set_page_config(page_title="Velove | Local Benchmark to Miro", page_icon="📍", layout="wide")

st.markdown(f"""
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap](https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap)');
    html, body, [class*="css"], .stApp {{ font-family: 'Work Sans', sans-serif !important; background-color: {COLOR_FONDO} !important; color: {COLOR_TEXTO} !important; }}
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {{ background-color: #ffffff !important; color: {COLOR_TEXTO} !important; border-radius: 8px !important; border: 1px solid {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    div.stButton > button:first-child {{ background-color: {COLOR_BOTON} !important; color: #ffffff !important; border-radius: 8px !important; border: none !important; font-weight: 600 !important; font-family: 'Work Sans', sans-serif !important; padding: 12px 24px !important; transition: all 0.3s ease !important; }}
    div.stButton > button:first-child:hover {{ background-color: {COLOR_BOTON_HOVER} !important; color: #ffffff !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label {{ color: {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_BOTON} !important; }}
    </style>
""", unsafe_allow_html=True)

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
    MIRO_ACCESS_TOKEN = st.secrets.get("MIRO_ACCESS_TOKEN", "")
except Exception:
    st.error("Falta la credencial de OpenRouter en .streamlit/secrets.toml")
    st.stop()

client = OpenAI(base_url="[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)", api_key=OPENROUTER_API_KEY)

def parsear_json_llm(texto):
    if not texto: return []
    # Limpieza segura de bloques markdown usando regex
    texto_clean = re.sub(r'[`]{3}json\s*', '', texto)
    texto_clean = re.sub(r'[`]{3}\s*', '', texto_clean)
    match = re.search(r'\[.*\]', texto_clean, re.DOTALL)
    if not match: return []
    raw_json = match.group(0)
    raw_json_clean = re.sub(r',\s*([\]}])', r'\1', raw_json)
    try: return json.loads(raw_json_clean)
    except Exception: pass
    try
