import streamlit as st
import pandas as pd
import numpy as np
import math
import os
import requests
import joblib
from datetime import datetime
from scipy.stats import entropy as scipy_entropy
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import xml.etree.ElementTree as ET
import urllib.parse
import re
import warnings
import time
import xgboost as xgb

warnings.filterwarnings('ignore')

# --- SETUP PAGINA E STATO GLOBALE ---
if 'app_init' not in st.session_state:
    st.set_page_config(page_title="Sniper Quant Terminal v30", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
    st.session_state.app_init = True
    st.session_state.live_matches = []
    st.session_state.df_top5 = pd.DataFrame()
    st.session_state.df_ai_future = pd.DataFrame()
    st.session_state.df_gen271 = pd.DataFrame() # SOSTITUISCE L'IBRIDO
    st.session_state.schedine_gen271 = {}
    st.session_state.df_scraped_leagues = pd.DataFrame() 
    st.session_state.dati_precalcolati = False
    
    st.session_state.data_limite = pd.Timestamp.today().normalize() - pd.DateOffset(years=2, months=8)
    st.session_state.data_limite = st.session_state.data_limite.replace(tzinfo=None)
    st.session_state.anno_limite = st.session_state.data_limite.year

# ==============================================================================
# CSS PULITO E MINIMALE
# ==============================================================================
def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── DESIGN TOKENS ───────────────────────────────────── */
    :root {
        --bg-base:       #07090F;
        --bg-surface:    #0C1018;
        --bg-card:       #111827;
        --bg-card-hover: #161F30;
        --border:        rgba(255,255,255,0.06);
        --border-active: rgba(99,179,237,0.35);
        --text-primary:  #EEF2FF;
        --text-secondary:#8B9CB8;
        --text-muted:    #3D4F66;
        --accent-blue:   #5BA3F5;
        --accent-green:  #4ADE80;
        --accent-red:    #F87171;
        --accent-gold:   #FBBF24;
        --accent-purple: #A78BFA;
        --accent-cyan:   #22D3EE;
        --font-sans:     'Inter', system-ui, sans-serif;
        --font-mono:     'JetBrains Mono', 'Fira Code', monospace;
        --radius-xs:     4px;
        --radius-sm:     8px;
        --radius-md:     12px;
        --radius-lg:     18px;
        --radius-xl:     24px;
        --shadow-card:   0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
        --shadow-glow-b: 0 0 24px rgba(91,163,245,0.12);
        --shadow-glow-g: 0 0 24px rgba(74,222,128,0.12);
    }

    /* ── RESET & BASE ────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: var(--font-sans) !important;
        background: var(--bg-base) !important;
        color: var(--text-primary) !important;
    }
    .main .block-container {
        padding: 1.75rem 2rem 4rem !important;
        max-width: 1440px !important;
        margin: 0 auto !important;
    }

    /* ── SIDEBAR ─────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090D18 0%, #0C1018 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1rem 2rem !important; }
    [data-testid="stSidebar"] h2 {
        font-size: 10px !important; font-weight: 700 !important;
        letter-spacing: 2.5px !important; text-transform: uppercase !important;
        color: var(--text-muted) !important; margin-bottom: 12px !important;
        padding-bottom: 10px !important;
        border-bottom: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] .stCaption {
        font-size: 10px !important; line-height: 1.6 !important;
        color: var(--text-muted) !important;
        font-family: var(--font-mono) !important;
    }

    /* ── SIDEBAR RADIO ───────────────────────────────────── */
    [data-testid="stRadio"] > label { display: none !important; }
    [data-testid="stRadio"] div[role="radiogroup"] { gap: 1px !important; }
    [data-testid="stRadio"] label {
        background: transparent !important; border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 7px 10px 7px 8px !important;
        font-size: 12.5px !important; font-weight: 500 !important;
        color: var(--text-secondary) !important;
        cursor: pointer !important; width: 100% !important;
        transition: background 0.15s, color 0.15s !important;
        display: flex !important; align-items: center !important;
    }
    [data-testid="stRadio"] label:hover {
        background: rgba(91,163,245,0.07) !important;
        color: var(--accent-blue) !important;
    }

    /* ── TITLES ──────────────────────────────────────────── */
    h1 {
        font-size: 20px !important; font-weight: 800 !important;
        color: var(--text-primary) !important; letter-spacing: -0.3px !important;
        padding-bottom: 14px !important; margin-bottom: 20px !important;
        border-bottom: 1px solid var(--border) !important;
        line-height: 1.3 !important;
    }
    h2 { font-size: 16px !important; font-weight: 700 !important; color: var(--text-primary) !important; }
    h3 { font-size: 13px !important; font-weight: 600 !important; color: var(--text-secondary) !important; letter-spacing: 0.2px !important; }
    h4 { font-size: 12px !important; font-weight: 600 !important; color: var(--text-muted) !important; text-transform: uppercase !important; letter-spacing: 1.2px !important; }
    p, li { font-size: 13.5px !important; line-height: 1.65 !important; color: var(--text-secondary) !important; }

    /* ── METRIC CARDS ────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 18px !important;
        box-shadow: var(--shadow-card) !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    [data-testid="metric-container"]:hover {
        border-color: var(--border-active) !important;
        box-shadow: var(--shadow-glow-b) !important;
    }
    [data-testid="metric-container"] label {
        font-size: 10px !important; font-weight: 600 !important;
        letter-spacing: 1.5px !important; text-transform: uppercase !important;
        color: var(--text-muted) !important;
        font-family: var(--font-mono) !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 22px !important; font-weight: 700 !important;
        font-family: var(--font-mono) !important;
        color: var(--text-primary) !important; letter-spacing: -0.5px !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 11px !important; font-family: var(--font-mono) !important;
    }

    /* ── DATAFRAME ───────────────────────────────────────── */
    [data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden !important;
    }
    iframe { border-radius: var(--radius-md) !important; background: var(--bg-card) !important; }

    /* ── BUTTONS ─────────────────────────────────────────── */
    button[kind="secondary"], [data-testid="stButton"] > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        font-family: var(--font-sans) !important;
        font-size: 13px !important; font-weight: 600 !important;
        letter-spacing: 0.2px !important;
        padding: 9px 20px !important;
        transition: all 0.18s ease !important;
        box-shadow: none !important;
    }
    [data-testid="stButton"] > button:hover {
        background: var(--bg-card-hover) !important;
        border-color: var(--accent-blue) !important;
        box-shadow: var(--shadow-glow-b) !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="stButton"] > button:active { transform: translateY(0) !important; }

    /* ── INPUTS ──────────────────────────────────────────── */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background: var(--bg-surface) !important;
        border-color: var(--border) !important;
        border-radius: var(--radius-sm) !important;
    }
    div[data-baseweb="input"] input, [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input {
        font-family: var(--font-mono) !important;
        font-size: 13px !important;
        color: var(--text-primary) !important;
        background: transparent !important;
    }
    div[data-baseweb="select"] > div {
        background: var(--bg-surface) !important;
        border-color: var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
    }

    /* ── PROGRESS ────────────────────────────────────────── */
    [data-testid="stProgress"] > div {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 4px !important; height: 4px !important;
    }
    [data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, var(--accent-blue) 0%, var(--accent-purple) 100%) !important;
        border-radius: 4px !important;
    }

    /* ── ALERTS ──────────────────────────────────────────── */
    [data-testid="stAlert"] {
        border-radius: var(--radius-md) !important;
        border-left-width: 3px !important;
        font-size: 13px !important;
        font-family: var(--font-mono) !important;
        padding: 12px 16px !important;
    }
    [data-testid="stAlert"][data-baseweb="notification"] {
        background: rgba(91,163,245,0.05) !important;
        border-color: rgba(91,163,245,0.25) !important;
    }

    /* ── SLIDER ──────────────────────────────────────────── */
    [data-testid="stSlider"] > div > div > div > div {
        background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)) !important;
    }

    /* ── CHECKBOX ────────────────────────────────────────── */
    [data-testid="stCheckbox"] label { font-size: 13px !important; color: var(--text-secondary) !important; }

    /* ── DIVIDER ───────────────────────────────────────── */
    hr, [data-testid="stDivider"] > hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 18px 0 !important;
    }

    /* ── CAPTION / SMALL ─────────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-family: var(--font-mono) !important;
        letter-spacing: 0.2px !important;
    }

    /* ── SPINNER ─────────────────────────────────────────── */
    [data-testid="stSpinner"] p { color: var(--accent-blue) !important; }

    /* ── CUSTOM QUANT BOXES ──────────────────────────────── */
    .quant-box-green {
        background: linear-gradient(135deg, rgba(74,222,128,0.07) 0%, rgba(74,222,128,0.02) 100%);
        border: 1px solid rgba(74,222,128,0.18);
        border-left: 3px solid var(--accent-green);
        padding: 14px 18px; border-radius: var(--radius-md);
        font-family: var(--font-mono); font-size: 12.5px;
        margin-bottom: 10px; color: var(--text-primary);
        box-shadow: 0 0 20px rgba(74,222,128,0.04);
    }
    .quant-box-green b { color: var(--accent-green); font-weight: 700; }

    .quant-box-red {
        background: linear-gradient(135deg, rgba(248,113,113,0.07) 0%, rgba(248,113,113,0.02) 100%);
        border: 1px solid rgba(248,113,113,0.18);
        border-left: 3px solid var(--accent-red);
        padding: 14px 18px; border-radius: var(--radius-md);
        font-family: var(--font-mono); font-size: 12.5px;
        margin-bottom: 10px; color: var(--text-primary);
    }
    .quant-box-red b { color: var(--accent-red); font-weight: 700; }

    .quant-box-blue {
        background: linear-gradient(135deg, rgba(91,163,245,0.07) 0%, rgba(91,163,245,0.02) 100%);
        border: 1px solid rgba(91,163,245,0.18);
        border-left: 3px solid var(--accent-blue);
        padding: 14px 18px; border-radius: var(--radius-md);
        font-family: var(--font-mono); font-size: 12.5px;
        margin-bottom: 10px; color: var(--text-primary);
    }
    .quant-box-blue b { color: var(--accent-blue); font-weight: 700; }

    /* ── LIVE DOT BADGE ──────────────────────────────────── */
    .live-dot {
        display: inline-block; width: 7px; height: 7px;
        background: var(--accent-green); border-radius: 50%;
        box-shadow: 0 0 8px var(--accent-green);
        animation: blink 2s ease-in-out infinite;
        margin-right: 6px; vertical-align: middle;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} }

    /* ── STATUS PILL ─────────────────────────────────────── */
    .pill {
        display:inline-flex; align-items:center; gap:5px;
        padding: 3px 10px; border-radius: 20px;
        font-size: 10px; font-weight: 700; font-family: var(--font-mono);
        letter-spacing: 0.8px; text-transform: uppercase;
    }
    .pill-green { background: rgba(74,222,128,0.1); color: var(--accent-green); border: 1px solid rgba(74,222,128,0.2); }
    .pill-red   { background: rgba(248,113,113,0.1); color: var(--accent-red);   border: 1px solid rgba(248,113,113,0.2); }
    .pill-blue  { background: rgba(91,163,245,0.1);  color: var(--accent-blue);  border: 1px solid rgba(91,163,245,0.2); }
    .pill-gold  { background: rgba(251,191,36,0.1);  color: var(--accent-gold);  border: 1px solid rgba(251,191,36,0.2); }

    /* ── SCROLLBAR ───────────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }

    /* ── SELECTBOX DROPDOWN ──────────────────────────────── */
    ul[data-testid="stSelectboxVirtualDropdown"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
    }
    li[role="option"]:hover {
        background: rgba(91,163,245,0.08) !important;
        color: var(--accent-blue) !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

FILE_UNDERSTAT = "Dati_Understat_Storico_2014_2026.xlsx"
FILE_SERIE_B = "Dati_Serie_B_2025_26.xlsx"
FILE_CHAMPIONSHIP = "Dati_Championship_2025_26.xlsx"
FILE_CHAMPIONS = "Dati_Champions_2025_26.xlsx"
MODEL_HOME_PKL = 'xgboost_home_master.pkl'
MODEL_AWAY_PKL = 'xgboost_away_master.pkl'

try:
    xgb_model_home = joblib.load(MODEL_HOME_PKL)
    xgb_model_away = joblib.load(MODEL_AWAY_PKL)
    ml_active = True
except Exception:
    ml_active = False

# ==============================================================================
# NLP E MOTORE AGENTE TATTICO
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def estrai_news_google(squadra):
    query = urllib.parse.quote(f"{squadra} calcio ultime notizie")
    try:
        response = requests.get(f"https://news.google.com/rss/search?q={query}+when:2d&hl=it&gl=IT&ceid=IT:it", timeout=5)
        if response.status_code == 200: return [item.find('title').text for item in ET.fromstring(response.text).findall('.//item')][:6]
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def estrai_news_google_en(squadra):
    query = urllib.parse.quote(f"{squadra} football news injury")
    try:
        response = requests.get(f"https://news.google.com/rss/search?q={query}+when:2d&hl=en-GB&gl=GB&ceid=GB:en", timeout=5)
        if response.status_code == 200: return [item.find('title').text for item in ET.fromstring(response.text).findall('.//item')][:6]
    except: return []

def chiedi_al_manager_ia(dati_partita, news_casa, news_trasferta):
    system_prompt = """Sei l'Assistente Tattico del sistema Sniper Quant.
Il tuo compito NON è calcolare, ma RAGIONARE. Leggi i pronostici e le ultime notizie online.
Fai un ragionamento cinico: le notizie confermano la bontà del pronostico matematico o inseriscono un rischio occulto?
Concludi dicendo se la giocata è CONFERMATA o DA EVITARE e perché."""
    prompt = f"{system_prompt}\n\n{dati_partita}\n\nNOTIZIE CASA:\n{news_casa}\n\nNOTIZIE TRASFERTA:\n{news_trasferta}\n\nAnalisi Tattica:"
    try:
        response = requests.post("http://localhost:11434/api/generate", json={"model": "gemma3:1b", "prompt": prompt, "stream": False}, timeout=60)
        return response.json().get("response", "Errore di connessione al cervello NLP locale.")
    except: return "⚠️ Server NLP offline."

def stima_statistiche_serie_b_con_ia(squadra_h, squadra_a):
    news_h = estrai_news_google(squadra_h)
    news_a = estrai_news_google(squadra_a)
    testo_news = f"News {squadra_h}: {news_h}. News {squadra_a}: {news_a}."
    prompt = f"""Leggi queste notizie sulle due squadre di Serie B: {testo_news}.
In base al momento di forma, stimami questi tre valori:
1. Expected Goals Casa (da 0.5 a 2.5)
2. Expected Goals Trasferta (da 0.5 a 2.5)
3. Indice PPDA (Pressione, da 8 a 15).
Rispondi SOLO con i tre numeri separati da virgola."""
    try:
        res = requests.post("http://localhost:11434/api/generate", json={"model": "gemma3:1b", "prompt": prompt, "stream": False}, timeout=15)
        numeri = re.findall(r"[-+]?\d*\.\d+|\d+", res.json().get("response", ""))
        if len(numeri) >= 3: return float(numeri[0]), float(numeri[1]), float(numeri[2])
    except: pass
    return 1.3, 1.1, 10.0 

def stima_statistiche_championship_con_ia(squadra_h, squadra_a):
    news_h = estrai_news_google_en(squadra_h)
    news_a = estrai_news_google_en(squadra_a)
    testo_news = f"News {squadra_h}: {news_h}. News {squadra_a}: {news_a}."
    prompt = f"""Leggi queste notizie sulle due squadre di English Championship: {testo_news}.
In base al momento di forma, stimami questi tre valori:
1. Expected Goals Casa (da 0.5 a 2.5)
2. Expected Goals Trasferta (da 0.5 a 2.5)
3. Indice PPDA (Pressione, da 8 a 15).
Rispondi SOLO con i tre numeri separati da virgola."""
    try:
        res = requests.post("http://localhost:11434/api/generate", json={"model": "gemma3:1b", "prompt": prompt, "stream": False}, timeout=15)
        numeri = re.findall(r"[-+]?\d*\.\d+|\d+", res.json().get("response", ""))
        if len(numeri) >= 3: return float(numeri[0]), float(numeri[1]), float(numeri[2])
    except: pass
    return 1.3, 1.1, 10.0 

def stima_statistiche_champions_con_ia(squadra_h, squadra_a):
    news_h = estrai_news_google_en(squadra_h)
    news_a = estrai_news_google_en(squadra_a)
    testo_news = f"News {squadra_h}: {news_h}. News {squadra_a}: {news_a}."
    prompt = f"""Leggi queste notizie sulle due squadre di UEFA Champions League: {testo_news}.
In base al momento di forma, stimami questi tre valori:
1. Expected Goals Casa (da 0.5 a 3.0)
2. Expected Goals Trasferta (da 0.5 a 3.0)
3. Indice PPDA (Pressione, da 8 a 15).
Rispondi SOLO con i tre numeri separati da virgola."""
    try:
        res = requests.post("http://localhost:11434/api/generate", json={"model": "gemma3:1b", "prompt": prompt, "stream": False}, timeout=15)
        numeri = re.findall(r"[-+]?\d*\.\d+|\d+", res.json().get("response", ""))
        if len(numeri) >= 3: return float(numeri[0]), float(numeri[1]), float(numeri[2])
    except: pass
    return 1.5, 1.2, 10.0 

# ==============================================================================
# LIBRERIA MATEMATICA COMPLETA & SHRINKAGE
# ==============================================================================
def calcola_expected_value(prob, quota): return ((prob / 100.0) * quota - 1.0) * 100.0

def calcola_xpts_storico(xg_for, xg_against):
    p1, px, p2 = 0.0, 0.0, 0.0
    for i in range(6):
        for j in range(6):
            prob = (math.exp(-xg_for) * (xg_for**i) / math.factorial(i)) * ((math.exp(-xg_against) * (xg_against**j) / math.factorial(j)))
            if i > j: p1 += prob
            elif i == j: px += prob
            else: p2 += prob
    tot = p1 + px + p2
    return (p1/tot) * 3 + (px/tot) * 1 if tot != 0 else 1.0

def calcola_frattura_strutturale(attacco, difesa, k=1.5):
    differenziale = attacco - difesa
    return 0.5 + ((1 / (1 + math.exp(-k * differenziale))) * 1.3)

def calculate_xg_final_proprietary(attacco, difesa, ec, molt_classifica, bonus, n_matches_history, is_new_team=False, home_team=True):
    base_xg = (attacco * calcola_frattura_strutturale(attacco, difesa)) + (ec - 1.0) * 0.20 + (molt_classifica - 1.0) * 0.35 + bonus
    media_lega = 1.45 if home_team else 1.20
    shrinkage = min(0.85, n_matches_history / 10.0) 
    base_xg = media_lega + (base_xg - media_lega) * shrinkage
    if is_new_team and home_team: base_xg *= 1.10
    return np.clip(base_xg, 0.3, 3.5)

def estrai_xg_da_quote(q1, qx, q2, qu25):
    margine_1x2 = (1/q1) + (1/qx) + (1/q2)
    p1 = (1/q1) / margine_1x2
    p2 = (1/q2) / margine_1x2
    pu25 = (1/qu25) 
    
    low, high = 0.1, 6.0
    xg_tot = 2.5
    for _ in range(20):
        mid = (low + high) / 2
        p_u = math.exp(-mid) * (1 + mid + (mid**2)/2)
        if p_u > pu25: low = mid
        else: high = mid
    xg_tot = (low + high) / 2
    
    best_h, best_a, min_err = xg_tot/2, xg_tot/2, 999
    for h_share in np.linspace(0.1, 0.9, 100):
        h_test = xg_tot * h_share
        a_test = xg_tot * (1 - h_share)
        calc_1, calc_x, calc_2 = poisson_probability_simple(h_test, a_test)
        err = (calc_1 - p1)**2 + (calc_2 - p2)**2
        if err < min_err:
            min_err = err
            best_h, best_a = h_test, a_test
            
    return best_h, best_a

def calculate_entropy_match(h_eval, a_eval):
    if len(h_eval) == 0 or len(a_eval) == 0: return 0.5
    def get_results(eval_list): return [1 if m.get('pts', 0) == 3 else (0 if m.get('pts', 0) == 1 else -1) for m in eval_list]
    def shannon_entropy(results):
        if len(results) == 0: return 0.0
        counts = np.bincount(np.array(results) + 1, minlength=3)
        probs = counts / len(results)
        return scipy_entropy(probs[probs > 0])
    result_entropy = (shannon_entropy(get_results(h_eval)) + shannon_entropy(get_results(a_eval))) / 2
    xg_volatility = min((np.std([h.get('xG', 0) for h in h_eval]) + np.std([h.get('xG', 0) for h in a_eval])) / 4, 1.0)
    return np.clip(0.6 * result_entropy + 0.4 * xg_volatility, 0.0, 1.0)

def calculate_matchup_bonus_advanced(h_eval, a_eval):
    if len(h_eval) == 0 or len(a_eval) == 0: return 0.0
    h_tactical = np.array([np.mean([x.get('IDT', 1.0) for x in h_eval]), np.mean([x.get('IMD', 1.0) for x in h_eval]), np.mean([x.get('EC', 1.0) for x in h_eval]), np.mean([x.get('IQO', 0.10) for x in h_eval])])
    a_tactical = np.array([np.mean([x.get('IDT', 1.0) for x in a_eval]), np.mean([x.get('IMD', 1.0) for x in a_eval]), np.mean([x.get('EC', 1.0) for x in a_eval]), np.mean([x.get('IQO', 0.10) for x in a_eval])])
    scaler = StandardScaler()
    combined = np.vstack([h_tactical, a_tactical])
    if np.all(combined == combined[0,:]): similarity = 1.0
    else:
        combined_normalized = scaler.fit_transform(combined)
        h_norm, a_norm = combined_normalized[0].reshape(1, -1), combined_normalized[1].reshape(1, -1)
        similarity = 0.0 if np.linalg.norm(h_norm) == 0 or np.linalg.norm(a_norm) == 0 else cosine_similarity(h_norm, a_norm)[0][0]
    avg_xg_diff = np.mean([x.get('xg_diff', 0) for x in h_eval])
    return np.clip(similarity * avg_xg_diff * 0.3, -0.35, 0.35)

def poisson_probability_with_home_advantage(xg_home, xg_away, home_advantage_multiplier):
    xg_h, xg_a = xg_home * home_advantage_multiplier, xg_away
    p_1, p_x, p_2 = 0.0, 0.0, 0.0
    for i in range(6):
        for j in range(6):
            prob = ((math.exp(-xg_h) * (xg_h ** i)) / math.factorial(i)) * ((math.exp(-xg_a) * (xg_a ** j)) / math.factorial(j))
            if i > j: p_1 += prob
            elif i == j: p_x += prob
            else: p_2 += prob
    tot = p_1 + p_x + p_2
    if tot == 0: return 33.3, 33.3, 33.3
    return (p_1/tot)*100, (p_x/tot)*100, (p_2/tot)*100

def poisson_probability_simple(xg_h, xg_a):
    p_1, p_x, p_2 = 0.0, 0.0, 0.0
    for i in range(6):
        for j in range(6):
            prob = ((math.exp(-xg_h) * (xg_h ** i)) / math.factorial(i)) * ((math.exp(-xg_a) * (xg_a ** j)) / math.factorial(j))
            if i > j: p_1 += prob
            elif i == j: p_x += prob
            else: p_2 += prob
    tot = p_1 + p_x + p_2
    if tot == 0: return 33.3, 33.3, 33.3
    return (p_1/tot), (p_x/tot), (p_2/tot) 

def calculate_poisson_o25(h_xg, a_xg):
    prob_under = 0
    for i in range(3):
        for j in range(3):
            if i + j <= 2:
                p_i = (math.exp(-h_xg) * (h_xg**i)) / math.factorial(i)
                p_j = (math.exp(-a_xg) * (a_xg**j)) / math.factorial(j)
                prob_under += p_i * p_j
    return (1 - prob_under)

def calculate_confidence_score(n_matches_h, n_matches_a, entropia, xg_diff_certainty, ppg_h, ppg_a):
    score = 100
    if n_matches_h < 3: score -= 20
    elif n_matches_h < 5: score -= 10
    if n_matches_a < 3: score -= 20
    elif n_matches_a < 5: score -= 10
    if entropia > 0.60: score -= min(int((entropia - 0.60) * 50), 30)
    if abs(ppg_h - ppg_a) < 0.1: score -= 5
    if xg_diff_certainty > 0.8: score += 15
    elif xg_diff_certainty > 0.5: score += 8
    if entropia < 0.40: score += 10
    return max(0, min(100, score))

def fill_missing_tactical_data(df, col_name, team_col='team'):
    df = df.copy()
    if col_name not in df.columns: return df
    media_per_team = df.groupby(team_col)[col_name].mean()
    media_globale = df[col_name].mean()
    df[col_name] = df.apply(lambda row: media_per_team.get(row[team_col], media_globale) if pd.isna(row[col_name]) else row[col_name], axis=1)
    return df

def validate_data_consistency(df_matches):
    df = df_matches.copy()
    if 'game_id' in df.columns: df = df.drop_duplicates(subset=['game_id'], keep='first')
    return df

def remove_outliers(df, cols, limits=(0.01, 0.99)):
    df = df.copy()
    for col in cols:
        if col not in df.columns: continue
        valid_data = df[col].dropna()
        if len(valid_data) == 0: continue
        p_low = np.percentile(valid_data, limits[0] * 100)
        p_high = np.percentile(valid_data, limits[1] * 100)
        df[col] = df[col].clip(p_low, p_high)
    return df

def simula_live_match(xg_pre_h, xg_pre_a, minuto, score_h, score_a, pressione_live_h, red_h, red_a):
    if minuto >= 90: return None
    t_rem = 90 - minuto
    t_ratio = (t_rem / 90.0) ** 0.85 
    rem_xg_h = xg_pre_h * t_ratio
    rem_xg_a = xg_pre_a * t_ratio
    if red_h: rem_xg_h *= 0.6; rem_xg_a *= 1.45
    if red_a: rem_xg_h *= 1.45; rem_xg_a *= 0.6
    diff = score_h - score_a
    if diff < 0: rem_xg_h *= 1.20; rem_xg_a *= 0.85
    elif diff > 0: rem_xg_h *= 0.85; rem_xg_a *= 1.20 
    press_factor_h = pressione_live_h / 50.0
    press_factor_a = (100 - pressione_live_h) / 50.0
    live_weight = minuto / 90.0 
    final_rem_xg_h = rem_xg_h * ((1 - live_weight) + (press_factor_h * live_weight))
    final_rem_xg_a = rem_xg_a * ((1 - live_weight) + (press_factor_a * live_weight))
    prob_exact = {}
    for i in range(7):
        for j in range(7):
            p_i = (math.exp(-final_rem_xg_h) * (final_rem_xg_h ** i)) / math.factorial(i)
            p_j = (math.exp(-final_rem_xg_a) * (final_rem_xg_a ** j)) / math.factorial(j)
            p_tot = p_i * p_j
            final_h = score_h + i
            final_a = score_a + j
            prob_exact[(final_h, final_a)] = prob_exact.get((final_h, final_a), 0) + p_tot
    p1, px, p2, over_25, under_25 = 0.0, 0.0, 0.0, 0.0, 0.0
    for (fh, fa), prob in prob_exact.items():
        if fh > fa: p1 += prob
        elif fh == fa: px += prob
        else: p2 += prob
        if (fh + fa) > 2.5: over_25 += prob
        else: under_25 += prob
    return {'1_Live': p1 * 100, 'X_Live': px * 100, '2_Live': p2 * 100, 'O2.5_Live': over_25 * 100, 'U2.5_Live': under_25 * 100}

def fetch_live_matches_api(api_key):
    try:
        response = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers={'x-apisports-key': api_key}, timeout=10)
        return response.json().get('response', []) if response.status_code == 200 else []
    except: return []

def fetch_live_stats_api(api_key, fixture_id):
    try:
        response = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}", headers={'x-apisports-key': api_key}, timeout=10)
        return response.json().get('response', []) if response.status_code == 200 else []
    except: return []

def get_pronostico_e_copertura(xg_home, xg_away, p1, px, p2, entropia_match):
    diff_xg = xg_home - xg_away
    if p1 >= 46.5 and diff_xg > 0.50: prono_secco = "1"
    elif p2 >= 45.0 and diff_xg < -0.45: prono_secco = "2"
    elif px >= 28.5 and abs(diff_xg) <= 0.20: prono_secco = "X"
    else: prono_secco = "1X" if xg_home >= xg_away else "X2"
    sicurezza = "1X" if diff_xg >= 0 else "X2"
    return prono_secco, sicurezza

def seleziona_miglior_multigol(prob_dict, tipo='FT'):
    if tipo == 'FT':
        strette = {'1-3': prob_dict.get('1-3', 0), '2-4': prob_dict.get('2-4', 0), '3-5': prob_dict.get('3-5', 0)}
        miglior_stretta = max(strette, key=strette.get)
        if strette[miglior_stretta] >= 60.0: return miglior_stretta, strette[miglior_stretta]
        larghe = {'1-4': prob_dict.get('1-4', 0), '2-5': prob_dict.get('2-5', 0), '3-6': prob_dict.get('3-6', 0)}
        miglior_larga = max(larghe, key=larghe.get)
        return miglior_larga, larghe[miglior_larga]
    elif tipo in ['HT', '2H']:
        strette = {'0-1': prob_dict.get('0-1', 0), '1-2': prob_dict.get('1-2', 0), '2-3': prob_dict.get('2-3', 0)}
        miglior_stretta = max(strette, key=strette.get)
        if strette[miglior_stretta] >= 55.0: return miglior_stretta, strette[miglior_stretta]
        return '1-3', prob_dict.get('1-3', 0)

def calcola_probabilita_gol_estese(xg_home, xg_away):
    prob_exact, prob_no_gol = {}, 0.0
    for i in range(10):
        for j in range(10):
            p_i = (math.exp(-xg_home) * (xg_home ** i)) / math.factorial(i)
            p_j = (math.exp(-xg_away) * (xg_away ** j)) / math.factorial(j)
            p_tot = p_i * p_j
            prob_exact[i+j] = prob_exact.get(i+j, 0) + p_tot
            if i == 0 or j == 0: prob_no_gol += p_tot
            
    somma_totale = sum(prob_exact.values()) or 1.0
    
    prob_ht, prob_2h = {}, {}
    xg_h_ht, xg_a_ht = xg_home * 0.45, xg_away * 0.45
    xg_h_2h, xg_a_2h = xg_home * 0.55, xg_away * 0.55
    
    for i in range(7):
        for j in range(7):
            prob_ht[i+j] = prob_ht.get(i+j, 0) + ((math.exp(-xg_h_ht) * (xg_h_ht ** i)) / math.factorial(i)) * ((math.exp(-xg_a_ht) * (xg_a_ht ** j)) / math.factorial(j))
            prob_2h[i+j] = prob_2h.get(i+j, 0) + ((math.exp(-xg_h_2h) * (xg_h_2h ** i)) / math.factorial(i)) * ((math.exp(-xg_a_2h) * (xg_a_2h ** j)) / math.factorial(j))
            
    somma_ht, somma_2h = sum(prob_ht.values()) or 1.0, sum(prob_2h.values()) or 1.0

    mg_ft = {
        '1-3': sum(prob_exact.get(k, 0) for k in range(1, 4)) / somma_totale * 100,
        '2-4': sum(prob_exact.get(k, 0) for k in range(2, 5)) / somma_totale * 100,
        '3-5': sum(prob_exact.get(k, 0) for k in range(3, 6)) / somma_totale * 100,
        '1-4': sum(prob_exact.get(k, 0) for k in range(1, 5)) / somma_totale * 100,
        '2-5': sum(prob_exact.get(k, 0) for k in range(2, 6)) / somma_totale * 100,
        '3-6': sum(prob_exact.get(k, 0) for k in range(3, 7)) / somma_totale * 100
    }
    mg_ht = {
        '0-1': sum(prob_ht.get(k, 0) for k in range(0, 2)) / somma_ht * 100,
        '1-2': sum(prob_ht.get(k, 0) for k in range(1, 3)) / somma_ht * 100,
        '2-3': sum(prob_ht.get(k, 0) for k in range(2, 4)) / somma_ht * 100,
        '1-3': sum(prob_ht.get(k, 0) for k in range(1, 4)) / somma_ht * 100
    }
    mg_2h = {
        '0-1': sum(prob_2h.get(k, 0) for k in range(0, 2)) / somma_2h * 100,
        '1-2': sum(prob_2h.get(k, 0) for k in range(1, 3)) / somma_2h * 100,
        '2-3': sum(prob_2h.get(k, 0) for k in range(2, 4)) / somma_2h * 100,
        '1-3': sum(prob_2h.get(k, 0) for k in range(1, 4)) / somma_2h * 100
    }

    best_ft_name, best_ft_prob = seleziona_miglior_multigol(mg_ft, 'FT')
    best_ht_name, best_ht_prob = seleziona_miglior_multigol(mg_ht, 'HT')
    best_2h_name, best_2h_prob = seleziona_miglior_multigol(mg_2h, '2H')

    return {
        'U0.5': (prob_exact.get(0, 0) / somma_totale) * 100, 'O0.5': (1 - prob_exact.get(0, 0) / somma_totale) * 100,
        'U1.5': (sum(prob_exact.get(k, 0) for k in range(2)) / somma_totale) * 100, 'O1.5': (1 - sum(prob_exact.get(k, 0) for k in range(2)) / somma_totale) * 100,
        'U2.5': (sum(prob_exact.get(k, 0) for k in range(3)) / somma_totale) * 100, 'O2.5': (1 - sum(prob_exact.get(k, 0) for k in range(3)) / somma_totale) * 100,
        'U3.5': (sum(prob_exact.get(k, 0) for k in range(4)) / somma_totale) * 100, 'O3.5': (1 - sum(prob_exact.get(k, 0) for k in range(4)) / somma_totale) * 100,
        'U4.5': (sum(prob_exact.get(k, 0) for k in range(5)) / somma_totale) * 100, 'O4.5': (1 - sum(prob_exact.get(k, 0) for k in range(5)) / somma_totale) * 100,
        'Gol': (1.0 - (prob_no_gol / somma_totale)) * 100, 'No_Gol': (prob_no_gol / somma_totale) * 100,
        'Best_MG_FT_Name': best_ft_name, 'Best_MG_FT_Prob': best_ft_prob,
        'Best_MG_HT_Name': best_ht_name, 'Best_MG_HT_Prob': best_ht_prob,
        'Best_MG_2H_Name': best_2h_name, 'Best_MG_2H_Prob': best_2h_prob
    }

def formatta_giocata(nome_mercato, prob, soglia=55.0):
    return f"{nome_mercato} | 🟢 {prob:.0f}%" if prob >= soglia else f"{nome_mercato} | 🔴 {prob:.0f}%"

# ==============================================================================
# ETL E MOTORE PREDITTIVO CENTRALE
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def estrai_dati_sicuri():
    if not os.path.exists(FILE_UNDERSTAT):
        return None
    try:
        xls = pd.ExcelFile(FILE_UNDERSTAT)
        df_m = pd.read_excel(xls, 'MATCH_LEVEL')
        df_m = validate_data_consistency(df_m)
        
        if 'date' in df_m.columns:
            df_m['date'] = pd.to_datetime(df_m['date'], errors='coerce', dayfirst=True)
            df_m['date'] = df_m['date'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)
            
            data_limite_sicura = st.session_state.data_limite
            df_m = df_m[(df_m['date'] >= data_limite_sicura) | (df_m['date'].isnull())]
            
        df_p = pd.read_excel(xls, 'PLAYER_SEASON_STATS') if 'PLAYER_SEASON_STATS' in xls.sheet_names else pd.DataFrame()
        if not df_p.empty and 'year' in df_p.columns:
            df_p = df_p[df_p['year'] >= st.session_state.anno_limite]
            
        df_l = pd.read_excel(xls, 'LEAGUE_TABLES') if 'LEAGUE_TABLES' in xls.sheet_names else None
        if df_l is not None and 'year' in df_l.columns:
            df_l = df_l[df_l['year'] >= st.session_state.anno_limite]

        df_tms = pd.DataFrame()
        if 'TEAM_MATCH_STATS' in xls.sheet_names:
            df_tms = pd.read_excel(xls, 'TEAM_MATCH_STATS')
            col_tattiche = ['game_id', 'home_ppda', 'away_ppda', 'home_deep_completions', 'away_deep_completions', 'home_shots', 'away_shots']
            col_presenti = [c for c in col_tattiche if c in df_tms.columns]
            if 'game_id' in df_m.columns and 'game_id' in col_presenti:
                df_m = df_m.merge(df_tms[col_presenti], on='game_id', how='left')

        cols_to_clean = [c for c in df_m.columns if 'ppda' in c or 'xg' in c or 'deep' in c]
        for c in cols_to_clean:
            df_m = fill_missing_tactical_data(df_m, c, 'home_team' if 'home' in c else 'away_team')
        df_m = remove_outliers(df_m, cols_to_clean)
            
        return {'m': df_m, 'p': df_p, 'l': df_l, 's': df_tms}
    except Exception as e: 
        st.error(f"Errore lettura database: {e}")
        return None

class AdvancedQuantEngine:
    def __init__(self, df_m, df_p, df_l):
        self.df_m = df_m.sort_values('date').reset_index(drop=True)
        for c in ['home_goals', 'away_goals']:
            if c in self.df_m.columns:
                self.df_m[c] = pd.to_numeric(self.df_m[c], errors='coerce')
        
        for c in ['xg_chain', 'xg_buildup']:
            if df_p is not None and not df_p.empty and c in df_p.columns:
                df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0)
        
        if df_p is not None and not df_p.empty and 'xg_buildup' in df_p.columns and 'xg_chain' in df_p.columns:
            df_p['irs_comp'] = np.exp(df_p['xg_buildup'] / (df_p['xg_chain'] + 0.1))
            self.irs_map = df_p.groupby('team')['irs_comp'].mean().to_dict()
        else: self.irs_map = {}

        if df_l is not None and not df_l.empty and 'pts' in df_l.columns and 'matches' in df_l.columns:
            df_l['ppg_storico'] = df_l['pts'] / df_l['matches'].replace(0, 1)
            self.storico_ppg_map = df_l.set_index('home_team')['ppg_storico'].to_dict()
        else: self.storico_ppg_map = {}

    def calcola_pronostici(self):
        cols_tattiche = ['home_deep_completions', 'home_ppda', 'home_shots', 'home_xg', 'away_deep_completions', 'away_ppda', 'away_shots', 'away_xg']
        for c in cols_tattiche:
            if c not in self.df_m.columns: self.df_m[c] = 1.0
            self.df_m[c] = pd.to_numeric(self.df_m[c], errors='coerce').fillna(1.0)

        self.df_m['h_IDT'] = (self.df_m['home_deep_completions'] / self.df_m['home_ppda'].replace(0, 5)) * np.log(self.df_m['home_shots'] + 2)
        self.df_m['a_IDT'] = (self.df_m['away_deep_completions'] / self.df_m['away_ppda'].replace(0, 5)) * np.log(self.df_m['away_shots'] + 2)
        self.df_m['h_EC'] = (self.df_m['home_goals'].fillna(0) + 0.1) / (self.df_m['home_xg'] + 0.1)
        self.df_m['a_EC'] = (self.df_m['away_goals'].fillna(0) + 0.1) / (self.df_m['away_xg'] + 0.1)
        self.df_m['h_IMD'] = (self.df_m['away_ppda'].replace(0, 5) / (self.df_m['away_deep_completions'] + 1)) * (1 / (self.df_m['away_xg'] + 0.5))
        self.df_m['a_IMD'] = (self.df_m['home_ppda'].replace(0, 5) / (self.df_m['home_deep_completions'] + 1)) * (1 / (self.df_m['home_xg'] + 0.5))
        self.df_m['h_IQO'] = self.df_m['home_xg'] / self.df_m['home_shots'].replace(0, 1)
        self.df_m['a_IQO'] = self.df_m['away_xg'] / self.df_m['away_shots'].replace(0, 1)
        self.df_m.replace([np.inf, -np.inf], 1.0, inplace=True)

        team_history, results = {}, []
        AVG_PPG, OGGI = 1.35, pd.Timestamp.today().normalize()

        for _, row in self.df_m.iterrows():
            h, a = row['home_team'], row['away_team']
            is_past = pd.notnull(row.get('home_goals')) and str(row.get('home_goals')).strip() != ""

            d_match_raw = pd.to_datetime(row.get('date', pd.NaT), dayfirst=True)
            d_match = d_match_raw.replace(tzinfo=None) if pd.notnull(d_match_raw) else pd.NaT
            
            h_hist_raw, a_hist_raw = team_history.get(h, []), team_history.get(a, [])

            if is_past:
                h_goals, a_goals = float(row['home_goals']), float(row['away_goals'])
                h_pts_earned = 3 if h_goals > a_goals else (1 if h_goals == a_goals else 0)
                a_pts_earned = 3 if a_goals > h_goals else (1 if h_goals == a_goals else 0)
                h_xpts, a_xpts = calcola_xpts_storico(row['home_xg'], row['away_xg']), calcola_xpts_storico(row['away_xg'], row['home_xg'])
                is_tight = abs(row['home_xg'] - row['away_xg']) <= 0.6
                team_history.setdefault(h, []).append({'opp_team': a, 'venue': 'home', 'xG': row['home_xg'], 'IDT': row['h_IDT'], 'IMD': row['h_IMD'], 'EC': row['h_EC'], 'IQO': row['h_IQO'], 'pts': h_pts_earned, 'xpts': h_xpts, 'xg_diff': (row['home_xg'] - row['away_xg']), 'is_tight': is_tight, 'clutch_win': (is_tight and h_pts_earned == 3)})
                team_history.setdefault(a, []).append({'opp_team': h, 'venue': 'away', 'xG': row['away_xg'], 'IDT': row['a_IDT'], 'IMD': row['a_IMD'], 'EC': row['a_EC'], 'IQO': row['a_IQO'], 'pts': a_pts_earned, 'xpts': a_xpts, 'xg_diff': (row['away_xg'] - row['home_xg']), 'is_tight': is_tight, 'clutch_win': (is_tight and a_pts_earned == 3)})
            else:
                if pd.notnull(d_match) and OGGI - pd.Timedelta(days=3) <= d_match.normalize() <= OGGI + pd.Timedelta(days=14):
                    h_eval_long, a_eval_long = h_hist_raw, a_hist_raw
                    h_eval_short = h_eval_long[-5:] if len(h_eval_long) >= 5 else h_eval_long
                    a_eval_short = a_eval_long[-5:] if len(a_eval_long) >= 5 else a_eval_long

                    N_h_long, N_a_long = len(h_eval_long), len(a_eval_long)
                    if N_h_long >= 5 and N_a_long >= 5: 
                        pesi_h = [0.85 ** (N_h_long - 1 - i) for i in range(N_h_long)]
                        pesi_h = [w / sum(pesi_h) for w in pesi_h] 
                        pesi_a = [0.85 ** (N_a_long - 1 - i) for i in range(N_a_long)]
                        pesi_a = [w / sum(pesi_a) for w in pesi_a]

                        h_xg_dna, a_xg_dna = sum(x['xG']*p for x,p in zip(h_eval_long, pesi_h)), sum(x['xG']*p for x,p in zip(a_eval_long, pesi_a))
                        h_idt_avg, a_idt_avg = sum(x['IDT']*p for x,p in zip(h_eval_long, pesi_h)), sum(x['IDT']*p for x,p in zip(a_eval_long, pesi_a))
                        h_imd_avg, a_imd_avg = sum(x['IMD']*p for x,p in zip(h_eval_long, pesi_h)), sum(x['IMD']*p for x,p in zip(a_eval_long, pesi_a))
                        h_ec_avg, a_ec_avg = sum(x['EC']*p for x,p in zip(h_eval_long, pesi_h)), sum(x['EC']*p for x,p in zip(a_eval_long, pesi_a))
                        
                        h_momentum_multiplier = 0.85 + ((sum(x['xpts'] for x in h_eval_short) / (len(h_eval_short)*3 if len(h_eval_short)>0 else 1)) * 0.30)
                        a_momentum_multiplier = 0.85 + ((sum(x['xpts'] for x in a_eval_short) / (len(a_eval_short)*3 if len(a_eval_short)>0 else 1)) * 0.30)

                        entropia_match = calculate_entropy_match(h_eval_short, a_eval_short)
                        h_ppg_home = sum(x['xpts'] for x in [x for x in h_eval_long if x['venue'] == 'home']) / len([x for x in h_eval_long if x['venue'] == 'home']) if [x for x in h_eval_long if x['venue'] == 'home'] else AVG_PPG
                        h_ppg_away = sum(x['xpts'] for x in [x for x in h_eval_long if x['venue'] == 'away']) / len([x for x in h_eval_long if x['venue'] == 'away']) if [x for x in h_eval_long if x['venue'] == 'away'] else AVG_PPG
                        polarizzazione_h = np.clip(h_ppg_home / (h_ppg_away + 0.1), 0.8, 2.5)

                        h_ppg = (((sum(x['xpts'] for x in h_eval_long) / N_h_long if N_h_long>0 else AVG_PPG) * N_h_long) + (self.storico_ppg_map.get(h, AVG_PPG) * 8)) / (N_h_long + 8)
                        a_ppg = (((sum(x['xpts'] for x in a_eval_long) / N_a_long if N_a_long>0 else AVG_PPG) * N_a_long) + (self.storico_ppg_map.get(a, AVG_PPG) * 8)) / (N_a_long + 8)

                        gap_classifica = h_ppg - a_ppg
                        molt_classifica_h = 1 + (gap_classifica * 0.15) if gap_classifica > 0 else 1.0
                        molt_classifica_a = 1 + (abs(gap_classifica) * 0.15) if gap_classifica < 0 else 1.0

                        h_irs, a_irs = self.irs_map.get(h, 1.5), self.irs_map.get(a, 1.5)
                        h_att = ((h_xg_dna * 0.50) + (h_idt_avg * 0.25) + (h_irs * 0.25))
                        a_att = ((a_xg_dna * 0.50) + (a_idt_avg * 0.25) + (a_irs * 0.25))
                        
                        h_matchup_bonus = calculate_matchup_bonus_advanced(h_eval_long, a_eval_long)
                        a_matchup_bonus = calculate_matchup_bonus_advanced(a_eval_long, h_eval_long)

                        xg_h_fin = calculate_xg_final_proprietary(h_att, a_imd_avg, h_ec_avg, molt_classifica_h, h_matchup_bonus, N_h_long, is_new_team=N_h_long < 4, home_team=True) * h_momentum_multiplier
                        xg_a_fin = calculate_xg_final_proprietary(a_att, h_imd_avg, a_ec_avg, molt_classifica_a, a_matchup_bonus, N_a_long, is_new_team=False, home_team=False) * a_momentum_multiplier

                        cda_multiplier = np.clip(1.0 + (0.05 * polarizzazione_h) + (0.15 * max(0, h_ppg - a_ppg)), 1.02, 1.35) 
                        
                        if N_h_long >= 1 and N_a_long >= 1:
                            h_tight_matches, a_tight_matches = sum(1 for x in h_eval_long if x['is_tight']), sum(1 for x in a_eval_long if x['is_tight'])
                            h_cf = sum(1 for x in h_eval_long if x['clutch_win']) / h_tight_matches if h_tight_matches > 0 else 0.33
                            a_cf = sum(1 for x in a_eval_long if x['clutch_win']) / a_tight_matches if a_tight_matches > 0 else 0.33
                            if abs((xg_h_fin * cda_multiplier) - xg_a_fin) <= 0.45:
                                if h_cf > a_cf + 0.15: xg_h_fin *= 1.08; xg_a_fin *= 0.92
                                elif a_cf > h_cf + 0.15: xg_a_fin *= 1.08; xg_h_fin *= 0.92

                        p1_c, px_c, p2_c = poisson_probability_with_home_advantage(xg_h_fin, xg_a_fin, cda_multiplier)
                        prono_c, sic_c = get_pronostico_e_copertura(xg_h_fin, xg_a_fin, p1_c, px_c, p2_c, entropia_match)
                        probs_gol_c = calcola_probabilita_gol_estese(xg_h_fin * cda_multiplier, xg_a_fin)
                        
                        sem_c = lambda p: "✅" if p >= 55.0 else "⛔"
                        verdetto_1x2_c = f"{prono_c} | {sem_c(max(p1_c, px_c, p2_c))}"
                        verdetto_gol_c = f"Over 2.5 | {sem_c(probs_gol_c['O2.5'])}" if probs_gol_c['O2.5'] > 55 else f"Under 2.5 | {sem_c(probs_gol_c['U2.5'])}"
                        mercati_gol_prob_c = f"G:{probs_gol_c['Gol']:.0f}% | O1.5:{probs_gol_c['O1.5']:.0f}% | O2.5:{probs_gol_c['O2.5']:.0f}% | U3.5:{probs_gol_c['U3.5']:.0f}%"

                        bet_1x2_c = formatta_giocata(prono_c, max(p1_c, px_c, p2_c), 55.0)
                        bet_o05_c = formatta_giocata("O 0.5", probs_gol_c['O0.5'], 85.0)
                        bet_u05_c = formatta_giocata("U 0.5", probs_gol_c['U0.5'], 15.0)
                        bet_o15_c = formatta_giocata("O 1.5", probs_gol_c['O1.5'], 75.0)
                        bet_u15_c = formatta_giocata("U 1.5", probs_gol_c['U1.5'], 45.0)
                        bet_o25_c = formatta_giocata("O 2.5", probs_gol_c['O2.5'], 55.0)
                        bet_u25_c = formatta_giocata("U 2.5", probs_gol_c['U2.5'], 55.0)
                        bet_o35_c = formatta_giocata("O 3.5", probs_gol_c['O3.5'], 35.0)
                        bet_u35_c = formatta_giocata("U 3.5", probs_gol_c['U3.5'], 75.0)
                        bet_o45_c = formatta_giocata("O 4.5", probs_gol_c['O4.5'], 20.0)
                        bet_u45_c = formatta_giocata("U 4.5", probs_gol_c['U4.5'], 85.0)
                        
                        bet_mg_ft_c = formatta_giocata(f"MG {probs_gol_c['Best_MG_FT_Name']}", probs_gol_c['Best_MG_FT_Prob'], 60.0)
                        bet_mg_ht_c = formatta_giocata(f"MG {probs_gol_c['Best_MG_HT_Name']} (1°T)", probs_gol_c['Best_MG_HT_Prob'], 55.0)
                        bet_mg_2h_c = formatta_giocata(f"MG {probs_gol_c['Best_MG_2H_Name']} (2°T)", probs_gol_c['Best_MG_2H_Prob'], 55.0)

                        results.append({
                            'Data_dt': d_match, 'Lega': row.get('league', 'N/D'), 'Partita': f"{h} - {a}",
                            'Verdetto_1X2': verdetto_1x2_c, 'Verdetto_Copertura': f"{sic_c} | ✅", 'Verdetto_Gol': verdetto_gol_c,
                            '1(%)': p1_c, 'X(%)': px_c, '2(%)': p2_c, 'Mercati_Gol_Prob': mercati_gol_prob_c,
                            'Bet_1X2': bet_1x2_c, 'Bet_O05': bet_o05_c, 'Bet_U05': bet_u05_c, 'Bet_O15': bet_o15_c, 'Bet_U15': bet_u15_c,
                            'Bet_O25': bet_o25_c, 'Bet_U25': bet_u25_c, 'Bet_O35': bet_o35_c, 'Bet_U35': bet_u35_c, 'Bet_O45': bet_o45_c, 'Bet_U45': bet_u45_c,
                            'Bet_MG_FT': bet_mg_ft_c, 'Bet_MG_HT': bet_mg_ht_c, 'Bet_MG_2H': bet_mg_2h_c,
                            '1_str': f"{p1_c:.1f}%", 'X_str': f"{px_c:.1f}%", '2_str': f"{p2_c:.1f}%", 'Pronostico_Puro': prono_c,
                            'O2.5_val': probs_gol_c['O2.5'], 'U2.5_val': probs_gol_c['U2.5'], 'O1.5_val': probs_gol_c['O1.5'],
                            'Copertura_Pura': sic_c,
                            'Rating': calculate_confidence_score(N_h_long, N_a_long, entropia_match, abs(xg_h_fin-xg_a_fin), h_ppg, a_ppg)
                        })

        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res.sort_values('Data_dt').reset_index(drop=True)
            df_res['Data'] = df_res['Data_dt'].apply(lambda x: x.strftime('%d/%m %H:%M') if pd.notnull(x) else "N/D")
        return df_res

class XGBoostInferenceEngine:
    def __init__(self, df_m):
        self.df_m = df_m.sort_values('date').reset_index(drop=True)
        for c in ['home_goals', 'away_goals']:
            if c in self.df_m.columns:
                self.df_m[c] = pd.to_numeric(self.df_m[c], errors='coerce')
                
        cols_tattiche = ['home_deep_completions', 'home_ppda', 'home_shots', 'home_xg', 'away_deep_completions', 'away_ppda', 'away_shots', 'away_xg']
        for c in cols_tattiche:
            if c not in self.df_m.columns: self.df_m[c] = 5.0
            self.df_m[c] = pd.to_numeric(self.df_m[c], errors='coerce').fillna(5.0)

        self.df_m['h_IDT'] = (self.df_m['home_deep_completions'] / self.df_m['home_ppda'].replace(0, 5)) * np.log(self.df_m['home_shots'] + 2)
        self.df_m['a_IDT'] = (self.df_m['away_deep_completions'] / self.df_m['away_ppda'].replace(0, 5)) * np.log(self.df_m['away_shots'] + 2)
        self.df_m['h_IMD'] = (self.df_m['away_ppda'].replace(0, 5) / self.df_m['away_deep_completions'].replace(0, 1)) * (1 / (self.df_m['away_xg'] + 0.5))
        self.df_m['a_IMD'] = (self.df_m['home_ppda'].replace(0, 5) / self.df_m['home_deep_completions'].replace(0, 1)) * (1 / (self.df_m['home_xg'] + 0.5))
        self.df_m['h_EC'] = (self.df_m['home_goals'].fillna(0) + 0.1) / (self.df_m['home_xg'] + 0.1)
        self.df_m['a_EC'] = (self.df_m['away_goals'].fillna(0) + 0.1) / (self.df_m['away_xg'] + 0.1)
        self.df_m['h_IQO'] = self.df_m['home_xg'] / self.df_m['home_shots'].replace(0, 1)
        self.df_m['a_IQO'] = self.df_m['away_xg'] / self.df_m['away_shots'].replace(0, 1)
        self.df_m.replace([np.inf, -np.inf], 1.0, inplace=True)

    def esegui_inferenza(self):
        if not ml_active: return pd.DataFrame()
        
        team_stats, results_ai = {}, []
        OGGI = pd.Timestamp.today().normalize()
        LIM_PASSATO = OGGI - pd.Timedelta(days=3)
        LIM_FUTURO = OGGI + pd.Timedelta(days=14)

        for _, row in self.df_m.iterrows():
            h, a = row['home_team'], row['away_team']
            is_past = pd.notnull(row.get('home_goals')) and str(row.get('home_goals')).strip() != ""
            
            d_match_raw = pd.to_datetime(row.get('date', pd.NaT), dayfirst=True)
            d_match = d_match_raw.replace(tzinfo=None) if pd.notnull(d_match_raw) else pd.NaT

            h_hist, a_hist = team_stats.get(h, []), team_stats.get(a, [])

            if is_past:
                h_pts_earned = 3 if row['home_goals'] > row['away_goals'] else (1 if row['home_goals'] == row['away_goals'] else 0)
                a_pts_earned = 3 if row['away_goals'] > row['home_goals'] else (1 if row['home_goals'] == row['away_goals'] else 0)
                team_stats.setdefault(h, []).append({'pts': h_pts_earned, 'xG': row['home_xg'], 'IDT': row['h_IDT'], 'IMD': row['h_IMD'], 'EC': row['h_EC'], 'IQO': row['h_IQO']})
                team_stats.setdefault(a, []).append({'pts': a_pts_earned, 'xG': row['away_xg'], 'IDT': row['a_IDT'], 'IMD': row['a_IMD'], 'EC': row['a_EC'], 'IQO': row['a_IQO']})
            else:
                if pd.notnull(d_match) and LIM_PASSATO <= d_match.normalize() <= LIM_FUTURO:
                    if len(h_hist) >= 5 and len(a_hist) >= 5:
                        h_eval, a_eval = h_hist[-10:], a_hist[-10:]

                        e_h = scipy_entropy(np.bincount([x['pts'] for x in h_hist[-5:]], minlength=4)[[0,1,3]] / 5.0)
                        e_a = scipy_entropy(np.bincount([x['pts'] for x in a_hist[-5:]], minlength=4)[[0,1,3]] / 5.0)
                        entropia_match = np.clip((e_h + e_a) / 2.2, 0, 1)

                        features_dict = {
                            'h_xg_mean': np.mean([x['xG'] for x in h_eval]), 'a_xg_mean': np.mean([x['xG'] for x in a_eval]),
                            'h_idt_mean': np.mean([x['IDT'] for x in h_eval]), 'a_idt_mean': np.mean([x['IDT'] for x in a_eval]),
                            'h_imd_mean': np.mean([x['IMD'] for x in h_eval]), 'a_imd_mean': np.mean([x['IMD'] for x in a_eval]),
                            'h_ec_mean': np.mean([x['EC'] for x in h_eval]), 'a_ec_mean': np.mean([x['EC'] for x in a_eval]),
                            'h_iqo_mean': np.mean([x['IQO'] for x in h_eval]), 'a_iqo_mean': np.mean([x['IQO'] for x in a_eval]),
                            'h_ppg': np.mean([x['pts'] for x in h_hist]), 'a_ppg': np.mean([x['pts'] for x in a_hist]),
                            'h_entropy': e_h, 'a_entropy': e_a
                        }
                        X_infer = pd.DataFrame([features_dict])
                        
                        xg_ai_h = xgb_model_home.predict(X_infer)[0]
                        xg_ai_a = xgb_model_away.predict(X_infer)[0]

                        p1_ai, px_ai, p2_ai = poisson_probability_simple(xg_ai_h, xg_ai_a)
                        prono_ai, sic_ai = get_pronostico_e_copertura(xg_ai_h, xg_ai_a, p1_ai * 100, px_ai * 100, p2_ai * 100, entropia_match)
                        probs_gol_ai = calcola_probabilita_gol_estese(xg_ai_h, xg_ai_a)

                        sem_c = lambda p: "✅" if p >= 55.0 else "⛔"
                        verdetto_1x2_ai = f"{prono_ai} | {sem_c(max(p1_ai, px_ai, p2_ai) * 100)}"
                        verdetto_gol_ai = f"Over 2.5 | {sem_c(probs_gol_ai['O2.5'])}" if probs_gol_ai['O2.5'] > 55 else f"Under 2.5 | {sem_c(probs_gol_ai['U2.5'])}"
                        mercati_gol_prob_ai = f"G:{probs_gol_ai['Gol']:.0f}% | O1.5:{probs_gol_ai['O1.5']:.0f}% | O2.5:{probs_gol_ai['O2.5']:.0f}% | U3.5:{probs_gol_ai['U3.5']:.0f}%"

                        bet_1x2_ai = formatta_giocata(prono_ai, max(p1_ai, px_ai, p2_ai) * 100, 58.0) 
                        bet_o05_ai = formatta_giocata("O 0.5", probs_gol_ai['O0.5'], 85.0)
                        bet_u05_ai = formatta_giocata("U 0.5", probs_gol_ai['U0.5'], 20.0)
                        bet_o15_ai = formatta_giocata("O 1.5", probs_gol_ai['O1.5'], 75.0)
                        bet_u15_ai = formatta_giocata("U 1.5", probs_gol_ai['U1.5'], 45.0)
                        bet_o25_ai = formatta_giocata("O 2.5", probs_gol_ai['O2.5'], 58.0)
                        bet_u25_ai = formatta_giocata("U 2.5", probs_gol_ai['U2.5'], 58.0)
                        bet_o35_ai = formatta_giocata("O 3.5", probs_gol_ai['O3.5'], 35.0)
                        bet_u35_ai = formatta_giocata("U 3.5", probs_gol_ai['U3.5'], 75.0)
                        bet_o45_ai = formatta_giocata("O 4.5", probs_gol_ai['O4.5'], 20.0)
                        bet_u45_ai = formatta_giocata("U 4.5", probs_gol_ai['U4.5'], 85.0)
                        
                        bet_mg_ft_ai = formatta_giocata(f"MG {probs_gol_ai['Best_MG_FT_Name']}", probs_gol_ai['Best_MG_FT_Prob'], 60.0)
                        bet_mg_ht_ai = formatta_giocata(f"MG {probs_gol_ai['Best_MG_HT_Name']} (1°T)", probs_gol_ai['Best_MG_HT_Prob'], 55.0)
                        bet_mg_2h_ai = formatta_giocata(f"MG {probs_gol_ai['Best_MG_2H_Name']} (2°T)", probs_gol_ai['Best_MG_2H_Prob'], 55.0)

                        results_ai.append({
                            'Data_dt': d_match, 'Lega': row.get('league', 'N/D'), 'Partita': f"{h} - {a}",
                            'Verdetto_1X2': verdetto_1x2_ai, 'Verdetto_Gol': verdetto_gol_ai, 'Mercati_Gol_Prob': mercati_gol_prob_ai,
                            'Bet_1X2': bet_1x2_ai, 'Bet_O05': bet_o05_ai, 'Bet_U05': bet_u05_ai, 'Bet_O15': bet_o15_ai, 'Bet_U15': bet_u15_ai,
                            'Bet_O25': bet_o25_ai, 'Bet_U25': bet_u25_ai, 'Bet_O35': bet_o35_ai, 'Bet_U35': bet_u35_ai, 'Bet_O45': bet_o45_ai, 'Bet_U45': bet_u45_ai,
                            'Bet_MG_FT': bet_mg_ft_ai, 'Bet_MG_HT': bet_mg_ht_ai, 'Bet_MG_2H': bet_mg_2h_ai,
                            '1(%)': p1_ai * 100, 'X(%)': px_ai * 100, '2(%)': p2_ai * 100, 'O2.5_val': probs_gol_ai['O2.5'], 'U2.5_val': probs_gol_ai['U2.5'], 'O1.5_val': probs_gol_ai['O1.5'],
                            'Pronostico_AI_Puro': prono_ai, 'Copertura_AI_Pura': sic_ai,
                            'Rating': calculate_confidence_score(10, 10, entropia_match, abs(xg_ai_h-xg_ai_a), 1.5, 1.5)
                        })

        df_res = pd.DataFrame(results_ai)
        if not df_res.empty:
            df_res = df_res.sort_values('Data_dt').reset_index(drop=True)
            df_res['Data'] = df_res['Data_dt'].apply(lambda x: x.strftime('%d/%m %H:%M'))
        return df_res

# ==============================================================================
# NUOVO MOTORE 3: IL DOMINATORE GEN-271 (O/U 2.5)
# ==============================================================================
class OUGen271_Engine:
    def __init__(self, data_m, data_s):
        self.df_m = data_m.sort_values('date').reset_index(drop=True)
        self.df_s = data_s
        self.df_s['date'] = pd.to_datetime(self.df_s['date'], errors='coerce')
        
        # Hyperparametri e Pesi Esatti estratti dalla Generazione 271
        self.w_att = 1.127
        self.w_def = 1.675
        self.w_ppda = 0.314
        self.w_deep = 1.016
        self.w_lt = 0.810
        self.w_poiss = 1.057
        self.w_mom = 1.388
        self.w_xgacc = 0.851

        self.features = [
            'CE_xg_accuracy', 'CE_expected_goals', 'poisson_o25_s', 'a_xg_acc_ag',
            'poisson_o25_v', 'h_xg_acc_ag', 'total_xg_s', 'def_sum_s',
            'h_venue_xg_ag', 'h_xg_acc_for', 'a_xg_acc_for', 'h_xg_for_s'
        ]
        
        self.model = xgb.XGBClassifier(
            n_estimators=162,
            learning_rate=0.0492,
            max_depth=5,
            subsample=0.6488,
            colsample_bytree=0.8242,
            min_child_weight=5,
            reg_alpha=0.3271,
            reg_lambda=1.9116,
            gamma=0.0813,
            objective='binary:logistic',
            eval_metric='auc',
            verbosity=0
        )

    def extract_tensors(self, df_target, is_training=False):
        dataset = []
        df_target = df_target.dropna(subset=['date'])
        
        for idx, row in df_target.iterrows():
            m_date = row['date']
            h_team, a_team = row['home_team'], row['away_team']
            
            # Anti-Data Leakage: strictly < match_date
            past_h = self.df_s[((self.df_s['home_team'] == h_team) | (self.df_s['away_team'] == h_team)) & (self.df_s['date'] < m_date)].sort_values('date', ascending=False).head(8)
            past_a = self.df_s[((self.df_s['home_team'] == a_team) | (self.df_s['away_team'] == a_team)) & (self.df_s['date'] < m_date)].sort_values('date', ascending=False).head(8)
            
            if len(past_h) >= 4 and len(past_a) >= 4:
                # Estrazione raw
                h_gf = np.where(past_h['home_team'] == h_team, past_h['home_goals'], past_h['away_goals']).astype(float)
                h_xgf = np.where(past_h['home_team'] == h_team, past_h['home_np_xg'], past_h['away_np_xg']).astype(float)
                h_xga = np.where(past_h['home_team'] == h_team, past_h['away_np_xg'], past_h['home_np_xg']).astype(float)
                h_dp = np.where(past_h['home_team'] == h_team, past_h['home_deep_completions'], past_h['away_deep_completions']).astype(float)
                
                a_gf = np.where(past_a['home_team'] == a_team, past_a['home_goals'], past_a['away_goals']).astype(float)
                a_xgf = np.where(past_a['home_team'] == a_team, past_a['home_np_xg'], past_a['away_np_xg']).astype(float)
                a_xga = np.where(past_a['home_team'] == a_team, past_a['away_np_xg'], past_a['home_np_xg']).astype(float)
                a_dp = np.where(past_a['home_team'] == a_team, past_a['home_deep_completions'], past_a['away_deep_completions']).astype(float)

                # Costruzione Feature Ingegnerizzate GEN-271
                h_xg_acc_for = (h_gf.sum() + 0.1) / (h_xgf.sum() + 0.1)
                a_xg_acc_for = (a_gf.sum() + 0.1) / (a_xgf.sum() + 0.1)
                
                h_xg_acc_ag = h_xga.mean() * self.w_def
                a_xg_acc_ag = a_xga.mean() * self.w_def
                
                CE_xg_accuracy = (h_xg_acc_for + a_xg_acc_for) * self.w_xgacc
                
                h_xg_for_s = h_xgf[:4].mean()
                a_xg_for_s = a_xgf[:4].mean()
                CE_expected_goals = ((h_xg_for_s * self.w_att) + (a_xg_acc_ag)) * self.w_lt
                
                total_xg_s = h_xg_for_s + a_xg_for_s
                def_sum_s = h_xga[:4].mean() + a_xga[:4].mean()
                
                poisson_o25_s = calculate_poisson_o25(h_xg_for_s, a_xga[:4].mean()) * self.w_poiss
                poisson_o25_v = calculate_poisson_o25(h_xg_for_s * h_xg_acc_for, a_xg_for_s * a_xg_acc_for)
                
                h_venue_xg_ag = h_xga.mean() * (self.w_deep * h_dp.mean() * 0.1)

                data_row = {
                    'Partita': f"{h_team} - {a_team}",
                    'Data_dt': m_date,
                    'CE_xg_accuracy': CE_xg_accuracy,
                    'CE_expected_goals': CE_expected_goals,
                    'poisson_o25_s': poisson_o25_s,
                    'a_xg_acc_ag': a_xg_acc_ag,
                    'poisson_o25_v': poisson_o25_v,
                    'h_xg_acc_ag': h_xg_acc_ag,
                    'total_xg_s': total_xg_s,
                    'def_sum_s': def_sum_s,
                    'h_venue_xg_ag': h_venue_xg_ag,
                    'h_xg_acc_for': h_xg_acc_for,
                    'a_xg_acc_for': a_xg_acc_for,
                    'h_xg_for_s': h_xg_for_s
                }
                
                if is_training:
                    tg = pd.to_numeric(row.get('home_goals', 0)) + pd.to_numeric(row.get('away_goals', 0))
                    data_row['Target'] = 1 if tg > 2.5 else 0
                    
                dataset.append(data_row)
                
        return pd.DataFrame(dataset)

    def train_and_predict(self):
        # Preparazione Dati Passati per il Training
        df_past = self.df_m.dropna(subset=['home_goals', 'away_goals'])
        train_data = self.extract_tensors(df_past, is_training=True)
        
        if train_data.empty: return pd.DataFrame()
        
        X_train = train_data[self.features]
        y_train = train_data['Target']
        self.model.fit(X_train, y_train)
        
        # Preparazione Dati Futuri per l'Inferenza
        oggi = pd.Timestamp.today().normalize()
        df_future = self.df_m[self.df_m['home_goals'].isnull() & (self.df_m['date'] >= oggi - pd.Timedelta(days=1))]
        
        infer_data = self.extract_tensors(df_future, is_training=False)
        if infer_data.empty: return pd.DataFrame()
        
        X_infer = infer_data[self.features]
        probs = self.model.predict_proba(X_infer)
        
        infer_data['Prob_Under_25'] = probs[:, 0] * 100
        infer_data['Prob_Over_25'] = probs[:, 1] * 100
        
        results = []
        for _, row in infer_data.iterrows():
            po = row['Prob_Over_25']
            pu = row['Prob_Under_25']
            verdetto = f"OVER 2.5 | 🟢 {po:.1f}%" if po > 58 else (f"UNDER 2.5 | 🔴 {pu:.1f}%" if pu > 58 else "NO BET | ⚖️")
            esito_puro = "OVER 2.5" if po > pu else "UNDER 2.5"
            confidenza = max(po, pu)
            
            results.append({
                'Data_dt': row['Data_dt'],
                'Data': row['Data_dt'].strftime('%d/%m %H:%M'),
                'Lega': self.df_m[self.df_m['date'] == row['Data_dt']]['league'].iloc[0] if len(self.df_m[self.df_m['date'] == row['Data_dt']]) > 0 else 'N/D',
                'Partita': row['Partita'],
                'Verdetto_Gen271': verdetto,
                'Esito_Puro': esito_puro,
                'Confidenza': confidenza,
                'Quota_Fair': 100.0 / confidenza if confidenza > 0 else 0
            })
            
        return pd.DataFrame(results)

def genera_schedine_ipotetiche(df_preds):
    if df_preds.empty: return {}
    
    # 1. Controllato tre volte: isoliamo ESCLUSIVAMENTE le partite di oggi
    oggi_date = pd.Timestamp.today().date()
    df_preds['temp_date'] = pd.to_datetime(df_preds['Data_dt']).dt.date
    df_oggi = df_preds[df_preds['temp_date'] == oggi_date].copy()
    
    if df_oggi.empty: 
        return {'Over': pd.DataFrame(), 'Under': pd.DataFrame()}
        
    # 2. Applichiamo la soglia di sicurezza AI sulle SOLE partite del giorno
    df_safe = df_oggi[df_oggi['Confidenza'] >= 68.0].sort_values('Confidenza', ascending=False)
    
    schedina_over = df_safe[df_safe['Esito_Puro'] == 'OVER 2.5'].head(4)
    schedina_under = df_safe[df_safe['Esito_Puro'] == 'UNDER 2.5'].head(4)
    
    return {
        'Over': schedina_over,
        'Under': schedina_under
    }

def run_all_engines():
    data = estrai_dati_sicuri()
    if data is not None and data['m'] is not None and not data['m'].empty:
        # 1. MOTORE CLASSICO
        engine_classic = AdvancedQuantEngine(data['m'], data['p'], data['l'])
        st.session_state.df_top5 = engine_classic.calcola_pronostici()
        
        # 2. MOTORE IA 1X2
        if ml_active:
            engine_ai = XGBoostInferenceEngine(data['m'])
            st.session_state.df_ai_future = engine_ai.esegui_inferenza()
            
        # 3. MOTORE GEN-271 (NUOVO O/U 2.5)
        if 's' in data and not data['s'].empty:
            engine_271 = OUGen271_Engine(data['m'], data['s'])
            st.session_state.df_gen271 = engine_271.train_and_predict()
            st.session_state.schedine_gen271 = genera_schedine_ipotetiche(st.session_state.df_gen271)

if not st.session_state.dati_precalcolati:
    with st.spinner(f"⏳ Boot Engine... Avvio Motori e Rete Gen-271 (Attendere prego)"):
        run_all_engines()
        st.session_state.dati_precalcolati = True

df_top5 = st.session_state.df_top5
df_ai_future = st.session_state.df_ai_future
df_gen271 = st.session_state.df_gen271
schedine_ipotetiche = st.session_state.schedine_gen271

# ==============================================================================
# MENU LATERALE E HUD INFORMAZIONI
# ==============================================================================
st.sidebar.markdown(f"## ⚙️ SYSTEM CONTROL")
st.sidebar.caption(f"⏱️ **Filtro Data Decay Attivo:** I calcoli sono basati esclusivamente sull'identità tattica recente (Dati validi da: {st.session_state.data_limite.strftime('%d/%m/%Y')}).")
st.sidebar.markdown("---")
sezione = st.sidebar.radio("MODULI OPERATIVI:", [
    "--- QUANT ENGINE (CLASSIC) ---",
    "1️⃣ Dashboard Probabilità", 
    "2️⃣ Analisi Singolo Match", 
    "3️⃣ Prediction Finale",
    "4️⃣ Live Betting Scanner",
    "5️⃣ Schedine (Analisi Scommettitore)",
    "--- AI ENGINE (XGBOOST) ---",
    "6️⃣ LAB AI (Inference)",
    "7️⃣ Schedine AI (Analisi Scommettitore)",
    "--- IL MOTORE O/U 2.5 ---",
    "8️⃣ LAB O/U 2.5 (Gen-271)",
    "9️⃣ Schedine O/U (Gen-271)",
    "--- TOOLS ---",
    "🔟 Sandbox (Simulatore Match)",
    "--- LEAGUE ESPANSIONI ---",
    "1️⃣1️⃣ Schedine Serie B (Scansione Web)",
    "1️⃣2️⃣ Schedine Championship (Scansione Web)",
    "1️⃣3️⃣ Schedine Champions League",
    "--- VALUE BETTING (API) ---",
    "1️⃣4️⃣ Auto-Betting (Value Finder)",
    "1️⃣5️⃣ Dark Market Engine"
], index=1)

# ==============================================================================
# SCHERMATE DELL'APP 
# ==============================================================================
if "---" in sezione:
    st.title("📈 Sniper Quant Terminal")
    st.info("👈 Seleziona un modulo operativo dal menu a sinistra.")

elif sezione == "1️⃣ Dashboard Probabilità":
    st.title("Terminale Probabilità | Motore Classico")
    if not df_top5.empty:
        col_config = {
            "1(%)": st.column_config.ProgressColumn("1 (%)", format="%.1f", min_value=0, max_value=100), 
            "X(%)": st.column_config.ProgressColumn("X (%)", format="%.1f", min_value=0, max_value=100), 
            "2(%)": st.column_config.ProgressColumn("2 (%)", format="%.1f", min_value=0, max_value=100), 
            "Mercati_Gol_Prob": st.column_config.TextColumn("Gol & Over (%)")
        }
        vista = df_top5[['Data', 'Lega', 'Partita', '1(%)', 'X(%)', '2(%)', 'Mercati_Gol_Prob']].copy()
        st.dataframe(vista, column_config=col_config, hide_index=True, use_container_width=True)
    else:
        st.warning("Nessun match imminente.")

elif sezione == "2️⃣ Analisi Singolo Match":
    st.title("Analisi Quantitativa e Manager IA")
    if not df_top5.empty:
        match_selezionato = st.selectbox("Seleziona Asse Partita per l'Analisi:", df_top5['Partita'].tolist())
        if match_selezionato:
            dati_match = df_top5[df_top5['Partita'] == match_selezionato].iloc[0]
            st.markdown(f"### {dati_match['Partita']} ({dati_match['Data']})")
            
            c_res1, c_res2, c_res3 = st.columns(3)
            with c_res1: st.markdown(f"<div class='quant-box-green'>TARGET 1X2<br><b>{dati_match['Verdetto_1X2']}</b></div>", unsafe_allow_html=True)
            with c_res2: st.markdown(f"<div class='quant-box-red'>HEDGE (Copertura)<br><b>{dati_match['Verdetto_Copertura']}</b></div>", unsafe_allow_html=True)
            with c_res3: st.markdown(f"<div class='quant-box-blue'>TARGET GOL<br><b>{dati_match['Verdetto_Gol']}</b></div>", unsafe_allow_html=True)

            st.markdown("#### Fair Odds & Value Edge Scanner")
            fair_1 = round(100.0 / dati_match['1(%)'], 2) if dati_match['1(%)'] > 0 else 2.0
            fair_x = round(100.0 / dati_match['X(%)'], 2) if dati_match['X(%)'] > 0 else 3.0
            fair_2 = round(100.0 / dati_match['2(%)'], 2) if dati_match['2(%)'] > 0 else 2.0

            cq1, cqx, cq2 = st.columns(3)
            q_1 = cq1.number_input("Quota Mercato 1", min_value=1.01, value=max(1.01, fair_1 - 0.20), step=0.05)
            q_x = cqx.number_input("Quota Mercato X", min_value=1.01, value=max(1.01, fair_x - 0.30), step=0.05)
            q_2 = cq2.number_input("Quota Mercato 2", min_value=1.01, value=max(1.01, fair_2 - 0.20), step=0.05)

            ev_1 = calcola_expected_value(dati_match['1(%)'], q_1)
            ev_x = calcola_expected_value(dati_match['X(%)'], q_x)
            ev_2 = calcola_expected_value(dati_match['2(%)'], q_2)

            def format_ev(ev_val): return f"<span style='color:#00FF00'>+{ev_val:.2f}%</span>" if ev_val > 0 else f"<span style='color:#FF3333'>{ev_val:.2f}%</span>"
            st.markdown(f"- EV 1: {format_ev(ev_1)} | EV X: {format_ev(ev_x)} | EV 2: {format_ev(ev_2)}", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🧠 Consulta l'Assistente Tattico IA")
            st.caption("L'IA leggerà il pronostico e cercherà le ultime notizie online per darti un parere ragionato, senza sovrascrivere la matematica.")
            if st.button("Cerca News e Genera Report Tattico"):
                with st.spinner("Analisi logica e ricerca infortuni in corso..."):
                    squadre = dati_match['Partita'].split(" - ")
                    news_h = estrai_news_google(squadre[0])
                    news_a = estrai_news_google(squadre[1])
                    dati_per_ia = f"Partita: {dati_match['Partita']}\nProb: 1({dati_match['1_str']}), X({dati_match['X_str']}), 2({dati_match['2_str']})\nVerdetto: {dati_match['Pronostico_Puro']}"
                    st.info(chiedi_al_manager_ia(dati_per_ia, "\n".join(news_h), "\n".join(news_a)))
    else:
        st.warning("Nessuna partita in calendario.")

elif sezione == "3️⃣ Prediction Finale":
    st.title("Riepilogo Predizioni Operative")
    if not df_top5.empty:
        vista = df_top5[['Data', 'Lega', 'Partita', 'Verdetto_1X2', 'Verdetto_Copertura', 'Verdetto_Gol']].copy()
        st.dataframe(vista, width='stretch', hide_index=True)
    else: st.warning("Nessuna partita in calendario.")

elif sezione == "4️⃣ Live Betting Scanner":
    st.title("Terminale Analisi Live")
    api_key_input = st.text_input("Inserisci Chiave API-Sports (Opzionale):", value="ec9046071a2e0054623823d629c2fcdb", type="password")
    
    if api_key_input and st.button("Fetch Live Server"):
        with st.spinner("Connessione ai server API..."):
            st.session_state.live_matches = fetch_live_matches_api(api_key_input)
            if st.session_state.live_matches: st.success("Dati Ricevuti.")
            else: st.warning("Nessun match o errore server.")
    
    live_minuto = 45; live_score_h = 0; live_score_a = 0; live_pressione = 50; live_red_h = False; live_red_a = False
    
    if 'live_matches' in st.session_state and st.session_state.live_matches:
        options = {f"{m['teams']['home']['name']} vs {m['teams']['away']['name']} ({m['fixture']['status']['elapsed']}'): {m['goals']['home']}-{m['goals']['away']}": m for m in st.session_state.live_matches}
        scelta = st.selectbox("Seleziona Match:", list(options.keys()))
        match_selezionato = options[scelta]
        live_minuto = int(match_selezionato['fixture']['status']['elapsed'] or 1)
        live_score_h = int(match_selezionato['goals']['home'] or 0)
        live_score_a = int(match_selezionato['goals']['away'] or 0)
        
        if st.button(f"Estrai Telemetria Live"):
            with st.spinner("Estrazione pacchetti dati..."):
                stats = fetch_live_stats_api(api_key_input, match_selezionato['fixture']['id'])
                if stats and len(stats) == 2:
                    stats_h = {s['type']: s['value'] for s in stats[0]['statistics']}
                    stats_a = {s['type']: s['value'] for s in stats[1]['statistics']}
                    possession_h = stats_h.get('Ball Possession', '50%')
                    live_pressione = int(str(possession_h).replace('%', '')) if possession_h else 50
                    live_red_h = int(stats_h.get('Red Cards', 0) or 0) > 0
                    live_red_a = int(stats_a.get('Red Cards', 0) or 0) > 0
                    st.success("Telemetria Sincronizzata.")

    col1, col2, col3 = st.columns(3)
    with col1:
        minuto = st.slider("Time [Min]", 1, 89, live_minuto)
        score_h = st.number_input("Gol [Casa]", 0, 10, live_score_h)
        score_a = st.number_input("Gol [Away]", 0, 10, live_score_a)
    with col2:
        xg_pre_h = st.number_input("Expected Goals Pre [Casa]", 0.1, 4.0, 1.5, step=0.1)
        xg_pre_a = st.number_input("Expected Goals Pre [Away]", 0.1, 4.0, 1.1, step=0.1)
    with col3:
        pressione = st.slider("Field Tilt (0=Away, 100=Casa)", 0, 100, live_pressione)
        red_h = st.checkbox("Cartellino Rosso [Casa]", value=live_red_h)
        red_a = st.checkbox("Cartellino Rosso [Away]", value=live_red_a)

    if st.button("CALCOLA SHIFT POISSONIANO"):
        with st.spinner("Bayesian Updating..."):
            res_live = simula_live_match(xg_pre_h, xg_pre_a, minuto, score_h, score_a, pressione, red_h, red_a)
            st.markdown("---")
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("P(Home Win)", f"{res_live['1_Live']:.1f}%")
            c_res2.metric("P(Draw)", f"{res_live['X_Live']:.1f}%")
            c_res3.metric("P(Away Win)", f"{res_live['2_Live']:.1f}%")
            
            cg1, cg2 = st.columns(2)
            cg1.metric("P(Over 2.5 Totali)", f"{res_live['O2.5_Live']:.1f}%")
            cg2.metric("P(Under 2.5 Totali)", f"{res_live['U2.5_Live']:.1f}%")

elif sezione == "5️⃣ Schedine (Analisi Scommettitore)":
    st.title("Terminale HD | Visione Scommettitore (Motore Classic)")
    
    if not df_top5.empty and 'Bet_1X2' in df_top5.columns:
        col_config_schedine = {
            "Data": st.column_config.TextColumn("🗓️ Data", width="small"),
            "Partita": st.column_config.TextColumn("⚔️ Match", width="medium"),
            "Bet_1X2": st.column_config.TextColumn("🎯 1X2"),
            "Bet_O05": st.column_config.TextColumn("O 0.5"),
            "Bet_U05": st.column_config.TextColumn("U 0.5"),
            "Bet_O15": st.column_config.TextColumn("O 1.5"),
            "Bet_U15": st.column_config.TextColumn("U 1.5"),
            "Bet_O25": st.column_config.TextColumn("O 2.5"),
            "Bet_U25": st.column_config.TextColumn("U 2.5"),
            "Bet_O35": st.column_config.TextColumn("O 3.5"),
            "Bet_U35": st.column_config.TextColumn("U 3.5"),
            "Bet_O45": st.column_config.TextColumn("O 4.5"),
            "Bet_U45": st.column_config.TextColumn("U 4.5"),
            "Bet_MG_FT": st.column_config.TextColumn("📊 Miglior MG (FT)"),
            "Bet_MG_HT": st.column_config.TextColumn("⏱️ Miglior MG (1°T)"),
            "Bet_MG_2H": st.column_config.TextColumn("⏱️ Miglior MG (2°T)")
        }
        
        vista_schedine = df_top5[['Data', 'Partita', 'Bet_1X2', 'Bet_O05', 'Bet_U05', 'Bet_O15', 'Bet_U15', 'Bet_O25', 'Bet_U25', 'Bet_O35', 'Bet_U35', 'Bet_O45', 'Bet_U45', 'Bet_MG_FT', 'Bet_MG_HT', 'Bet_MG_2H']].copy()
        st.dataframe(vista_schedine, column_config=col_config_schedine, hide_index=True, use_container_width=False, height=600)
    else:
        st.warning("Nessuna partita disponibile o calcolo non completato.")

elif sezione == "6️⃣ LAB AI (Inference)":
    st.title("Terminale AI (XGBoost + Semaforo)")
    if not ml_active: st.error("Modelli XGBoost offline.")
    elif not df_ai_future.empty:
        vista = df_ai_future[['Data', 'Lega', 'Partita', 'Verdetto_1X2', 'Verdetto_Gol', 'Mercati_Gol_Prob']].copy()
        st.dataframe(vista, hide_index=True, use_container_width=True)
    else:
        st.warning("Nessun match imminente trovato dall'IA.")

elif sezione == "7️⃣ Schedine AI (Analisi Scommettitore)":
    st.title("Terminale HD | Visione Scommettitore (AI XGBoost)")
    
    if not ml_active: st.error("Modelli XGBoost offline.")
    elif not df_ai_future.empty and 'Bet_1X2' in df_ai_future.columns:
        col_config_schedine_ai = {
            "Data": st.column_config.TextColumn("🗓️ Data", width="small"),
            "Partita": st.column_config.TextColumn("⚔️ Match", width="medium"),
            "Bet_1X2": st.column_config.TextColumn("🎯 1X2 (AI)"),
            "Bet_O05": st.column_config.TextColumn("O 0.5 (AI)"),
            "Bet_U05": st.column_config.TextColumn("U 0.5 (AI)"),
            "Bet_O15": st.column_config.TextColumn("O 1.5 (AI)"),
            "Bet_U15": st.column_config.TextColumn("U 1.5 (AI)"),
            "Bet_O25": st.column_config.TextColumn("O 2.5 (AI)"),
            "Bet_U25": st.column_config.TextColumn("U 2.5 (AI)"),
            "Bet_O35": st.column_config.TextColumn("O 3.5 (AI)"),
            "Bet_U35": st.column_config.TextColumn("U 3.5 (AI)"),
            "Bet_O45": st.column_config.TextColumn("O 4.5 (AI)"),
            "Bet_U45": st.column_config.TextColumn("U 4.5 (AI)"),
            "Bet_MG_FT": st.column_config.TextColumn("📊 Miglior MG FT (AI)"),
            "Bet_MG_HT": st.column_config.TextColumn("⏱️ Miglior MG 1°T (AI)"),
            "Bet_MG_2H": st.column_config.TextColumn("⏱️ Miglior MG 2°T (AI)")
        }
        
        vista_schedine_ai = df_ai_future[['Data', 'Partita', 'Bet_1X2', 'Bet_O05', 'Bet_U05', 'Bet_O15', 'Bet_U15', 'Bet_O25', 'Bet_U25', 'Bet_O35', 'Bet_U35', 'Bet_O45', 'Bet_U45', 'Bet_MG_FT', 'Bet_MG_HT', 'Bet_MG_2H']].copy()
        st.dataframe(vista_schedine_ai, column_config=col_config_schedine_ai, hide_index=True, use_container_width=False, height=600)
    else:
        st.warning("Nessuna partita disponibile nel LAB AI.")

elif sezione == "8️⃣ LAB O/U 2.5 (Gen-271)":
    st.title("🧬 Terminale Gen-271 | Over/Under 2.5")
    st.markdown("Il Motore definitivo addestrato con i pesi evolutivi. Focalizzato ESCLUSIVAMENTE sull'esplosione o sull'assenza di gol, decodificando l'accuratezza offensiva e la permeabilità difensiva.")
    
    if df_gen271 is None or df_gen271.empty:
        st.warning("Motore Gen-271 in attesa di dati futuri o offline.")
    else:
        vista = df_gen271[['Data', 'Lega', 'Partita', 'Verdetto_Gen271', 'Confidenza', 'Quota_Fair']].copy()
        
        col_config = {
            "Data": st.column_config.TextColumn("🗓️ Data"),
            "Lega": st.column_config.TextColumn("🌍 Lega"),
            "Partita": st.column_config.TextColumn("⚔️ Match"),
            "Verdetto_Gen271": st.column_config.TextColumn("🎯 Segno Predetto"),
            "Confidenza": st.column_config.ProgressColumn("🤖 Sicurezza AI (%)", format="%.1f", min_value=0, max_value=100),
            "Quota_Fair": st.column_config.NumberColumn("⚖️ Quota Fair", format="%.2f")
        }
        st.dataframe(vista, column_config=col_config, hide_index=True, use_container_width=True)

elif sezione == "9️⃣ Schedine O/U (Gen-271)":
    st.title("🔥 Generatore Schedine (Test Affidabilità Gen-271)")
    st.markdown("Queste schedine sono generate in automatico incrociando **ESCLUSIVAMENTE** le partite di **OGGI** dove la Rete Neurale supera il **68% di confidenza reale**.")
    
    if not schedine_ipotetiche or (schedine_ipotetiche['Over'].empty and schedine_ipotetiche['Under'].empty):
        st.warning("Nessuna partita odierna ha superato i test di sicurezza estrema (Soglia 68%). Il Gen-271 consiglia il NO BET per oggi.")
    else:
        col_over, col_under = st.columns(2)
        
        with col_over:
            st.subheader("📈 Schedina [BLOCCO OVER 2.5]")
            df_o = schedine_ipotetiche['Over']
            if df_o.empty:
                st.info("Nessun Over Blindato trovato oggi.")
            else:
                quota_tot_o = 1.0
                for _, row in df_o.iterrows():
                    q = max(1.30, row['Quota_Fair'] * 1.15) 
                    quota_tot_o *= q
                    st.markdown(f"**{row['Partita']}**")
                    st.caption(f"Segno: OVER 2.5 | Sicurezza: {row['Confidenza']:.1f}% | Quota: {q:.2f}")
                    st.divider()
                st.metric("Quota Totale Ipotetica", f"{quota_tot_o:.2f}")

        with col_under:
            st.subheader("🧊 Schedina [BLOCCO UNDER 2.5]")
            df_u = schedine_ipotetiche['Under']
            if df_u.empty:
                st.info("Nessun Under Blindato trovato oggi.")
            else:
                quota_tot_u = 1.0
                for _, row in df_u.iterrows():
                    q = max(1.30, row['Quota_Fair'] * 1.15)
                    quota_tot_u *= q
                    st.markdown(f"**{row['Partita']}**")
                    st.caption(f"Segno: UNDER 2.5 | Sicurezza: {row['Confidenza']:.1f}% | Quota: {q:.2f}")
                    st.divider()
                st.metric("Quota Totale Ipotetica", f"{quota_tot_u:.2f}")

elif sezione == "🔟 Sandbox (Simulatore Match)":
    st.title("🧪 Laboratorio Sandbox | Simulatore Scontri")
    
    dati_sandbox = estrai_dati_sicuri()
    if dati_sandbox is not None and dati_sandbox['m'] is not None and not dati_sandbox['m'].empty:
        squadre_disponibili = sorted(dati_sandbox['m']['home_team'].dropna().unique().tolist())
        
        c1, c2 = st.columns(2)
        team_h = c1.selectbox("Seleziona Squadra in Casa:", squadre_disponibili, index=0)
        team_a = c2.selectbox("Seleziona Squadra in Trasferta:", squadre_disponibili, index=1 if len(squadre_disponibili)>1 else 0)
        
        motore_scelto = st.radio("Scegli il Motore di Calcolo:", ["📈 Classico (Modello Quantitativo)", "🧠 IA (XGBoost)"])
        
        if st.button("Simula Match"):
            if team_h == team_a:
                st.error("Seleziona due squadre diverse.")
            else:
                with st.spinner("Estrazione matrici storiche e calcolo Poissoniano..."):
                    df_m_sb = dati_sandbox['m']
                    h_matches = df_m_sb[(df_m_sb['home_team'] == team_h) | (df_m_sb['away_team'] == team_h)]
                    a_matches = df_m_sb[(df_m_sb['home_team'] == team_a) | (df_m_sb['away_team'] == team_a)]
                    
                    h_xg_list, a_xg_list = [], []
                    
                    for _, row in h_matches.iterrows():
                        if pd.notnull(row.get('home_goals')):
                            if row['home_team'] == team_h: h_xg_list.append(row['home_xg'])
                            else: h_xg_list.append(row['away_xg'])
                    
                    for _, row in a_matches.iterrows():
                        if pd.notnull(row.get('home_goals')):
                            if row['home_team'] == team_a: a_xg_list.append(row['home_xg'])
                            else: a_xg_list.append(row['away_xg'])
                            
                    if len(h_xg_list) < 5 or len(a_xg_list) < 5:
                        st.warning("Dati insufficienti per questa simulazione nel periodo recente.")
                    else:
                        h_xg_base = np.mean(h_xg_list[-10:]) if len(h_xg_list) >= 10 else np.mean(h_xg_list)
                        a_xg_base = np.mean(a_xg_list[-10:]) if len(a_xg_list) >= 10 else np.mean(a_xg_list)
                        
                        xg_fin_h_classic = h_xg_base * 1.1 
                        xg_fin_a_classic = a_xg_base * 0.95
                        
                        xg_fin_h = xg_fin_h_classic
                        xg_fin_a = xg_fin_a_classic
                        
                        if "IA" in motore_scelto and ml_active:
                            X_inf = pd.DataFrame([{'h_xg_mean': xg_fin_h_classic, 'a_xg_mean': xg_fin_a_classic, 'h_idt_mean': 1.5, 'a_idt_mean': 1.5, 'h_imd_mean': 0.8, 'a_imd_mean': 0.8, 'h_ec_mean': 1.0, 'a_ec_mean': 1.0, 'h_iqo_mean': 0.1, 'a_iqo_mean': 0.1, 'h_ppg': 1.5, 'a_ppg': 1.5, 'h_entropy': 0.5, 'a_entropy': 0.5}])
                            xg_fin_h_ai = xgb_model_home.predict(X_inf)[0]
                            xg_fin_a_ai = xgb_model_away.predict(X_inf)[0]
                            xg_fin_h = xg_fin_h_ai
                            xg_fin_a = xg_fin_a_ai
                        elif not ml_active and "IA" in motore_scelto:
                            st.error("Modelli XGBoost offline. Uso il motore classico.")
                        
                        p1, px, p2 = poisson_probability_simple(xg_fin_h, xg_fin_a)
                        prono, sic = get_pronostico_e_copertura(xg_fin_h, xg_fin_a, p1*100, px*100, p2*100, 0.5)
                        probs_gol = calcola_probabilita_gol_estese(xg_fin_h, xg_fin_a)
                        
                        st.markdown(f"### Risultato Simulazione: {team_h} - {team_a}")
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Expected Goals Casa", f"{xg_fin_h:.2f}")
                        c2.metric("Expected Goals Trasferta", f"{xg_fin_a:.2f}")
                        c3.metric("Differenziale", f"{(xg_fin_h - xg_fin_a):.2f}")
                        
                        st.markdown("#### Quote Matematiche (Fair Price)")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("1", f"{1/p1:.2f}" if p1 > 0 else "N/A")
                        c2.metric("X", f"{1/px:.2f}" if px > 0 else "N/A")
                        c3.metric("2", f"{1/p2:.2f}" if p2 > 0 else "N/A")
                        
                        st.markdown("#### Probabilità Gol Estese")
                        cg1, cg2, cg3, cg4 = st.columns(4)
                        cg1.info(f"**O/U 1.5:** {probs_gol['O1.5']:.1f}% / {probs_gol['U1.5']:.1f}%")
                        cg2.info(f"**O/U 2.5:** {probs_gol['O2.5']:.1f}% / {probs_gol['U2.5']:.1f}%")
                        cg3.info(f"**O/U 3.5:** {probs_gol['O3.5']:.1f}% / {probs_gol['U3.5']:.1f}%")
                        cg4.info(f"**BTTS (Gol):** {probs_gol['Gol']:.1f}%")
                        
                        st.success(f"**Pronostico Diretto Suggerito:** {prono}")
    else:
        st.warning("Database non caricato.")

elif sezione == "1️⃣1️⃣ Schedine Serie B (Scansione Web)":
    st.title("🛡️ Schedine Serie B | Deep Web Scan")
    
    if os.path.exists(FILE_SERIE_B):
        try:
            df_b = pd.read_excel(FILE_SERIE_B, 'MATCH_LEVEL')
            df_b['date'] = pd.to_datetime(df_b['date'], errors='coerce', dayfirst=True)
            
            OGGI = pd.Timestamp.today().normalize()
            df_b_futuro = df_b[df_b['home_goals'].isnull() & (df_b['date'] >= OGGI)].copy()
            
            if df_b_futuro.empty:
                st.warning("Nessuna partita futura di Serie B trovata nel file locale.")
            else:
                if st.button("🌐 Avvia Scansione Web IA (Serie B)"):
                    risultati_b = []
                    progress_bar = st.progress(0.0)
                    totale_partite = len(df_b_futuro)
                    
                    for idx, (original_idx, row) in enumerate(df_b_futuro.iterrows()):
                        h, a = row['home_team'], row['away_team']
                        
                        with st.spinner(f"Scansione Web: Analisi {h} vs {a}..."):
                            xg_h_stima, xg_a_stima, ppda_stima = stima_statistiche_serie_b_con_ia(h, a)
                            p1, px, p2 = poisson_probability_simple(xg_h_stima, xg_a_stima)
                            prono, sic = get_pronostico_e_copertura(xg_h_stima, xg_a_stima, p1*100, px*100, p2*100, 0.5)
                            probs_gol = calcola_probabilita_gol_estese(xg_h_stima, xg_a_stima)
                            
                            sem_c = lambda p: "✅" if p >= 55.0 else "⛔"
                            bet_1x2 = formatta_giocata(prono, max(p1, px, p2)*100, 55.0)
                            bet_o15 = formatta_giocata("O 1.5", probs_gol['O1.5'], 75.0)
                            bet_o25 = formatta_giocata("O 2.5", probs_gol['O2.5'], 55.0)
                            bet_mg_ft = formatta_giocata(f"MG {probs_gol['Best_MG_FT_Name']}", probs_gol['Best_MG_FT_Prob'], 60.0)
                            
                            risultati_b.append({
                                'Data_dt': row['date'], 'Data': row['date'].strftime('%d/%m'), 'Partita': f"{h} - {a}",
                                'xG_Stimati': f"{xg_h_stima:.1f} - {xg_a_stima:.1f}", 'Bet_1X2': bet_1x2, 
                                'Bet_O15': bet_o15, 'Bet_O25': bet_o25, 'Bet_MG_FT': bet_mg_ft,
                                '1(%)': p1*100, 'X(%)': px*100, '2(%)': p2*100
                            })
                            time.sleep(2) 
                            progress_bar.progress(min((idx + 1) / totale_partite, 1.0))
                    
                    if risultati_b:
                        df_res_b = pd.DataFrame(risultati_b)
                        st.session_state.df_scraped_leagues = pd.concat([st.session_state.df_scraped_leagues, df_res_b], ignore_index=True)
                        st.dataframe(df_res_b[['Data', 'Partita', 'xG_Stimati', 'Bet_1X2', 'Bet_O15', 'Bet_O25', 'Bet_MG_FT']], hide_index=True, use_container_width=True)
                        st.success("Scansione Completata! I dati sono stati inviati al Modulo 14 per l'Auto-Betting.")

        except Exception as e:
            st.error(f"Errore lettura Dati Serie B: {e}")
    else:
        st.warning(f"File {FILE_SERIE_B} non trovato.")

elif sezione == "1️⃣2️⃣ Schedine Championship (Scansione Web)":
    st.title("🦁 Schedine Championship | Deep Web Scan")
    if os.path.exists(FILE_CHAMPIONSHIP):
        try:
            df_c = pd.read_excel(FILE_CHAMPIONSHIP, 'MATCH_LEVEL')
            df_c['date'] = pd.to_datetime(df_c['date'], errors='coerce', dayfirst=True)
            
            OGGI = pd.Timestamp.today().normalize()
            df_c_futuro = df_c[df_c['home_goals'].isnull() & (df_c['date'] >= OGGI)].copy()
            
            if df_c_futuro.empty:
                st.warning("Nessuna partita futura di Championship trovata.")
            else:
                if st.button("🌐 Avvia Scansione Web IA (Championship)"):
                    risultati_c = []
                    progress_bar = st.progress(0.0)
                    totale_partite = len(df_c_futuro)
                    
                    for idx, (original_idx, row) in enumerate(df_c_futuro.iterrows()):
                        h, a = row['home_team'], row['away_team']
                        
                        with st.spinner(f"UK Web Scan: Analisi {h} vs {a}..."):
                            xg_h_stima, xg_a_stima, ppda_stima = stima_statistiche_championship_con_ia(h, a)
                            p1, px, p2 = poisson_probability_simple(xg_h_stima, xg_a_stima)
                            prono, sic = get_pronostico_e_copertura(xg_h_stima, xg_a_stima, p1*100, px*100, p2*100, 0.5)
                            probs_gol = calcola_probabilita_gol_estese(xg_h_stima, xg_a_stima)
                            
                            bet_1x2 = formatta_giocata(prono, max(p1, px, p2)*100, 55.0)
                            bet_o15 = formatta_giocata("O 1.5", probs_gol['O1.5'], 75.0)
                            bet_o25 = formatta_giocata("O 2.5", probs_gol['O2.5'], 55.0)
                            bet_mg_ft = formatta_giocata(f"MG {probs_gol['Best_MG_FT_Name']}", probs_gol['Best_MG_FT_Prob'], 60.0)
                            
                            risultati_c.append({
                                'Data_dt': row['date'], 'Data': row['date'].strftime('%d/%m'), 'Partita': f"{h} - {a}",
                                'xG_Stimati': f"{xg_h_stima:.1f} - {xg_a_stima:.1f}", 'Bet_1X2': bet_1x2, 
                                'Bet_O15': bet_o15, 'Bet_O25': bet_o25, 'Bet_MG_FT': bet_mg_ft,
                                '1(%)': p1*100, 'X(%)': px*100, '2(%)': p2*100
                            })
                            time.sleep(2) 
                            progress_bar.progress(min((idx + 1) / totale_partite, 1.0))
                    
                    if risultati_c:
                        df_res_c = pd.DataFrame(risultati_c)
                        st.session_state.df_scraped_leagues = pd.concat([st.session_state.df_scraped_leagues, df_res_c], ignore_index=True)
                        st.dataframe(df_res_c[['Data', 'Partita', 'xG_Stimati', 'Bet_1X2', 'Bet_O15', 'Bet_O25', 'Bet_MG_FT']], hide_index=True, use_container_width=True)
                        st.success("Scansione Completata! I dati sono stati inviati al Modulo 14 per l'Auto-Betting.")

        except Exception as e:
            st.error(f"Errore: {e}")
    else:
        st.warning(f"File {FILE_CHAMPIONSHIP} non trovato.")

elif sezione == "1️⃣3️⃣ Schedine Champions League":
    st.title("⭐ Schedine Champions League | Deep Web Scan")
    if os.path.exists(FILE_CHAMPIONS):
        try:
            df_cl = pd.read_excel(FILE_CHAMPIONS, 'MATCH_LEVEL')
            df_cl['date'] = pd.to_datetime(df_cl['date'], errors='coerce', dayfirst=True)
            
            OGGI = pd.Timestamp.today().normalize()
            df_cl_futuro = df_cl[df_cl['home_goals'].isnull() & (df_cl['date'] >= OGGI)].copy()
            
            if df_cl_futuro.empty:
                st.warning("Nessuna partita futura di Champions League trovata.")
            else:
                if st.button("🌐 Avvia Scansione Web IA (Champions League)"):
                    risultati_cl = []
                    progress_bar = st.progress(0.0)
                    totale_partite = len(df_cl_futuro)
                    
                    for idx, (original_idx, row) in enumerate(df_cl_futuro.iterrows()):
                        h, a = row['home_team'], row['away_team']
                        
                        with st.spinner(f"European Web Scan: Analisi {h} vs {a}..."):
                            xg_h_stima, xg_a_stima, ppda_stima = stima_statistiche_champions_con_ia(h, a)
                            p1, px, p2 = poisson_probability_simple(xg_h_stima, xg_a_stima)
                            prono, sic = get_pronostico_e_copertura(xg_h_stima, xg_a_stima, p1*100, px*100, p2*100, 0.5)
                            probs_gol = calcola_probabilita_gol_estese(xg_h_stima, xg_a_stima)
                            
                            bet_1x2 = formatta_giocata(prono, max(p1, px, p2)*100, 55.0)
                            bet_o15 = formatta_giocata("O 1.5", probs_gol['O1.5'], 75.0)
                            bet_o25 = formatta_giocata("O 2.5", probs_gol['O2.5'], 55.0)
                            bet_mg_ft = formatta_giocata(f"MG {probs_gol['Best_MG_FT_Name']}", probs_gol['Best_MG_FT_Prob'], 60.0)
                            
                            risultati_cl.append({
                                'Data_dt': row['date'], 'Data': row['date'].strftime('%d/%m'), 'Partita': f"{h} - {a}",
                                'xG_Stimati': f"{xg_h_stima:.1f} - {xg_a_stima:.1f}", 'Bet_1X2': bet_1x2, 
                                'Bet_O15': bet_o15, 'Bet_O25': bet_o25, 'Bet_MG_FT': bet_mg_ft,
                                '1(%)': p1*100, 'X(%)': px*100, '2(%)': p2*100
                            })
                            time.sleep(2) 
                            progress_bar.progress(min((idx + 1) / totale_partite, 1.0))
                    
                    if risultati_cl:
                        df_res_cl = pd.DataFrame(risultati_cl)
                        st.session_state.df_scraped_leagues = pd.concat([st.session_state.df_scraped_leagues, df_res_cl], ignore_index=True)
                        st.dataframe(df_res_cl[['Data', 'Partita', 'xG_Stimati', 'Bet_1X2', 'Bet_O15', 'Bet_O25', 'Bet_MG_FT']], hide_index=True, use_container_width=True)
                        st.success("Scansione Completata! I dati sono stati inviati al Modulo 14 per l'Auto-Betting.")

        except Exception as e:
            st.error(f"Errore: {e}")
    else:
        st.warning(f"File {FILE_CHAMPIONS} non trovato.")

elif sezione == "1️⃣4️⃣ Auto-Betting (Value Finder)":
    st.title("💰 Auto-Betting Value Builder (API Reale)")
    st.markdown("Cerca vantaggi matematici su **TUTTO** il palinsesto calcolato oggi (Serie A, B, Champions, ecc).")

    api_key_input = st.text_input("Inserisci la tua chiave API-Sports:", value="ec9046071a2e0054623823d629c2fcdb", type="password")

    c1, c2 = st.columns(2)
    target_quota = c1.number_input("Quota Totale Bersaglio (Target):", min_value=2.0, value=5.0, step=0.5)
    stake = c2.number_input("Stake (Puntata in €):", min_value=1.0, value=10.0, step=1.0)

    if st.button("🚀 Cerca Valore e Costruisci Schedine su Goldbet"):
        if not api_key_input:
            st.error("⚠️ Serve la chiave API-Sports per scaricare le quote vere in tempo reale!")
        else:
            with st.spinner("Scaricamento match e quote in corso..."):
                oggi_str = pd.Timestamp.today().strftime('%Y-%m-%d')
                headers = {'x-apisports-key': api_key_input}

                try:
                    url_fixtures = f"https://v3.football.api-sports.io/fixtures?date={oggi_str}"
                    res_fix = requests.get(url_fixtures, headers=headers, timeout=15)
                    data_fix = res_fix.json().get('response', [])
                    
                    mappa_squadre = {}
                    for f in data_fix:
                        f_id = f['fixture']['id']
                        h = f['teams']['home']['name']
                        a = f['teams']['away']['name']
                        mappa_squadre[f_id] = (h, a)

                    url_odds = f"https://v3.football.api-sports.io/odds?date={oggi_str}"
                    res_odds = requests.get(url_odds, headers=headers, timeout=15)
                    data_odds = res_odds.json().get('response', [])

                    if not data_odds:
                        st.warning("⚠️ L'API non ha restituito quote per la giornata di oggi.")
                    else:
                        quote_reali = {}
                        
                        def normalizza(nome):
                            n = str(nome).lower()
                            rimuovi = ['fc', 'ac', 'as', 'ss', 'us', 'calcio', '1909', '1913', '1907', 'cfc', 'bc', 'united', 'city', 'town', 'albion', 'rovers', 'athletic', 'hotspur', 'sporting', 'club', 'internazionale', 'milano', 'munich', 'dortmund']
                            for w in rimuovi:
                                n = re.sub(rf'\b{w}\b', '', n)
                            n = n.replace('inter ', 'inter').replace('paris saint-germain', 'psg')
                            return n.strip().replace(' ', '')

                        for match in data_odds:
                            f_id = match['fixture']['id']
                            if f_id not in mappa_squadre: continue
                                
                            h_name, a_name = mappa_squadre[f_id]
                            bookmakers = match.get('bookmakers', [])
                            selected_bets = []
                            bookie_trovato = "N/D"
                            
                            goldbet_found = False
                            for bm in bookmakers:
                                if bm['name'].lower() == 'goldbet':
                                    selected_bets = bm.get('bets', [])
                                    bookie_trovato = "Goldbet"
                                    goldbet_found = True
                                    break
                            
                            if not goldbet_found and len(bookmakers) > 0:
                                selected_bets = bookmakers[0].get('bets', [])
                                bookie_trovato = bookmakers[0].get('name', 'Paracadute API')

                            odds_1x2 = {}
                            for b in selected_bets:
                                if b['name'] == 'Match Winner':
                                    for val in b['values']:
                                        if val['value'] == 'Home': odds_1x2['1'] = float(val['odd'])
                                        elif val['value'] == 'Draw': odds_1x2['X'] = float(val['odd'])
                                        elif val['value'] == 'Away': odds_1x2['2'] = float(val['odd'])
                                    break

                            if odds_1x2:
                                chiave = f"{normalizza(h_name)}_{normalizza(a_name)}"
                                quote_reali[chiave] = {'Nomi_Veri': f"{h_name} - {a_name}", 'Quote': odds_1x2, 'Bookmaker': bookie_trovato}

                        df_globale_c = df_top5.copy() if not df_top5.empty else pd.DataFrame()
                        df_globale_a = df_ai_future.copy() if not df_ai_future.empty else pd.DataFrame()
                        
                        if not st.session_state.df_scraped_leagues.empty:
                            df_globale_c = pd.concat([df_globale_c, st.session_state.df_scraped_leagues], ignore_index=True).drop_duplicates(subset=['Partita'])
                            df_globale_a = pd.concat([df_globale_a, st.session_state.df_scraped_leagues], ignore_index=True).drop_duplicates(subset=['Partita'])

                        if df_globale_c.empty:
                            st.warning("Nessun pronostico presente in memoria. Esegui prima i calcoli sui moduli precedenti.")
                        else:
                            st.success(f"✅ Analisi del Valore (EV) sulle {len(quote_reali)} partite del palinsesto mondiale in corso...")

                            def costruisci_schedina(df_motore):
                                if df_motore.empty: return [], 1.0
                                schedina = []
                                quota_tot = 1.0
                                oggi_dt = pd.Timestamp.today().normalize()
                                
                                df_motore['Data_dt'] = pd.to_datetime(df_motore['Data_dt'], errors='coerce')
                                df_oggi = df_motore[df_motore['Data_dt'].dt.normalize() == oggi_dt]

                                possibilita = []
                                for _, row in df_oggi.iterrows():
                                    squadre = row['Partita'].split(" - ")
                                    h_norm, a_norm = normalizza(squadre[0]), normalizza(squadre[1])
                                    chiave_cerca = f"{h_norm}_{a_norm}"

                                    if chiave_cerca in quote_reali:
                                        qr = quote_reali[chiave_cerca]['Quote']
                                        fonte = quote_reali[chiave_cerca]['Bookmaker']
                                        
                                        for segno, prob_col in [('1', '1(%)'), ('X', 'X(%)'), ('2', '2(%)')]:
                                            prob_calc = row.get(prob_col, 0)
                                            if segno in qr and prob_calc > 0:
                                                q_banco = qr[segno]
                                                ev = ((prob_calc / 100.0) * q_banco) - 1.0
                                                
                                                if ev > 0.05: 
                                                    possibilita.append({
                                                        'Partita': row['Partita'], 'Segno': segno,
                                                        'Quota': q_banco, 'Fonte': fonte,
                                                        'EV': f"+{ev * 100:.1f}%", 'Prob': f"{prob_calc:.1f}%"
                                                    })

                                possibilita.sort(key=lambda x: float(x['EV'].replace('+', '').replace('%', '')), reverse=True)

                                for bet in possibilita:
                                    if quota_tot >= target_quota: break
                                    if not any(b['Partita'] == bet['Partita'] for b in schedina):
                                        schedina.append(bet)
                                        quota_tot *= bet['Quota']

                                return schedina, quota_tot

                            schedina_classic, qt_classic = costruisci_schedina(df_globale_c)
                            schedina_ai, qt_ai = costruisci_schedina(df_globale_a)

                            col_c, col_a = st.columns(2)

                            with col_c:
                                st.subheader("📈 Schedina CLASSIC 1X2")
                                if not schedina_classic: st.warning("No Value found.")
                                else:
                                    st.table(pd.DataFrame(schedina_classic)[['Partita', 'Segno', 'Quota', 'EV']])
                                    st.metric("Quota Totale", f"{qt_classic:.2f}")

                            with col_a:
                                st.subheader("🧠 Schedina IA Pura 1X2")
                                if not ml_active: st.warning("IA Offline.")
                                elif not schedina_ai: st.warning("No Value found.")
                                else:
                                    st.table(pd.DataFrame(schedina_ai)[['Partita', 'Segno', 'Quota', 'EV']])
                                    st.metric("Quota Totale", f"{qt_ai:.2f}")

                except Exception as e:
                    st.error(f"Errore: {e}")

elif sezione == "1️⃣5️⃣ Dark Market Engine":
    st.title("🕵️‍♂️ Dark Market Engine (Risultati Esatti)")
    st.markdown("Algoritmo di **Ingegneria Inversa sulle Quote** + **Modificatore Bayesiano**. Sfrutta le quote dei Bookmaker per generare *Expected Goals Sintetici* su campionati asiatici, sudamericani o serie minori dove non esistono database.")

    st.sidebar.header("1️⃣ Inserisci Quote Bookmaker")
    q1 = st.sidebar.number_input("Quota 1", 1.01, 20.0, 2.10)
    qx = st.sidebar.number_input("Quota X", 1.01, 20.0, 3.20)
    q2 = st.sidebar.number_input("Quota 2", 1.01, 20.0, 3.50)
    qu25 = st.sidebar.number_input("Quota Under 2.5", 1.01, 10.0, 1.70)

    st.sidebar.header("2️⃣ Inserisci Micro-Forma (Ultime 4 partite)")
    h_gol_fatti = st.sidebar.number_input("Media Gol Fatti/Partita (CASA)", 0.0, 5.0, 1.2)
    a_gol_fatti = st.sidebar.number_input("Media Gol Fatti/Partita (OSPITE)", 0.0, 5.0, 0.8)

    if st.sidebar.button("🧪 Esegui Reverse Engineering"):
        col1, col2, col3 = st.columns(3)
        
        xg_h_banco, xg_a_banco = estrai_xg_da_quote(q1, qx, q2, qu25)
        
        with col1:
            st.subheader("🕵️‍♂️ Segreti del Banco")
            st.info("L'algoritmo del Bookmaker prevede in realtà questo scenario:")
            st.metric("xG Casa (Bookmaker)", f"{xg_h_banco:.2f}")
            st.metric("xG Trasferta (Bookmaker)", f"{xg_a_banco:.2f}")
            
        peso_banco = 0.70
        peso_forma = 0.30
        
        xg_h_adj = (xg_h_banco * peso_banco) + (h_gol_fatti * peso_forma)
        xg_a_adj = (xg_a_banco * peso_banco) + (a_gol_fatti * peso_forma)
        
        with col2:
            st.subheader("🧬 Modifica Bayesiana")
            st.success("Accelerazione dei dati recenti applicata:")
            st.metric("xG Casa (Nostro)", f"{xg_h_adj:.2f}", f"{(xg_h_adj - xg_h_banco):.2f}")
            st.metric("xG Trasferta (Nostro)", f"{xg_a_adj:.2f}", f"{(xg_a_adj - xg_a_banco):.2f}")
            
        p1_m, px_m, p2_m = poisson_probability_simple(xg_h_adj, xg_a_adj)
        ev_1, ev_x, ev_2 = (p1_m * q1) - 1.0, (px_m * qx) - 1.0, (p2_m * q2) - 1.0
        
        with col3:
            st.subheader("💰 Esito Value Bet")
            st.markdown("Confronto tra le nostre probabilità e il mercato:")
            st.markdown(f"**Segno 1:** Reale {p1_m*100:.1f}% | EV: <span style='color:{'#00FF00' if ev_1>0 else '#FF0000'}'>{ev_1*100:.1f}%</span>", unsafe_allow_html=True)
            st.markdown(f"**Segno X:** Reale {px_m*100:.1f}% | EV: <span style='color:{'#00FF00' if ev_x>0 else '#FF0000'}'>{ev_x*100:.1f}%</span>", unsafe_allow_html=True)
            st.markdown(f"**Segno 2:** Reale {p2_m*100:.1f}% | EV: <span style='color:{'#00FF00' if ev_2>0 else '#FF0000'}'>{ev_2*100:.1f}%</span>", unsafe_allow_html=True)
            
            miglior_bet = max([('1', ev_1), ('X', ev_x), ('2', ev_2)], key=lambda x: x[1])
            if miglior_bet[1] > 0.05:
                st.success(f"🔥 VALUE TROVATA! Giocare Segno {miglior_bet[0]}")
            else:
                st.warning("⛔ Nessun margine di vantaggio.")
                
        st.markdown("---")
        st.subheader("🎯 Griglia Risultati Esatti Previsti (Top 3)")
        st.caption("Calcolati estrapolando la matrice Poissoniana dai nuovi Expected Goals Bayesiani.")
        
        prob_exact = {}
        for i in range(5):
            for j in range(5):
                p_i = (math.exp(-xg_h_adj) * (xg_h_adj ** i)) / math.factorial(i)
                p_j = (math.exp(-xg_a_adj) * (xg_a_adj ** j)) / math.factorial(j)
                prob_exact[f"{i}-{j}"] = p_i * p_j * 100
                
        top_3_scores = sorted(prob_exact.items(), key=lambda item: item[1], reverse=True)[:3]
        
        cr1, cr2, cr3 = st.columns(3)
        cr1.metric(f"Risultato Esatto: {top_3_scores[0][0]}", f"{top_3_scores[0][1]:.1f}%")
        cr2.metric(f"Risultato Esatto: {top_3_scores[1][0]}", f"{top_3_scores[1][1]:.1f}%")
        cr3.metric(f"Risultato Esatto: {top_3_scores[2][0]}", f"{top_3_scores[2][1]:.1f}%")