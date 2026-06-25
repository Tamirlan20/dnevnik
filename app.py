import streamlit as st
import pandas as pd
import sqlite3
import logging
import time
import random
import hashlib
from datetime import datetime, timedelta, date
import json
import calendar
import numpy as np

# ====================================================
# КОНФИГУРАЦИЯ
# ====================================================
DB_NAME = "focus_space_enhanced.db"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ====================================================
# НОВЫЕ ТАБЛИЦЫ ДЛЯ РАСШИРЕННОГО ФУНКЦИОНАЛА
# ====================================================

def init_db_enhanced():
    with get_connection() as conn:
        c = conn.cursor()

        # ✨ DECISION JOURNAL - журнал решений
        c.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            context TEXT,
            options TEXT NOT NULL,
            choice TEXT NOT NULL,
            reasoning TEXT,
            expected_outcome TEXT,
            review_date TEXT,
            actual_outcome TEXT,
            impact_score INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )""")

        # ✨ DISTRACTION LOG - логирование отвлечений
        c.execute("""CREATE TABLE IF NOT EXISTS distractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            distraction_type TEXT NOT NULL,
            description TEXT,
            duration_minutes INTEGER,
            severity INTEGER DEFAULT 5,
            task_interrupted INTEGER,
            recovery_minutes INTEGER DEFAULT 0
        )""")

        # ✨ SKILL TREE - развитие навыков
        c.execute("""CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            description TEXT,
            resources TEXT DEFAULT '',
            created_date TEXT NOT NULL,
            target_level INTEGER DEFAULT 5
        )""")

        # ✨ SKILL LOGS - логирование практики навыков
        c.execute("""CREATE TABLE IF NOT EXISTS skill_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            practice_minutes INTEGER,
            notes TEXT,
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )""")

        # ✨ FOCUS FLOW STATE - состояние потока
        c.execute("""CREATE TABLE IF NOT EXISTS focus_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            interruptions INTEGER DEFAULT 0,
            satisfaction INTEGER DEFAULT 5,
            task_id INTEGER,
            notes TEXT
        )""")

        # ✨ POMODORO QUEUE - очередь задач
        c.execute("""CREATE TABLE IF NOT EXISTS pomodoro_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            position INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )""")

        # ✨ SHUTDOWN RITUAL - ритуал завершения дня
        c.execute("""CREATE TABLE IF NOT EXISTS shutdown_rituals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            reflection TEXT,
            wins TEXT,
            tomorrow_focus TEXT,
            completed_checklist TEXT DEFAULT '[]',
            duration_minutes INTEGER DEFAULT 15,
            satisfaction INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )""")

        # ✨ WEEKLY COMMITMENT - еженедельные обязательства
        c.execute("""CREATE TABLE IF NOT EXISTS weekly_commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'Средний',
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )""")

        # ✨ SYNERGY ANALYSIS - анализ синергии
        c.execute("""CREATE TABLE IF NOT EXISTS synergies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task1_id INTEGER NOT NULL,
            task2_id INTEGER NOT NULL,
            synergy_level INTEGER DEFAULT 5,
            description TEXT,
            UNIQUE(task1_id, task2_id)
        )""")

        # ✨ RECOVERY TRACKING - отслеживание восстановления
        c.execute("""CREATE TABLE IF NOT EXISTS recovery_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            duration_minutes INTEGER,
            energy_before INTEGER,
            energy_after INTEGER,
            notes TEXT
        )""")

        conn.commit()

# ====================================================
# DATABASE CONNECTION (from original)
# ====================================================

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Ошибка подключения к БД: {e}")
        raise

# ====================================================
# DECISION JOURNAL - Журнал решений
# ====================================================

def add_decision(title, context, options, choice, reasoning, expected_outcome):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO decisions 
                (title, context, options, choice, reasoning, expected_outcome, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, context, json.dumps(options, ensure_ascii=False), choice, reasoning, 
                 expected_outcome, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_all_decisions():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM decisions ORDER BY created_at DESC LIMIT 50")
            return [dict(row) for row in c.fetchall()]
    except: return []

def review_decision(decision_id, actual_outcome, impact_score):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE decisions SET actual_outcome=?, impact_score=?, review_date=? WHERE id=?",
                (actual_outcome, impact_score, datetime.now().strftime("%Y-%m-%d"), decision_id))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# DISTRACTION TRACKER - Логирование отвлечений
# ====================================================

def log_distraction(distraction_type, description, duration_minutes, severity):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO distractions 
                (timestamp, distraction_type, description, duration_minutes, severity)
                VALUES (?, ?, ?, ?, ?)""",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), distraction_type, description, 
                 duration_minutes, severity))
            conn.commit()
    except Exception as e: logging.error(e)

def get_distractions_today():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT * FROM distractions WHERE timestamp LIKE ? ORDER BY timestamp DESC", 
                (f"{today}%",))
            return [dict(row) for row in c.fetchall()]
    except: return []

def get_distraction_stats(days=7):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("""SELECT distraction_type, COUNT(*) as count, SUM(duration_minutes) as total_time
                FROM distractions WHERE timestamp >= ? GROUP BY distraction_type""", (start,))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# SKILL TREE - Дерево развития навыков
# ====================================================

def add_skill(name, category, target_level=5):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO skills (name, category, target_level, created_date)
                VALUES (?, ?, ?, ?)""",
                (name, category, target_level, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_all_skills():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM skills ORDER BY category")
            return [dict(row) for row in c.fetchall()]
    except: return []

def log_skill_practice(skill_id, practice_minutes, notes=''):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("""INSERT OR REPLACE INTO skill_logs (skill_id, date, practice_minutes, notes)
                VALUES (?, ?, ?, ?)""",
                (skill_id, today, practice_minutes, notes))
            
            # Обновить прогресс навыка
            c.execute("SELECT COUNT(*) as cnt FROM skill_logs WHERE skill_id=?", (skill_id,))
            practice_count = c.fetchone()['cnt']
            level = 1 + (practice_count // 10)  # Уровень растёт каждые 10 сессий
            progress = (practice_count % 10) * 10
            
            conn.execute("UPDATE skills SET level=?, progress=? WHERE id=?", (level, progress, skill_id))
            conn.commit()
    except Exception as e: logging.error(e)

def get_skill_stats(skill_id, days=30):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("""SELECT date, practice_minutes FROM skill_logs 
                WHERE skill_id=? AND date>=? ORDER BY date""", (skill_id, start))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# FOCUS FLOW STATE - Состояние потока
# ====================================================

def start_focus_session(task_id=None):
    try:
        with get_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            now = datetime.now().strftime("%H:%M")
            conn.execute("""INSERT INTO focus_flow (date, start_time, task_id, end_time)
                VALUES (?, ?, ?, ?)""",
                (today, now, task_id, now))
            conn.commit()
            return True
    except: return False

def end_focus_session(interruptions, satisfaction, notes=''):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            now = datetime.now().strftime("%H:%M")
            
            c.execute("SELECT id FROM focus_flow WHERE date=? ORDER BY id DESC LIMIT 1", (today,))
            row = c.fetchone()
            if row:
                conn.execute("""UPDATE focus_flow SET end_time=?, interruptions=?, satisfaction=?, notes=?
                    WHERE id=?""", (now, interruptions, satisfaction, notes, row['id']))
                conn.commit()
                return True
    except: return False

def get_focus_sessions(days=14):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("SELECT * FROM focus_flow WHERE date>=? ORDER BY date DESC", (start,))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# POMODORO QUEUE - Очередь задач
# ====================================================

def add_to_pomodoro_queue(task_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM pomodoro_queue WHERE status='pending'")
            position = c.fetchone()['cnt'] + 1
            conn.execute("""INSERT INTO pomodoro_queue (task_id, position, created_at)
                VALUES (?, ?, ?)""",
                (task_id, position, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_pomodoro_queue():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT pq.*, t.title FROM pomodoro_queue pq 
                LEFT JOIN tasks t ON pq.task_id = t.id 
                WHERE pq.status='pending' ORDER BY pq.position""")
            return [dict(row) for row in c.fetchall()]
    except: return []

def remove_from_queue(queue_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM pomodoro_queue WHERE id=?", (queue_id,))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# SHUTDOWN RITUAL - Ритуал завершения дня
# ====================================================

def save_shutdown_ritual(reflection, wins, tomorrow_focus, completed_checklist, satisfaction):
    try:
        with get_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("""INSERT OR REPLACE INTO shutdown_rituals 
                (date, reflection, wins, tomorrow_focus, completed_checklist, satisfaction, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (today, reflection, wins, tomorrow_focus, json.dumps(completed_checklist, ensure_ascii=False),
                 satisfaction, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_shutdown_ritual(date_str=None):
    try:
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM shutdown_rituals WHERE date=?", (date_str,))
            row = c.fetchone()
            return dict(row) if row else None
    except: return None

# ====================================================
# WEEKLY COMMITMENTS - Еженедельные обязательства
# ====================================================

def get_week_start(date_obj=None):
    if not date_obj:
        date_obj = datetime.now()
    return (date_obj - timedelta(days=date_obj.weekday())).strftime("%Y-%m-%d")

def add_weekly_commitment(title, description, priority='Средний'):
    try:
        with get_connection() as conn:
            week_start = get_week_start()
            conn.execute("""INSERT INTO weekly_commitments 
                (week_start, title, description, priority, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (week_start, title, description, priority, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_weekly_commitments():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            week_start = get_week_start()
            c.execute("""SELECT * FROM weekly_commitments WHERE week_start=? ORDER BY priority DESC, id""",
                (week_start,))
            return [dict(row) for row in c.fetchall()]
    except: return []

def update_commitment_progress(commit_id, progress):
    try:
        with get_connection() as conn:
            status = "1" if progress >= 100 else "0"
            conn.execute("UPDATE weekly_commitments SET progress=?, completed=? WHERE id=?",
                (progress, status, commit_id))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# RECOVERY TRACKING - Отслеживание восстановления
# ====================================================

def log_recovery_session(recovery_type, duration_minutes, energy_before, energy_after, notes=''):
    try:
        with get_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("""INSERT INTO recovery_sessions 
                (date, type, duration_minutes, energy_before, energy_after, notes)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (today, recovery_type, duration_minutes, energy_before, energy_after, notes))
            conn.commit()
    except Exception as e: logging.error(e)

def get_recovery_impact():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("""SELECT type, COUNT(*) as count, AVG(energy_after - energy_before) as avg_boost
                FROM recovery_sessions WHERE date=? GROUP BY type""", (today,))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# SYNERGY ANALYSIS - Анализ синергии
# ====================================================

def analyze_task_synergy(task1_id, task2_id, synergy_level, description=''):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT OR REPLACE INTO synergies 
                (task1_id, task2_id, synergy_level, description)
                VALUES (?, ?, ?, ?)""",
                (task1_id, task2_id, synergy_level, description))
            conn.commit()
    except Exception as e: logging.error(e)

def get_task_synergies(task_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT * FROM synergies 
                WHERE task1_id=? OR task2_id=? ORDER BY synergy_level DESC""",
                (task_id, task_id))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# SMART RECOMMENDATIONS ENGINE
# ====================================================

def generate_smart_recommendations():
    """Анализирует данные и выдаёт умные рекомендации"""
    recommendations = []
    
    # Анализ отвлечений
    distractions = get_distraction_stats(7)
    if distractions:
        total_distraction_time = sum(d['total_time'] or 0 for d in distractions)
        if total_distraction_time > 120:  # более 2 часов в неделю
            top_distraction = max(distractions, key=lambda x: x['total_time'] or 0)
            recommendations.append({
                'type': 'distraction',
                'severity': 'high',
                'icon': '⚠️',
                'title': f'Высокие отвлечения: {top_distraction["distraction_type"]}',
                'description': f'В неделю вы потеряли {total_distraction_time:.0f} минут. Используйте режим "Do Not Disturb".',
                'color': '#f43f5e'
            })
    
    # Анализ качества фокуса
    focus_sessions = get_focus_sessions(7)
    if focus_sessions:
        avg_satisfaction = sum(s['satisfaction'] for s in focus_sessions) / len(focus_sessions)
        avg_interruptions = sum(s['interruptions'] for s in focus_sessions) / len(focus_sessions)
        if avg_interruptions > 3:
            recommendations.append({
                'type': 'focus_quality',
                'severity': 'medium',
                'icon': '🎯',
                'title': 'Улучшите качество фокуса',
                'description': f'Среднее количество перерывов: {avg_interruptions:.1f}. Попробуйте более длительные сессии.',
                'color': '#f59e0b'
            })
    
    # Анализ навыков
    skills = get_all_skills()
    stagnant_skills = [s for s in skills if s['progress'] == 0]
    if stagnant_skills:
        recommendations.append({
            'type': 'skill_development',
            'severity': 'low',
            'icon': '🌱',
            'title': f'Продолжите развитие навыков',
            'description': f'Вы не практиковали {len(stagnant_skills)} навыков на этой неделе.',
            'color': '#22c55e'
        })
    
    return recommendations

# ====================================================
# STYLES & CONFIG
# ====================================================

DAYS_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MOOD_EMOJIS = {1:"😞", 2:"😟", 3:"😐", 4:"🙂", 5:"😊", 6:"😄", 7:"🌟", 8:"🚀", 9:"🔥", 10:"⚡"}
ENERGY_EMOJIS = {1:"🪫", 2:"😴", 3:"😑", 4:"🌿", 5:"💡", 6:"⚡", 7:"🔥", 8:"💪", 9:"🦁", 10:"🌋"}

st.set_page_config(page_title="Пространство Фокуса 2.0+", page_icon="🪐", layout="wide", initial_sidebar_state="auto")

# ====================================================
# СТИЛИ
# ====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: radial-gradient(circle at 50% 0%, #1a103c 0%, #0b0f19 60%, #020408 100%) !important;
    color: #f8fafc !important;
    font-family: 'Inter', sans-serif !important;
}

.saas-title {
    background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800; font-size: 2.6rem; letter-spacing: -0.04em; margin-bottom: 4px;
}

.section-title { font-size: 1.25rem; font-weight: 700; color: #fff; margin: 8px 0 16px 0; display: flex; align-items: center; gap: 8px; }

.card-enhanced {
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 16px; margin-bottom: 12px;
}

.insight-box {
    background: linear-gradient(135deg, rgba(50,121,255,0.06), rgba(123,62,255,0.06));
    border: 1px solid rgba(50,121,255,0.2);
    border-radius: 12px; padding: 14px 18px; margin: 12px 0;
}

.skill-level {
    display: inline-block; width: 20px; height: 20px;
    border-radius: 50%; background: linear-gradient(135deg, #3279FF, #7B3EFF);
    color: white; font-weight: 700; font-size: 12px;
    display: flex; align-items: center; justify-content: center;
}

.recovery-badge {
    background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(15,23,42,0.3));
    border: 1px solid rgba(16,185,129,0.2); border-radius: 10px;
    padding: 10px 12px; margin-bottom: 8px; font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ====================================================
# ИНИЦИАЛИЗАЦИЯ БД
# ====================================================

init_db_enhanced()

# ====================================================
# HEADER
# ====================================================

st.markdown('<div class="saas-title">🪐 Пространство Фокуса 2.0+</div>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8; font-size:0.95rem;">Система управления жизнью нового поколения с AI-помощником</p>', unsafe_allow_html=True)

# ====================================================
# САЙДБАР
# ====================================================

with st.sidebar:
    st.markdown('<div style="font-size:0.7rem; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;">✨ Навигация</div>', unsafe_allow_html=True)
    section = st.radio("", [
        "📊 Главная панель",
        "📝 Планшет задач",
        "⏰ Тайм-блокинг",
        "🍅 Очередь Pomodoro",
        "🧠 Brain Dump",
        "😊 Дневник настроения",
        "✅ Привычки",
        "🎯 Цели",
        "🌳 Дерево навыков",
        "🧩 База мыслей",
        "💰 Финансы",
        "🔄 Ретроспектива",
        "📋 Журнал решений",
        "📉 Отвлечения",
        "⚡ Состояние потока",
        "💤 Ритуал завершения",
        "📈 Умные рекомендации",
        "📊 Полная аналитика",
    ], label_visibility="collapsed")

    st.markdown("---")
    
    # Умные рекомендации в сайдбаре
    smart_recs = generate_smart_recommendations()
    if smart_recs:
        st.markdown('<div style="font-size:0.7rem; color:#a5b4fc; font-weight:700; margin-bottom:8px;">💡 Умные советы</div>', unsafe_allow_html=True)
        for rec in smart_recs[:2]:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border-left:3px solid {rec['color']};
                border-radius:0 8px 8px 0; padding:8px 10px; margin-bottom:8px; font-size:0.75rem;">
                <div style="color:{rec['color']}; font-weight:700;">{rec['icon']} {rec['title']}</div>
                <div style="color:#94a3b8; margin-top:3px;">{rec['description']}</div>
            </div>""", unsafe_allow_html=True)

# ====================================================
# РАЗДЕЛ: ГЛАВНАЯ ПАНЕЛЬ (НОВАЯ)
# ====================================================

if section == "📊 Главная панель":
    st.markdown('<div class="section-title">📊 Ваша производительность сегодня</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        today_mood = None
        try:
            with get_connection() as conn:
                c = conn.cursor()
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute("SELECT mood FROM mood_journal WHERE date=?", (today,))
                row = c.fetchone()
                if row: today_mood = row['mood']
        except: pass
        mood_emoji = MOOD_EMOJIS.get(today_mood, "😐") if today_mood else "❓"
        st.metric("😊 Настроение", mood_emoji, "Обновить" if not today_mood else "✓")
    
    with col2:
        commitments = get_weekly_commitments()
        completed = len([c for c in commitments if c['completed']])
        st.metric("🎯 Обязательства", f"{completed}/{len(commitments)}", f"+{completed}")
    
    with col3:
        focus_sess = get_focus_sessions(1)
        st.metric("⚡ Сессии фокуса", len(focus_sess), "Начать новую")
    
    with col4:
        distractions_today = get_distractions_today()
        total_distraction = sum(d['duration_minutes'] or 0 for d in distractions_today)
        st.metric("⚠️ Отвлечения", f"{total_distraction} мин", f"{len(distractions_today)} раз")
    
    # Еженедельные обязательства
    st.markdown("### 🎯 Обязательства на неделю")
    commitments = get_weekly_commitments()
    if commitments:
        for commit in commitments:
            prio_color = {"Высокий": "#f43f5e", "Средний": "#f59e0b", "Низкий": "#94a3b8"}.get(commit['priority'], '#94a3b8')
            with st.container():
                st.markdown(f"""
                <div class="card-enhanced">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
                        <div style="font-weight:600; color:#fff;">{commit['title']}</div>
                        <span class="badge" style="border-color:{prio_color}; color:{prio_color};">{commit['priority']}</span>
                    </div>
                    <div style="background:rgba(0,0,0,0.3); border-radius:4px; height:6px;">
                        <div style="width:{commit['progress']}%; height:6px; background:{prio_color}; border-radius:4px;"></div>
                    </div>
                </div>""", unsafe_allow_html=True)
                
                c1, c2 = st.columns([3, 1])
                with c1:
                    new_prog = st.slider("Прогресс", 0, 100, commit['progress'], key=f"cp_{commit['id']}")
                with c2:
                    if st.button("💾", key=f"cs_{commit['id']}", use_container_width=True):
                        update_commitment_progress(commit['id'], new_prog)
                        st.rerun()
    else:
        with st.expander("➕ Добавить обязательства на неделю"):
            with st.form("weekly_commitment_form"):
                title = st.text_input("Название обязательства", placeholder="Завершить квартальный проект")
                desc = st.text_area("Описание", height=60)
                priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                if st.form_submit_button("✅ Добавить"):
                    add_weekly_commitment(title, desc, priority)
                    st.rerun()
    
    # Ритуал завершения дня
    st.markdown("---")
    st.markdown("### 💤 Ритуал завершения дня")
    
    shutdown = get_shutdown_ritual()
    if shutdown:
        st.success(f"✅ Ритуал завершения уже проведён: {shutdown['date']}")
        st.info(f"Завтрашний фокус: {shutdown['tomorrow_focus']}")
    else:
        with st.form("shutdown_form"):
            reflection = st.text_area("📝 Рефлексия дня", placeholder="Что произошло, как я себя чувствую...")
            wins = st.text_area("🏆 Мои победы", placeholder="Что удалось сделать хорошего...")
            tomorrow_focus = st.text_area("🎯 Фокус на завтра", placeholder="Что самое важное завтра...")
            satisfaction = st.slider("😊 Удовлетворённость днём", 1, 10, 7)
            
            if st.form_submit_button("💾 Сохранить ритуал завершения"):
                save_shutdown_ritual(reflection, wins, tomorrow_focus, [], satisfaction)
                st.toast("✅ Ритуал завершения дня сохранён!")
                st.rerun()

# ====================================================
# РАЗДЕЛ: ОЧЕРЕДЬ POMODORO (НОВАЯ)
# ====================================================

elif section == "🍅 Очередь Pomodoro":
    st.markdown('<div class="section-title">🍅 Очередь задач для Pomodoro</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="insight-box">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            🎯 <strong>Очередь Pomodoro</strong> — план задач на сегодняшние сессии.
            Добавляйте задачи в очередь и выполняйте их по одной за каждый Pomodoro.
        </div>
    </div>""", unsafe_allow_html=True)
    
    # Добавить в очередь
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, title FROM tasks WHERE status='В процессе' LIMIT 20")
            open_tasks = [dict(row) for row in c.fetchall()]
    except: open_tasks = []
    
    if open_tasks:
        with st.form("add_to_queue_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                task_opt = st.selectbox("Выберите задачу", [f"{t['title'][:50]}" for t in open_tasks])
            with col2:
                if st.form_submit_button("➕ В очередь", use_container_width=True):
                    task_id = open_tasks[[f"{t['title'][:50]}" for t in open_tasks].index(task_opt)]['id']
                    add_to_pomodoro_queue(task_id)
                    st.toast("✅ Задача добавлена в очередь!")
                    st.rerun()
    
    # Показать очередь
    queue = get_pomodoro_queue()
    if queue:
        st.markdown(f"### 📋 В очереди: {len(queue)} задач")
        
        for i, item in enumerate(queue, 1):
            st.markdown(f"""
            <div class="card-enhanced" style="background:linear-gradient(135deg, rgba(123,62,255,0.08), rgba(15,23,42,0.3));">
                <div style="display:flex; gap:12px; align-items:start;">
                    <div style="font-size:1.4rem; font-weight:800; color:#7B3EFF; min-width:30px;">
                        #{i}
                    </div>
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:600; color:#fff; word-break:break-word;">🍅 {item.get('title', 'Задача')}</div>
                        <div style="font-size:0.8rem; color:#94a3b8; margin-top:4px;">
                            Добавлено: {item['created_at']}
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("▶️ Начать сессию", key=f"start_pom_{item['id']}", use_container_width=True):
                    st.info(f"🍅 Начните Pomodoro для: {item.get('title', 'Задача')}")
            with c2:
                if st.button("✓ Выполнено", key=f"done_pom_{item['id']}", use_container_width=True):
                    remove_from_queue(item['id'])
                    st.toast(f"✅ {item.get('title', 'Задача')} завершена!")
                    st.rerun()
    else:
        st.info("📭 Очередь пуста. Добавьте задачи выше!")

# ====================================================
# РАЗДЕЛ: ДЕРЕВО НАВЫКОВ
# ====================================================

elif section == "🌳 Дерево навыков":
    st.markdown('<div class="section-title">🌳 Дерево развития навыков</div>', unsafe_allow_html=True)
    
    skills = get_all_skills()
    
    with st.form("add_skill_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            skill_name = st.text_input("Навык", placeholder="Python, Лидерство, Дизайн...")
        with col2:
            skill_category = st.selectbox("Категория", ["Техническое", "Софт скиллы", "Здоровье", "Спорт", "Творчество", "Другое"])
        with col3:
            target_level = st.slider("Целевой уровень", 1, 10, 5)
        
        if st.form_submit_button("🌱 Добавить навык", use_container_width=True):
            if skill_name.strip():
                add_skill(skill_name.strip(), skill_category, target_level)
                st.rerun()
    
    if skills:
        # Группировать по категориям
        by_category = {}
        for skill in skills:
            cat = skill['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(skill)
        
        for category, cat_skills in by_category.items():
            st.markdown(f"### 📚 {category}")
            
            for skill in cat_skills:
                stats = get_skill_stats(skill['id'], 30)
                total_practice = sum(s['practice_minutes'] for s in stats) if stats else 0
                
                progress_pct = (skill['progress']) * 10
                
                st.markdown(f"""
                <div class="card-enhanced">
                    <div style="display:flex; justify-content:space-between; align-items:start; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
                        <div>
                            <div style="font-weight:600; color:#fff; font-size:1.05rem;">{skill['name']}</div>
                            <div style="font-size:0.8rem; color:#94a3b8; margin-top:3px;">
                                Уровень {skill['level']}/{skill['target_level']} | 
                                Практика: {total_practice} мин/месяц
                            </div>
                        </div>
                        <div style="text-align:center;">
                            <div class="skill-level">{skill['level']}</div>
                        </div>
                    </div>
                    <div style="background:rgba(0,0,0,0.3); border-radius:4px; height:6px; margin-bottom:8px;">
                        <div style="width:{progress_pct}%; height:6px; background:linear-gradient(90deg,#3279FF,#7B3EFF); border-radius:4px;"></div>
                    </div>
                </div>""", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    minutes = st.number_input("Минут практики", 0, 240, 30, key=f"skill_min_{skill['id']}")
                with col2:
                    notes = st.text_input("Заметки", key=f"skill_notes_{skill['id']}")
                with col3:
                    if st.button("📝 Записать", key=f"skill_log_{skill['id']}", use_container_width=True):
                        log_skill_practice(skill['id'], minutes, notes)
                        st.rerun()
    else:
        st.info("🌱 Нет навыков. Добавьте первый!")

# ====================================================
# РАЗДЕЛ: ЖУРНАЛ РЕШЕНИЙ
# ====================================================

elif section == "📋 Журнал решений":
    st.markdown('<div class="section-title">📋 Журнал решений и их влияние</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="insight-box">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            📋 <strong>Журнал решений</strong> помогает отслеживать ключевые выборы, их последствия и учиться на опыте.
        </div>
    </div>""", unsafe_allow_html=True)
    
    with st.form("decision_form"):
        title = st.text_input("Описание решения *", placeholder="Выбрать новый фреймворк для проекта")
        context = st.text_area("Контекст ситуации", height=80, placeholder="Почему нужно это решение...")
        
        col1, col2 = st.columns(2)
        with col1:
            options_text = st.text_area("Варианты выбора (по одному в строке)", height=80)
            choice = st.selectbox("Что вы выбрали?", options_text.split('\n') if options_text else [""])
        with col2:
            reasoning = st.text_area("Ваше обоснование", height=80, placeholder="Почему выбрали именно это...")
            expected = st.text_area("Ожидаемый результат", height=80)
        
        if st.form_submit_button("💾 Сохранить решение", use_container_width=True):
            if title.strip():
                options = [o.strip() for o in options_text.split('\n') if o.strip()]
                add_decision(title, context, options, choice, reasoning, expected)
                st.success("✅ Решение записано!")
                st.rerun()
    
    # История решений
    decisions = get_all_decisions()
    if decisions:
        st.markdown("### 📚 История решений")
        
        for decision in decisions:
            reviewed = decision['actual_outcome'] is not None
            
            st.markdown(f"""
            <div class="card-enhanced" style="border-left:3px solid {'#10b981' if reviewed else '#7B3EFF'};">
                <div style="display:flex; justify-content:space-between; align-items:start; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:600; color:#fff; font-size:1.05rem;">{decision['title']}</div>
                        <div style="font-size:0.8rem; color:#94a3b8; margin-top:3px;">
                            Решение: <strong>{decision['choice']}</strong> | {decision['created_at']}
                        </div>
                    </div>
                    {'<span class="badge" style="color:#10b981; border-color:#10b981;">✓ Проверено</span>' if reviewed else '<span class="badge" style="color:#7B3EFF;">⏳ Ожидает</span>'}
                </div>
            </div>""", unsafe_allow_html=True)
            
            if not reviewed:
                with st.expander("📝 Добавить результат"):
                    with st.form(f"review_decision_{decision['id']}"):
                        outcome = st.text_area("Что произошло в итоге?", height=80)
                        impact = st.slider("Влияние на успех (-10 до +10)", -10, 10, 5)
                        if st.form_submit_button("💾 Сохранить результат"):
                            review_decision(decision['id'], outcome, 5 + impact)
                            st.rerun()

# ====================================================
# РАЗДЕЛ: ОТВЛЕЧЕНИЯ
# ====================================================

elif section == "📉 Отвлечения":
    st.markdown('<div class="section-title">📉 Трекер отвлечений и потерь времени</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("distraction_form"):
            dist_type = st.selectbox("Тип отвлечения", 
                ["Социальные сети", "Мессенджеры", "Новости", "Эмейл", "Другие веб-сайты", "Разговоры", "Уведомления", "Сон", "Другое"])
            description = st.text_input("Описание")
            duration = st.number_input("Длительность (мин)", 0, 480, 5)
            severity = st.slider("Серьёзность потери", 1, 10, 5)
            
            if st.form_submit_button("📝 Зафиксировать отвлечение", use_container_width=True):
                log_distraction(dist_type, description, duration, severity)
                st.toast("📊 Отвлечение записано!")
                st.rerun()
    
    with col2:
        today_distractions = get_distractions_today()
        total_time = sum(d['duration_minutes'] or 0 for d in today_distractions)
        st.metric("📊 Потеряно сегодня", f"{total_time} мин", f"{len(today_distractions)} раз")
    
    # Статистика
    st.markdown("---")
    stats = get_distraction_stats(7)
    
    if stats:
        st.markdown("### 📈 За последние 7 дней")
        
        stats_sorted = sorted(stats, key=lambda x: x['total_time'] or 0, reverse=True)
        
        for stat in stats_sorted:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border-radius:10px; padding:12px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <div style="font-weight:600; color:#fff;">{stat['distraction_type']}</div>
                        <div style="font-size:0.8rem; color:#94a3b8;">{stat['count']} раз</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.2rem; font-weight:700; color:#f43f5e;">{stat['total_time']:.0f} мин</div>
                        <div style="font-size:0.8rem; color:#94a3b8;">всего</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
    
    # Рекомендации
    st.markdown("---")
    st.markdown("### 💡 Как сократить отвлечения")
    
    recommendations = [
        ("🚫 Режим \"Не беспокоить\"", "Активируйте во время работы на 90 минут"),
        ("🔕 Отключите уведомления", "Включайте их только при необходимости"),
        ("📱 Телефон подальше", "Оставляйте в другой комнате во время фокуса"),
        ("⏰ Определённое время для проверки", "Проверяйте эмейл/мессенджеры 3 раза в день"),
    ]
    
    for title, desc in recommendations:
        st.markdown(f"""
        <div style="background:rgba(50,121,255,0.06); border-left:3px solid #3279FF;
            border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:10px;">
            <div style="font-weight:700; color:#a5b4fc;">{title}</div>
            <div style="font-size:0.85rem; color:#94a3b8; margin-top:3px;">{desc}</div>
        </div>""", unsafe_allow_html=True)

# ====================================================
# РАЗДЕЛ: СОСТОЯНИЕ ПОТОКА
# ====================================================

elif section == "⚡ Состояние потока":
    st.markdown('<div class="section-title">⚡ Анализ состояния потока (Flow State)</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="insight-box">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            ⚡ <strong>Состояние потока</strong> — идеальное состояние полного погружения в работу.
            Отслеживайте качество ваших сессий и учитесь его достигать.
        </div>
    </div>""", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ НАЧАТЬ СЕССИЮ ПОТОКА", use_container_width=True):
            if start_focus_session():
                st.success("🎯 Сессия началась! Сосредоточьтесь на работе.")
                st.session_state.flow_started = True
    
    with col2:
        if st.button("⏹️ ЗАВЕРШИТЬ СЕССИЮ", use_container_width=True):
            with st.form("end_flow_form"):
                interruptions = st.slider("Количество перерывов", 0, 10, 0)
                satisfaction = st.slider("Удовлетворённость", 1, 10, 7)
                notes = st.text_area("Заметки о сессии", height=60)
                
                if st.form_submit_button("💾 Завершить"):
                    end_focus_session(interruptions, satisfaction, notes)
                    st.success("✅ Сессия записана!")
                    st.rerun()
    
    # Анализ сессий
    sessions = get_focus_sessions(14)
    
    if sessions:
        st.markdown("### 📊 Ваши сессии потока (14 дней)")
        
        avg_satisfaction = sum(s['satisfaction'] for s in sessions) / len(sessions)
        avg_interruptions = sum(s['interruptions'] for s in sessions) / len(sessions)
        
        st.markdown(f"""
        <div class="insight-box">
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; text-align:center;">
                <div>
                    <div style="font-size:1.4rem; font-weight:700; color:#3279FF;">{len(sessions)}</div>
                    <div style="font-size:0.8rem; color:#94a3b8;">сессий</div>
                </div>
                <div>
                    <div style="font-size:1.4rem; font-weight:700; color:#22c55e;">{avg_satisfaction:.1f}/10</div>
                    <div style="font-size:0.8rem; color:#94a3b8;">средняя удовлетворённость</div>
                </div>
                <div>
                    <div style="font-size:1.4rem; font-weight:700; color:#f59e0b;">{avg_interruptions:.1f}</div>
                    <div style="font-size:0.8rem; color:#94a3b8;">среднее количество перерывов</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
        
        # График
        sess_df = pd.DataFrame([{
            'Дата': s['date'],
            'Удовлетворённость': s['satisfaction'],
            'Перерывы': s['interruptions']
        } for s in sessions]).set_index('Дата')
        
        st.line_chart(sess_df, color=["#22c55e", "#f43f5e"])
        
        # Последние сессии
        st.markdown("### 📋 Последние сессии")
        for session in sessions[-5:]:
            st.markdown(f"""
            <div class="card-enhanced">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <div style="font-weight:600; color:#fff;">⚡ {session['date']} {session['start_time']} - {session['end_time']}</div>
                        <div style="font-size:0.8rem; color:#94a3b8; margin-top:3px;">
                            Перерывы: {session['interruptions']} | Удовлетворённость: {session['satisfaction']}/10
                        </div>
                    </div>
                    <div style="text-align:right;">
                        {'🟢 Отличная' if session['satisfaction'] >= 8 else '🟡 Хорошая' if session['satisfaction'] >= 6 else '🔴 Нужно улучшить'}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

# ====================================================
# РАЗДЕЛ: РИТУАЛ ЗАВЕРШЕНИЯ
# ====================================================

elif section == "💤 Ритуал завершения":
    st.markdown('<div class="section-title">💤 Daily Shutdown Ritual</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="insight-box">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            💤 <strong>Ритуал завершения дня</strong> помогает закончить день с чувством завершённости
            и подготовиться к завтрашнему дню. Займёт 10-15 минут.
        </div>
    </div>""", unsafe_allow_html=True)
    
    shutdown = get_shutdown_ritual()
    
    if shutdown:
        st.success(f"✅ Ритуал сегодня уже проведён в {shutdown['created_at']}")
        with st.expander("📖 Посмотреть результаты сегодня"):
            st.markdown(f"**📝 Рефлексия:**\n{shutdown['reflection']}")
            st.markdown(f"**🏆 Победы:**\n{shutdown['wins']}")
            st.markdown(f"**🎯 Завтрашний фокус:**\n{shutdown['tomorrow_focus']}")
            st.metric("😊 Удовлетворённость", f"{shutdown['satisfaction']}/10")
    
    with st.expander("📋 Провести ритуал завершения", expanded=not shutdown):
        with st.form("shutdown_ritual_form"):
            st.markdown("## 🎯 Ритуал завершения дня (15 мин)")
            
            st.markdown("### 1️⃣ Рефлексия (3 мин)")
            reflection = st.text_area(
                "📝 Как прошёл мой день? Что я чувствую?",
                height=80,
                placeholder="Описание энергии, эмоций, событий дня..."
            )
            
            st.markdown("### 2️⃣ Победы (3 мин)")
            wins = st.text_area(
                "🏆 Мои достижения сегодня",
                height=80,
                placeholder="Даже маленькие победы считаются..."
            )
            
            st.markdown("### 3️⃣ Планирование (5 мин)")
            tomorrow_focus = st.text_area(
                "🎯 На чём я сфокусируюсь завтра? (максимум 3 пункта)",
                height=80,
                placeholder="1. Главная приоритетная задача\n2. Поддерживающая задача\n3. Личная нужда"
            )
            
            st.markdown("### 4️⃣ Оценка (1 мин)")
            satisfaction = st.slider("😊 Я удовлетворён днём", 1, 10, 7)
            
            st.markdown("---")
            
            if st.form_submit_button("💾 ЗАВЕРШИТЬ ДЕНЬ", use_container_width=True):
                save_shutdown_ritual(reflection, wins, tomorrow_focus, [], satisfaction)
                st.balloons()
                st.success("✅ Отличная работа! День завершён. Хорошего вам вечера! 🌙")
                st.rerun()
    
    # История ритуалов
    st.markdown("---")
    st.markdown("### 📚 История ритуалов")
    
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM shutdown_rituals ORDER BY date DESC LIMIT 7")
            rituals = [dict(row) for row in c.fetchall()]
    except: rituals = []
    
    if rituals:
        for ritual in rituals:
            with st.expander(f"📅 {ritual['date']} - Удовлетворённость: {'⭐' * ritual['satisfaction']}"):
                st.markdown(f"**Рефлексия:** {ritual['reflection']}")
                st.markdown(f"**Победы:** {ritual['wins']}")
                st.markdown(f"**Завтра:** {ritual['tomorrow_focus']}")

# ====================================================
# РАЗДЕЛ: УМНЫЕ РЕКОМЕНДАЦИИ
# ====================================================

elif section == "📈 Умные рекомендации":
    st.markdown('<div class="section-title">📈 AI-powered рекомендации</div>', unsafe_allow_html=True)
    
    recommendations = generate_smart_recommendations()
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['severity'], "⚪")
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border-left:4px solid {rec['color']};
                border-radius:0 12px 12px 0; padding:16px; margin-bottom:12px;">
                <div style="display:flex; gap:12px; align-items:start;">
                    <div style="font-size:1.5rem;">{rec['icon']}</div>
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:700; color:{rec['color']}; font-size:1.05rem;">
                            {rec['title']}
                        </div>
                        <div style="color:#94a3b8; margin-top:6px; font-size:0.95rem;">
                            {rec['description']}
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            
            # Действие
            if rec['type'] == 'distraction':
                if st.button("🚫 Включить режим фокуса", key=f"action_{i}"):
                    st.info("Активируйте режим 'Do Not Disturb' на ваших устройствах")
            elif rec['type'] == 'focus_quality':
                if st.button("⚡ Запланировать длительную сессию", key=f"action_{i}"):
                    st.info("Попробуйте сессию в 90 минут вместо стандартных 25")
            elif rec['type'] == 'skill_development':
                if st.button("🌱 Планировать практику", key=f"action_{i}"):
                    st.info("Добавьте практику в еженедельный график")
    else:
        st.success("🌟 Нет критических рекомендаций. Вы отлично справляетесь!")
        st.info("💡 Продолжайте собирать данные для получения персональных рекомендаций")

# ====================================================
# РАЗДЕЛ: ПОЛНАЯ АНАЛИТИКА
# ====================================================

elif section == "📊 Полная аналитика":
    st.markdown('<div class="section-title">📊 Детальная аналитика</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Время", "Привычки", "Энергия", "Успех"])
    
    with tab1:
        st.markdown("### ⏰ Анализ времени")
        sessions = get_focus_sessions(30)
        if sessions:
            time_df = pd.DataFrame([{
                'Дата': s['date'],
                'Качество': s['satisfaction'],
                'Перерывы': s['interruptions']
            } for s in sessions])
            st.line_chart(time_df.set_index('Дата'))
    
    with tab2:
        st.markdown("### ✅ Успех привычек")
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT name, id FROM habits LIMIT 10")
                habits = [dict(row) for row in c.fetchall()]
        except: habits = []
        
        if habits:
            habit_data = []
            for h in habits:
                try:
                    with get_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) as cnt FROM habit_logs WHERE habit_id=? AND completed=1 AND date >= date('now', '-7 days')", (h['id'],))
                        cnt = c.fetchone()['cnt']
                        habit_data.append({'Привычка': h['name'], 'На этой неделе': cnt})
                except: pass
            
            if habit_data:
                st.bar_chart(pd.DataFrame(habit_data).set_index('Привычка'))
    
    with tab3:
        st.markdown("### ⚡ Уровень энергии")
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT date, energy FROM mood_journal WHERE date >= date('now', '-30 days') ORDER BY date")
                energy_data = [dict(row) for row in c.fetchall()]
        except: energy_data = []
        
        if energy_data:
            df = pd.DataFrame(energy_data).set_index('date')
            st.area_chart(df, color=["#3279FF"])
    
    with tab4:
        st.markdown("### 🏆 Показатели успеха")
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM focus_scores ORDER BY date DESC LIMIT 30")
                scores = [dict(row) for row in c.fetchall()]
        except: scores = []
        
        if scores:
            df = pd.DataFrame(scores)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Средний счёт", f"{df['score'].mean():.0f}/100")
            with col2:
                st.metric("Лучший день", f"{df['score'].max()}/100")
            
            st.line_chart(df.set_index('date')['score'])

st.markdown("---")
st.caption("🚀 Пространство Фокуса 2.0+ | Умная система управления жизнью | Версия Enhanced")