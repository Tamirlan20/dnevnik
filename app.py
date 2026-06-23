import streamlit as st
import pandas as pd
import sqlite3
import logging
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ И ЛОГИРОВАНИЯ ---
DB_NAME = "focus_space.db"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Критическая ошибка подключения к БД: {e}")
        raise

def init_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Таблица задач
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    notes TEXT,
                    status TEXT NOT NULL DEFAULT 'В процессе',
                    priority TEXT NOT NULL DEFAULT 'Средний ⚡'
                )
            """)
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [col['name'] for col in cursor.fetchall()]
            if 'priority' not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'Средний ⚡'")
                
            # 2. Таблица заметок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes_hub (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tag TEXT
                )
            """)
            
            # 3. Таблица финансов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, 
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL
                )
            """)
                
            # 4. Таблица настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка при инициализации таблиц: {e}")

# --- ОПЕРАЦИИ С ЗАЗАЧАМИ ---
def get_all_tasks_raw():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, category, day_of_week, notes, status, priority FROM tasks")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return []

def get_all_tasks_for_analytics():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category AS [Категория], day_of_week AS [День недели], status AS [Статус], priority AS [Приоритет] FROM tasks")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return []

def add_task(title, category, day_of_week, notes, priority):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, category, day_of_week, notes, status, priority) VALUES (?, ?, ?, ?, 'В процессе', ?)", (title, category, day_of_week, notes, priority))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка добавления задачи: {e}")

def update_task_status(task_id, new_status):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка обновления статуса: {e}")

def delete_task(task_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка удаления задачи: {e}")

# --- ОПЕРАЦИИ С ЗАМЕТКАМИ ---
def get_all_notes():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, created_at, tag FROM notes_hub ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return []

def add_note(title, content, tag):
    try:
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes_hub (title, content, created_at, tag) VALUES (?, ?, ?, ?)", (title, content, current_time, tag))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка добавления заметки: {e}")

def delete_note(note_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes_hub WHERE id = ?", (note_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка удаления заметки: {e}")

# --- ОПЕРАЦИИ С ФИНАНСАМИ ---
def get_all_transactions():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, type, amount, category, description, date FROM finances ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return []

def add_transaction(t_type, amount, category, description):
    try:
        current_date = datetime.now().strftime("%d.%m.%Y")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO finances (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)", (t_type, amount, category, description, current_date))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка транзакции: {e}")

def delete_transaction(t_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM finances WHERE id = ?", (t_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка удаления транзакции: {e}")

# --- ОНБОРДИНГ ---
def is_onboarding_completed():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'onboarding_completed'")
            row = cursor.fetchone()
            return row is not None and row["value"] == "True"
    except sqlite3.Error as e:
        return False

def seed_demo_tour():
    if not is_onboarding_completed():
        add_task("🪐 Развернуть Пространство Фокуса", "Работа", "Понедельник", "Закройте эту задачу для проверки реактивности.", "Высокий 🔥")
        add_note("💡 Первая ментальная искра", "Это пространство заметок. Храните тут свои инсайты и идеи для проектов.", "Идеи")
        add_transaction("Доход", 150000, "Бизнес/SaaS 🚀", "Первая подписка на систему")
        add_transaction("Расход", 12000, "Серверы/IT-Инструменты 🌐", "Оплата облачного хостинга")
        with get_connection() as conn:
            conn.cursor().execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('onboarding_completed', 'True')")
            conn.commit()

# --- ИНИЦИАЛИЗАЦИЯ СТИЛЕЙ СТРАНИЦЫ С ПОЛНОЙ МОБИЛЬНОЙ ОПТИМИЗАЦИЕЙ ---
st.set_page_config(page_title="Пространство Фокуса | SaaS", page_icon="🪐", layout="wide", initial_sidebar_state="auto")
init_db()
seed_demo_tour() 

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* === БАЗОВЫЕ СТИЛИ === */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: radial-gradient(circle at 50% 0%, #1a103c 0%, #0b0f19 60%, #020408 100%) !important;
        color: #f8fafc !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    html, body, [data-testid="stAppViewContainer"], .stApp,
    a, button, input, textarea, select, [role="button"],
    .stSelectbox, div[data-baseweb="select"], .stButton button,
    iframe, [data-testid="stSidebar"], .stTextInput input, .stTextArea textarea {
        cursor: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" fill="url(%23grad)" filter="drop-shadow(0px 0px 3px %233279FF)"/><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:%233279FF;stop-opacity:1" /><stop offset="100%" style="stop-color:%237B3EFF;stop-opacity:1" /></linearGradient></defs></svg>') 7 7, auto !important;
    }

    html {
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch;
        -webkit-text-size-adjust: 100%;
    }

    body {
        overflow-x: hidden !important;
        overflow-y: auto !important;
        min-height: 100vh;
        min-height: 100dvh;
        overscroll-behavior-y: none;
        touch-action: pan-y;
    }

    [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        overflow-y: visible !important;
        min-height: 100vh;
        min-height: 100dvh;
        overscroll-behavior-y: none;
    }

    .stApp {
        overflow: visible !important;
        min-height: 100vh;
        min-height: 100dvh;
        overscroll-behavior-y: none;
    }
    
    /* === САЙДБАР === */
    [data-testid="stSidebar"] {
        background: rgba(11, 15, 25, 0.7) !important;
        backdrop-filter: blur(25px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain;
    }

    [data-testid="stSidebarContent"] {
        overflow: visible !important;
        max-height: none !important;
        height: auto !important;
    }

    [data-testid="stSidebarNav"] {
        overflow: visible !important;
        max-height: none !important;
    }

    [data-testid="stSidebarCollapsedControl"] {
        position: fixed;
        top: 0.75rem;
        left: 0.75rem;
        z-index: 10002;
        touch-action: manipulation;
    }

    [data-testid="stSidebar"] [role="button"],
    [data-testid="stSidebar"] button {
        touch-action: manipulation;
    }

    @media (max-width: 768px) {
        html, body, [data-testid="stAppViewContainer"], .stApp {
            overflow-x: hidden !important;
            overflow-y: auto !important;
            max-height: none !important;
            height: auto !important;
            overscroll-behavior-y: none;
        }

        [data-testid="stSidebar"] {
            max-height: 100dvh;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch;
            touch-action: pan-y;
            overscroll-behavior-y: contain;
        }

        [data-testid="stSidebarContent"],
        [data-testid="stSidebarNav"] {
            max-height: none !important;
            overflow: visible !important;
        }
    }

    @media (max-width: 480px) {
        [data-testid="stSidebarCollapsedControl"] {
            top: 0.5rem;
            left: 0.5rem;
        }
        [data-testid="stSidebar"] {
            max-height: 100dvh;
        }
    }
    
    /* === ЗАГОЛОВКИ === */
    .saas-title {
        background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; letter-spacing: -0.04em; margin-bottom: 5px;
    }
    .saas-subtitle { 
        color: #94a3b8; 
        font-size: 1.05rem; 
        margin-bottom: 35px;
    }
    
    /* === ФОРМЫ (ИСПРАВЛЕНА ОШИБКА СМЕЩЕНИЯ ТЕКСТА) === */
    div[data-testid="stForm"] {
        background: rgba(15, 22, 42, 0.4) !important; 
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important; 
        border-radius: 20px !important; 
        padding: 30px !important;
    }
    
    /* Точечное изменение без ломания внутренних Flexbox-свойств Streamlit */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea, 
    div[data-baseweb="select"] > div {
        background-color: rgba(7, 10, 19, 0.7) !important; 
        color: #ffffff !important;
        font-size: 1rem !important;
        border-radius: 10px !important;
    }
    
    .stTextInput, .stTextArea, .stSelectbox {
        margin-bottom: 16px !important;
    }
    
    /* === КНОПКИ === */
    .stButton button {
        background: rgba(255, 255, 255, 0.07) !important; 
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important; 
        border-radius: 12px !important;
        min-height: 44px !important;
        font-weight: 500 !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        transform: translateY(-1px);
    }
    
    .stFormSubmitButton button { 
        background: linear-gradient(135deg, #3279FF 0%, #7B3EFF 100%) !important;
        min-height: 48px !important;
        font-weight: 600 !important;
    }
    
    /* === KPI КОНТЕЙНЕРЫ === */
    .kpi-container { 
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px; 
        margin-bottom: 25px;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 14px; 
        padding: 16px 20px;
    }
    
    .kpi-val {
        font-size: 1.8rem; 
        font-weight: 700;
        background: linear-gradient(135deg, #3279FF 0%, #a5b4fc 100%); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
    }
    
    /* === КАРТОЧКИ ЗАДАЧ === */
    .task-box {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 18px; 
        padding: 16px 20px; 
        margin-bottom: 12px; 
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .task-completed {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
    }
    
    .task-title {
        font-size: 1.1rem;
        font-weight: 600;
        word-break: break-word;
    }
    
    .task-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    
    /* === КАРТОЧКИ ЗАМЕТОК === */
    .note-box {
        background: linear-gradient(135deg, rgba(123, 62, 255, 0.06) 0%, rgba(15, 23, 42, 0.3) 100%) !important;
        border: 1px solid rgba(123, 62, 255, 0.2) !important; 
        border-radius: 16px; 
        padding: 16px; 
        margin-bottom: 15px;
    }
    
    /* === ФИНАНСОВЫЕ СТРОКИ === */
    .finance-row {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        background: rgba(15, 22, 42, 0.3); 
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 14px 16px; 
        border-radius: 12px; 
        margin-bottom: 8px;
    }
    
    .finance-left {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        flex: 1;
        min-width: 0;
    }
    
    .finance-amount {
        min-width: 120px;
        text-align: right;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    /* === БЕЙДЖИ === */
    .custom-badge {
        background: rgba(15, 23, 42, 0.8); 
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 6px 12px; 
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: 700;
        white-space: nowrap;
    }
    
    /* === ПОМОДОРО КОНТЕЙНЕР === */
    .pomo-container {
        background: rgba(30, 27, 75, 0.4); 
        border: 1px solid rgba(123, 62, 255, 0.2);
        padding: 15px; 
        border-radius: 15px; 
        text-align: center; 
        margin-top: 25px;
    }
    
    .pomo-time { 
        font-size: 2rem; 
        font-weight: 800; 
        color: #ff4b4b; 
        font-family: monospace;
    }
    
    /* === ПРОГРЕСС БАР === */
    .stProgress > div > div > div > div { 
        background: linear-gradient(to right, #3279FF, #7B3EFF) !important; 
    }
    
    /* ========== МОБИЛЬНАЯ ОПТИМИЗАЦИЯ ========== */
    @media (max-width: 768px) {
        .saas-title { font-size: 1.8rem; }
        .saas-subtitle { font-size: 0.9rem; }
        .kpi-container { grid-template-columns: repeat(2, 1fr); }
        .finance-row { flex-direction: column; align-items: flex-start; }
        .finance-amount { text-align: left; min-width: auto; margin-top: 5px; }
    }
    </style>
""", unsafe_allow_html=True)

DAYS_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def pluralize_tasks(n):
    if n % 10 == 1 and n % 100 != 11: return f"{n} задача"
    elif n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]: return f"{n} задачи"
    else: return f"{n} задач"

all_tasks = get_all_tasks_raw()

st.markdown('<div class="saas-title">🪐 Пространство Фокуса</div>', unsafe_allow_html=True)
st.markdown('<p class="saas-subtitle">Интеллектуальный SaaS-хаб управления личной эффективностью, мыслями и бизнес-капиталом</p>', unsafe_allow_html=True)

# --- САЙДБАР: НАВИГАЦИЯ И ПОМОДОРО ---
with st.sidebar:
    section = st.radio("Навигация", ["📝 Мой Планшет", "🧠 База Мыслей", "💰 Финансовый Хаб", "📊 Метрики Продуктивности"])
    
    st.markdown("---")
    st.markdown("### ⏱️ Станция Фокуса (Pomodoro)")
    
    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
    if "pomo_time" not in st.session_state:
        st.session_state.pomo_time = 25 * 60

    if not st.session_state.pomo_running:
        chosen_mins = st.slider("Длительность сессии (мин):", min_value=5, max_value=90, value=int(st.session_state.pomo_time / 60), step=5)
        st.session_state.pomo_time = chosen_mins * 60
    else:
        current_target_mins = int((st.session_state.pomo_time + 59) // 60)
        st.markdown(f"<p style='color: #94a3b8; font-size: 0.85rem;'>Выставленная цель: {current_target_mins} мин.</p>", unsafe_allow_html=True)

    pomo_box = st.empty()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("▶️ Старт", use_container_width=True, disabled=st.session_state.pomo_running):
            st.session_state.pomo_running = True
            st.rerun()
    with col_p2:
        if st.button("⏹️ Сброс", use_container_width=True):
            st.session_state.pomo_running = False
            st.session_state.pomo_time = 25 * 60
            st.rerun()

    if st.session_state.pomo_running and st.session_state.pomo_time > 0:
        mins, secs = divmod(st.session_state.pomo_time, 60)
        pomo_box.markdown("""
        <div class="pomo-container">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: #94a3b8;">Идет сессия фокуса</div>
            <div class="pomo-time">{:02d}:{:02d}</div>
        </div>
        """.format(mins, secs), unsafe_allow_html=True)
        time.sleep(1)
        st.session_state.pomo_time -= 1
        st.rerun()
    else:
        if st.session_state.pomo_time == 0:
            st.session_state.pomo_running = False
            st.toast("🔥 Сессия фокуса завершена!", icon="🔔")
        mins, secs = divmod(st.session_state.pomo_time, 60)
        pomo_box.markdown("""
        <div class="pomo-container">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: #94a3b8;">Статус: Готов к работе</div>
            <div class="pomo-time" style="color: #10b981;">{0:02d}:{1:02d}</div>
        </div>
        """.format(mins, secs), unsafe_allow_html=True)

# РАЗДЕЛ 1: ПЛАНИРОВЩИК ЗАДАЧ
if section == "📝 Мой Планшет":
    total_tasks = len(all_tasks)
    done_tasks = len([t for t in all_tasks if t["status"] == "Выполнено"])
    progress_ratio = done_tasks / total_tasks if total_tasks > 0 else 0.0
    active_tasks = total_tasks - done_tasks
    
    st.markdown("""
    <div class="kpi-container">
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Эффективность Спринта</div>
            <div class="kpi-val">{}%</div>
        </div>
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Завершено</div>
            <div class="kpi-val" style="background: linear-gradient(135deg, #10b981 0%, #6ee7b7 100%); -webkit-background-clip: text;">{} / {}</div>
        </div>
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Активный</div>
            <div class="kpi-val" style="background: linear-gradient(135deg, #f59e0b 0%, #fcd34d 100%); -webkit-background-clip: text;">{}</div>
        </div>
    </div>
    """.format(int(progress_ratio * 100), done_tasks, total_tasks, pluralize_tasks(active_tasks)), unsafe_allow_html=True)
    
    st.markdown('<p style="font-size: 0.9rem; font-weight: 600; color: #a5b4fc; margin-bottom: 5px;">🔥 Прогресс закрытия текущего спринта:</p>', unsafe_allow_html=True)
    st.progress(progress_ratio)
    st.write("")

    with st.form("task_form", clear_on_submit=True):
        task_text = st.text_input("Название фокуса", placeholder="Например: Oтредактировать конфиг")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Сфера", ["Работа", "Личное", "Учёба", "Спорт", "Другое"])
        with col2:
            priority = st.selectbox("Приоритет", ["Высокий 🔥", "Средний ⚡", "Низкий 🎯"])
        
        day_of_week = st.selectbox("Период времени", DAYS_ORDER)
        task_notes = st.text_area("Контекст и спецификации", height=100)
        submitted = st.form_submit_button("Интегрировать в систему", use_container_width=True)
            
    if submitted and task_text.strip():
        add_task(task_text.strip(), category, day_of_week, task_notes.strip(), priority)
        st.rerun()
            
    if all_tasks:
        for t in all_tasks:
            is_done = t['status'] == 'Выполнено'
            box_class = "task-box task-completed" if is_done else "task-box"
            prio = t.get('priority', 'Средний ⚡')
            prio_color = "#f43f5e" if "Высокий" in prio else ("#38bdf8" if "Средний" in prio else "#94a3b8")
            
            with st.container():
                st.markdown(f"""
                <div class="{box_class}">
                    <div class="task-title" style="color: {'#64748b' if is_done else '#ffffff'}; text-decoration: {'line-through' if is_done else 'none'};">
                        {t['title']}
                    </div>
                    <div class="task-badges">
                        <span class="custom-badge" style="border-color: {prio_color}; color: {prio_color};">🚨 {prio}</span>
                        <span class="custom-badge" style="border-color: rgba(50, 121, 255, 0.4); color: #60a5fa;">🏷️ {t['category']}</span>
                        <span class="custom-badge" style="border-color: rgba(123, 62, 255, 0.4); color: #c084fc;">📅 {t['day_of_week']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if t["status"] == "В процессе":
                        if st.button("✅ Закрыть", key=f"done_{t['id']}", use_container_width=True):
                            update_task_status(t['id'], "Выполнено")
                            st.rerun()
                    else:
                        st.markdown('<p style="color: #4ade80; font-weight: 700; text-align: center; margin-top: 8px;">✓ Выполнено</p>', unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️ Удалить", key=f"del_{t['id']}", use_container_width=True):
                        delete_task(t['id'])
                        st.rerun()
                
                with col3:
                    if t.get("notes"):
                        if st.button("📖 Спец.", key=f"exp_{t['id']}", use_container_width=True):
                            st.info(t["notes"])
                
                st.write("")

# РАЗДЕЛ 2: БАЗА МЫСЛЕЙ
elif section == "🧠 База Мыслей":
    st.markdown('<p style="font-size: 1.35rem; font-weight: 600; color: #fff;">🧠 Ментальное Хранилище</p>', unsafe_allow_html=True)
    
    with st.form("note_form", clear_on_submit=True):
        note_title = st.text_input("Заголовок мысли / идеи", placeholder="Например: Архитектурные паттерны")
        note_tag = st.selectbox("Тег группы", ["Идеи", "Инсайты", "Учёба", "Проекты", "Разное"])
        note_content = st.text_area("Ваш text (поддерживает Markdown)", height=120)
        note_submitted = st.form_submit_button("Зафиксировать мысль", use_container_width=True)
        
    if note_submitted and note_content.strip():
        add_note(note_title.strip() if note_title.strip() else "Без заголовка", note_content.strip(), note_tag)
        st.rerun()
        
    saved_notes = get_all_notes()
    if saved_notes:
        for note in saved_notes:
            with st.container():
                st.markdown(f"""
                <div class="note-box">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;">
                        <span style="font-size: 1.1rem; font-weight: 700; color: #a5b4fc; word-break: break-word;">{note['title']}</span>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                            <span class="custom-badge" style="border-color: rgba(165, 180, 252, 0.4); color: #e2e8f0;">🕒 {note['created_at']}</span>
                            <span class="custom-badge" style="border-color: #7B3EFF; color: #c084fc;">📌 {note['tag']}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(note['content'])
                
                if st.button("🗑️ Стереть заметку", key=f"del_note_{note['id']}", use_container_width=True):
                    delete_note(note['id'])
                    st.rerun()
                
                st.write("")
    else:
        st.info("💡 Записей еще нет. Создайте первую выше!")

# РАЗДЕЛ 3: ФИНАНСОВЫЙ ХАБ
elif section == "💰 Финансовый Хаб":
    st.markdown('<p style="font-size: 1.35rem; font-weight: 600; color: #fff;">💰 Финансовый Учет и Управление</p>', unsafe_allow_html=True)
    
    transactions = get_all_transactions()
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'Доход')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'Расход')
    current_balance = total_income - total_expense
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Баланс</div>
            <div class="kpi-val" style="background: linear-gradient(135deg, #10b981 0%, #34d399 100%); -webkit-background-clip: text;">{current_balance:,.0f} ₸</div>
        </div>
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Поступл.</div>
            <div class="kpi-val" style="background: linear-gradient(135deg, #3279FF 0%, #60a5fa 100%); -webkit-background-clip: text;">{total_income:,.0f} ₸</div>
        </div>
        <div class="kpi-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Траты</div>
            <div class="kpi-val" style="background: linear-gradient(135deg, #f43f5e 0%, #fb7185 100%); -webkit-background-clip: text;">{total_expense:,.0f} ₸</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("finance_form", clear_on_submit=True):
        t_type = st.radio("Тип операции", ["Доход", "Расход"], horizontal=True)
        amount = st.number_input("Сумма (₸)", min_value=0.0, value=0.0, step=1000.0)
        category = st.selectbox("Выбор категории", ["Бизнес/SaaS 🚀", "Серверы/IT-Инструменты 🌐", "Маркетинг 📊", "Личное 🍕", "Другое 💎"])
        category = st.selectbox("Выбор категории", ["Серверы/IT-Инструменты 🌐", "Еда/Продукты 🍕", "Спорт/Здоровье 🏋️", "Обучение 📚", "Развлечения/Отдых 🎮", "Долги/Кредиты 💸", "Другое 🎰"])
        description = st.text_input("Комментарий", placeholder="Например: Покупка серверов...")
        fin_submitted = st.form_submit_button("Зарегистрировать операцию", use_container_width=True)
        
    if fin_submitted and amount > 0:
        add_transaction(t_type, amount, category, description.strip())
        st.rerun()
        
    if transactions:
        st.markdown('### 📜 История транзакций')
        for t in transactions:
            color = "#10b981" if t['type'] == "Доход" else "#f43f5e"
            prefix = "+" if t['type'] == "Доход" else "-"
            
            with st.container():
                st.markdown(f"""
                <div class="finance-row">
                    <div class="finance-left">
                        <span class="custom-badge" style="border-color: {color}; color: {color};">{t['type']}</span>
                        <span style="font-weight: 600; font-size: 1rem;">{t['category']}</span>
                        <span style="color: #94a3b8; font-size: 0.85rem;">— {t['description']}</span>
                    </div>
                    <div class="finance-amount" style="color: {color};">
                        {prefix}{t['amount']:,.0f} ₸
                        <div style="font-size: 0.7rem; color: #64748b; font-weight: 400;">{t['date']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🗑️ Удалить транзакцию", key=f"del_fin_{t['id']}", use_container_width=True):
                    delete_transaction(t['id'])
                    st.rerun()
                st.write("")
    else:
        st.info("💰 Транзакции отсутствуют. Внесите данные выше.")

# РАЗДЕЛ 4: МЕТРИКИ ПРОДУКТИВНОСТИ
elif section == "📊 Метрики Продуктивности":
    st.markdown('<p style="font-size: 1.35rem; font-weight: 600; color: #fff;">📊 Метрики Продуктивности спринта</p>', unsafe_allow_html=True)
    
    analytics_data = get_all_tasks_for_analytics()
    if analytics_data:
        df = pd.DataFrame(analytics_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🎯 Распределение задач по сферам")
            if "Категория" in df.columns:
                cat_chart = df["Категория"].value_counts()
                st.bar_chart(cat_chart)
                
        with col2:
            st.markdown("#### ⚡ Статусы выполнения")
            if "Статус" in df.columns:
                status_chart = df["Статус"].value_counts()
                st.bar_chart(status_chart)
                
        st.markdown("#### 📋 Общая таблица активностей")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("📊 База данных пуста. Наполните «Мой Планшет» задачами для генерации аналитики.")