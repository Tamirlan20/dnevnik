import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime

# --- 1. МОБИЛЬНАЯ ОПТИМИЗАЦИЯ И НАСТРОЙКИ ---
st.set_page_config(page_title="Focus Space", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Блокировка свайп-обновления и прыжков */
        html, body { overscroll-behavior-y: contain; overflow: hidden; height: 100%; }
        .stApp { height: 100vh; overflow-y: auto; }
        
        /* Темная тема и шрифты */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 50% 0%, #1a103c 0%, #0b0f19 60%, #020408 100%) !important;
            color: #f8fafc !important;
            font-family: 'Inter', sans-serif !important;
        }
        .saas-title { background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.2rem; }
        .kpi-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 15px; margin-bottom: 10px; }
        .kpi-val { font-size: 1.5rem; font-weight: 700; color: #a5b4fc; }
    </style>
""", unsafe_allow_html=True)

# --- 2. БАЗА ДАННЫХ ---
DB_NAME = "focus_space.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, day_of_week TEXT, notes TEXT, status TEXT DEFAULT 'В процессе', priority TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS notes_hub (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at TEXT, tag TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS finances (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, amount REAL, category TEXT, description TEXT, date TEXT)")
        conn.commit()

init_db()

# --- 3. ФУНКЦИИ ---
def get_all_tasks():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM tasks")]

# --- 4. ИНТЕРФЕЙС ---
st.markdown('<div class="saas-title">🪐 Пространство Фокуса</div>', unsafe_allow_html=True)

# Навигация (используем selectbox для экономии места на мобильных)
section = st.selectbox("Раздел:", ["📝 Планшет", "🧠 База Мыслей", "💰 Финансы", "📊 Метрики"])

if section == "📝 Планшет":
    st.subheader("Мои задачи")
    task = st.text_input("Название задачи")
    if st.button("Добавить"):
        with get_connection() as conn:
            conn.execute("INSERT INTO tasks (title, category) VALUES (?, ?)", (task, "Работа"))
            conn.commit()
            st.rerun()
    
    tasks = get_all_tasks()
    for t in tasks:
        st.info(f"{t['title']}")

elif section == "💰 Финансы":
    st.subheader("Финансы")
    f_type = st.radio("Тип:", ["Доход", "Расход"], horizontal=True)
    amt = st.number_input("Сумма", min_value=0.0)
    if st.button("Провести"):
        with get_connection() as conn:
            conn.execute("INSERT INTO finances (type, amount, category, date) VALUES (?, ?, ?, ?)", 
                         (f_type, amt, "Разное", datetime.now().strftime("%d.%m.%Y")))
            conn.commit()
            st.rerun()

elif section == "📊 Метрики":
    st.subheader("Дашборд")
    tx_data = pd.read_sql("SELECT * FROM finances", get_connection())
    if not tx_data.empty:
        st.bar_chart(tx_data.groupby("type")["amount"].sum())

# ... (Здесь ты можешь добавить остальные свои функции из длинного кода)