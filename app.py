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

# --- КОНФИГУРАЦИЯ ---
DB_NAME = "focus_space_v2.db"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ====================================================
# БАЗА ДАННЫХ
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

def init_db():
    with get_connection() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, category TEXT NOT NULL,
            day_of_week TEXT NOT NULL, notes TEXT,
            status TEXT NOT NULL DEFAULT 'В процессе',
            priority TEXT NOT NULL DEFAULT 'Средний ⚡',
            time_spent INTEGER DEFAULT 0,
            pomodoro_sessions INTEGER DEFAULT 0,
            created_date TEXT, completed_date TEXT,
            due_date TEXT, estimated_minutes INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            energy_level TEXT DEFAULT 'Средний'
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS notes_hub (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT NOT NULL, tag TEXT,
            pinned INTEGER DEFAULT 0,
            color TEXT DEFAULT 'default'
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, amount REAL NOT NULL,
            category TEXT NOT NULL, description TEXT,
            date TEXT NOT NULL, recurring INTEGER DEFAULT 0,
            recurring_period TEXT DEFAULT ''
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT NOT NULL,
            frequency TEXT NOT NULL, created_date TEXT NOT NULL,
            color TEXT DEFAULT 'blue',
            goal_count INTEGER DEFAULT 1,
            reminder_time TEXT DEFAULT ''
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL, date TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0, notes TEXT,
            count INTEGER DEFAULT 1,
            FOREIGN KEY (habit_id) REFERENCES habits(id),
            UNIQUE(habit_id, date)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT,
            category TEXT NOT NULL, target_date TEXT NOT NULL,
            progress INTEGER DEFAULT 0, status TEXT DEFAULT 'Активна',
            created_date TEXT NOT NULL,
            milestones TEXT DEFAULT '[]',
            priority TEXT DEFAULT 'Средний'
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER, duration_minutes INTEGER NOT NULL,
            completed BOOLEAN DEFAULT 1, date TEXT NOT NULL, notes TEXT
        )""")

        # ✨ НОВЫЕ ТАБЛИЦЫ
        c.execute("""CREATE TABLE IF NOT EXISTS mood_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            mood INTEGER NOT NULL,
            energy INTEGER NOT NULL,
            notes TEXT,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS time_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            color TEXT DEFAULT 'blue',
            task_id INTEGER,
            completed INTEGER DEFAULT 0
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            wins TEXT DEFAULT '',
            challenges TEXT DEFAULT '',
            insights TEXT DEFAULT '',
            next_actions TEXT DEFAULT '',
            rating INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS brain_dump (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS focus_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            score INTEGER NOT NULL,
            tasks_done INTEGER DEFAULT 0,
            pomodoros INTEGER DEFAULT 0,
            habits_done INTEGER DEFAULT 0,
            mood INTEGER DEFAULT 5
        )""")

        # Миграции для старых столбцов
        for col_def in [
            ("tasks", "due_date", "TEXT"),
            ("tasks", "estimated_minutes", "INTEGER DEFAULT 0"),
            ("tasks", "tags", "TEXT DEFAULT ''"),
            ("tasks", "energy_level", "TEXT DEFAULT 'Средний'"),
            ("notes_hub", "pinned", "INTEGER DEFAULT 0"),
            ("notes_hub", "color", "TEXT DEFAULT 'default'"),
            ("finances", "recurring", "INTEGER DEFAULT 0"),
            ("finances", "recurring_period", "TEXT DEFAULT ''"),
            ("habits", "goal_count", "INTEGER DEFAULT 1"),
            ("habits", "reminder_time", "TEXT DEFAULT ''"),
            ("goals", "milestones", "TEXT DEFAULT '[]'"),
            ("goals", "priority", "TEXT DEFAULT 'Средний'"),
        ]:
            try:
                c.execute(f"ALTER TABLE {col_def[0]} ADD COLUMN {col_def[1]} {col_def[2]}")
            except Exception:
                pass

        conn.commit()

# ====================================================
# ЗАДАЧИ
# ====================================================

def get_all_tasks_raw():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM tasks ORDER BY priority DESC, created_date DESC")
            return [dict(row) for row in c.fetchall()]
    except: return []

def add_task(title, category, day_of_week, notes, priority, due_date=None, estimated_minutes=0, tags='', energy_level='Средний'):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO tasks 
                (title, category, day_of_week, notes, status, priority, created_date, due_date, estimated_minutes, tags, energy_level)
                VALUES (?, ?, ?, ?, 'В процессе', ?, ?, ?, ?, ?, ?)""",
                (title, category, day_of_week, notes, priority,
                 datetime.now().strftime("%Y-%m-%d"),
                 due_date.strftime("%Y-%m-%d") if due_date else None,
                 estimated_minutes, tags, energy_level))
            conn.commit()
    except Exception as e:
        logging.error(f"Ошибка добавления задачи: {e}")

def update_task_status(task_id, new_status):
    try:
        completed_date = datetime.now().strftime("%Y-%m-%d") if new_status == "Выполнено" else None
        with get_connection() as conn:
            conn.execute("UPDATE tasks SET status=?, completed_date=? WHERE id=?", (new_status, completed_date, task_id))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_task(task_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()
    except Exception as e: logging.error(e)

def update_pomodoro_count(task_id):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE tasks SET pomodoro_sessions=pomodoro_sessions+1 WHERE id=?", (task_id,))
            conn.commit()
    except Exception as e: logging.error(e)

def get_tasks_by_energy(energy_level):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM tasks WHERE energy_level=? AND status='В процессе'", (energy_level,))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# ПРИВЫЧКИ
# ====================================================

def add_habit(name, category, frequency, goal_count=1):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO habits (name, category, frequency, created_date, goal_count)
                VALUES (?, ?, ?, ?, ?)""",
                (name, category, frequency, datetime.now().strftime("%Y-%m-%d"), goal_count))
            conn.commit()
    except Exception as e: logging.error(e)

def get_all_habits():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM habits")
            return [dict(row) for row in c.fetchall()]
    except: return []

def log_habit(habit_id, log_date, completed, count=1):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT OR REPLACE INTO habit_logs (habit_id, date, completed, count)
                VALUES (?, ?, ?, ?)""", (habit_id, log_date, completed, count))
            conn.commit()
    except Exception as e: logging.error(e)

def get_habit_streak(habit_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT date FROM habit_logs WHERE habit_id=? AND completed=1
                ORDER BY date DESC LIMIT 60""", (habit_id,))
            dates = [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in c.fetchall()]
            if not dates: return 0
            streak = 0
            today = datetime.now().date()
            expected = today
            for d in dates:
                if d == expected or d == expected - timedelta(days=1):
                    streak += 1
                    expected = d - timedelta(days=1)
                else:
                    break
            return streak
    except: return 0

def get_habit_heatmap_data(habit_id, days=60):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT date, completed FROM habit_logs WHERE habit_id=?
                ORDER BY date DESC LIMIT ?""", (habit_id, days))
            return {row['date']: row['completed'] for row in c.fetchall()}
    except: return {}

def delete_habit(habit_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM habit_logs WHERE habit_id=?", (habit_id,))
            conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
            conn.commit()
    except Exception as e: logging.error(e)

def get_habit_completion_rate(habit_id, days=30):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("""SELECT COUNT(*) as cnt FROM habit_logs WHERE habit_id=? AND completed=1 AND date>=?""",
                (habit_id, start))
            completed = c.fetchone()['cnt']
            return round(completed / days * 100)
    except: return 0

# ====================================================
# ЦЕЛИ
# ====================================================

def add_goal(title, description, category, target_date, priority='Средний'):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO goals (title, description, category, target_date, created_date, priority)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (title, description, category, target_date, datetime.now().strftime("%Y-%m-%d"), priority))
            conn.commit()
    except Exception as e: logging.error(e)

def get_all_goals():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM goals ORDER BY target_date ASC")
            return [dict(row) for row in c.fetchall()]
    except: return []

def update_goal_progress(goal_id, progress):
    try:
        with get_connection() as conn:
            status = "Завершена" if progress >= 100 else "Активна"
            conn.execute("UPDATE goals SET progress=?, status=? WHERE id=?", (progress, status, goal_id))
            conn.commit()
    except Exception as e: logging.error(e)

def update_goal_milestones(goal_id, milestones):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE goals SET milestones=? WHERE id=?", (json.dumps(milestones, ensure_ascii=False), goal_id))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_goal(goal_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# ЗАМЕТКИ
# ====================================================

def get_all_notes():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM notes_hub ORDER BY pinned DESC, id DESC")
            return [dict(row) for row in c.fetchall()]
    except: return []

def add_note(title, content, tag, color='default'):
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO notes_hub (title, content, created_at, tag, color) VALUES (?, ?, ?, ?, ?)",
                (title, content, datetime.now().strftime("%d.%m.%Y %H:%M"), tag, color))
            conn.commit()
    except Exception as e: logging.error(e)

def toggle_pin_note(note_id, current_pin):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE notes_hub SET pinned=? WHERE id=?", (0 if current_pin else 1, note_id))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_note(note_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM notes_hub WHERE id=?", (note_id,))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# ФИНАНСЫ
# ====================================================

def get_all_transactions():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM finances ORDER BY id DESC")
            return [dict(row) for row in c.fetchall()]
    except: return []

def add_transaction(t_type, amount, category, description, recurring=False, recurring_period=''):
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO finances (type, amount, category, description, date, recurring, recurring_period) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (t_type, amount, category, description, datetime.now().strftime("%d.%m.%Y"), 1 if recurring else 0, recurring_period))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_transaction(t_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM finances WHERE id=?", (t_id,))
            conn.commit()
    except Exception as e: logging.error(e)

def get_monthly_summary():
    try:
        transactions = get_all_transactions()
        monthly = {}
        for t in transactions:
            try:
                parts = t['date'].split('.')
                key = f"{parts[2]}-{parts[1]}"
                if key not in monthly:
                    monthly[key] = {'income': 0, 'expense': 0}
                if t['type'] == 'Доход':
                    monthly[key]['income'] += t['amount']
                else:
                    monthly[key]['expense'] += t['amount']
            except: pass
        return monthly
    except: return {}

# ====================================================
# ДНЕВНИК НАСТРОЕНИЯ (НОВОЕ)
# ====================================================

def add_mood_entry(mood, energy, notes, tags=''):
    try:
        with get_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("""INSERT OR REPLACE INTO mood_journal (date, mood, energy, notes, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (today, mood, energy, notes, tags, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_mood_history(days=30):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("SELECT * FROM mood_journal WHERE date>=? ORDER BY date ASC", (start,))
            return [dict(row) for row in c.fetchall()]
    except: return []

def get_today_mood():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT * FROM mood_journal WHERE date=?", (today,))
            row = c.fetchone()
            return dict(row) if row else None
    except: return None

# ====================================================
# ТАЙМ-БЛОКИ (НОВОЕ)
# ====================================================

def add_time_block(title, start_time, end_time, block_date, category, color='blue', task_id=None):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO time_blocks (title, start_time, end_time, date, category, color, task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, start_time, end_time, block_date, category, color, task_id))
            conn.commit()
    except Exception as e: logging.error(e)

def get_time_blocks(block_date):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM time_blocks WHERE date=? ORDER BY start_time ASC", (block_date,))
            return [dict(row) for row in c.fetchall()]
    except: return []

def toggle_time_block(block_id):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE time_blocks SET completed = 1 - completed WHERE id=?", (block_id,))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_time_block(block_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM time_blocks WHERE id=?", (block_id,))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# РЕТРОСПЕКТИВЫ (НОВОЕ)
# ====================================================

def add_review(review_type, wins, challenges, insights, next_actions, rating):
    try:
        with get_connection() as conn:
            conn.execute("""INSERT INTO reviews (type, date, wins, challenges, insights, next_actions, rating, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (review_type, datetime.now().strftime("%Y-%m-%d"), wins, challenges, insights, next_actions, rating,
                 datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_all_reviews():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM reviews ORDER BY created_at DESC LIMIT 20")
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# МОЗГОВОЙ ШТУРМ / BRAIN DUMP (НОВОЕ)
# ====================================================

def add_brain_dump(content):
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO brain_dump (content, created_at) VALUES (?, ?)",
                (content, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
    except Exception as e: logging.error(e)

def get_brain_dump_items(processed=None):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            if processed is None:
                c.execute("SELECT * FROM brain_dump ORDER BY created_at DESC")
            else:
                c.execute("SELECT * FROM brain_dump WHERE processed=? ORDER BY created_at DESC", (processed,))
            return [dict(row) for row in c.fetchall()]
    except: return []

def process_brain_dump(item_id, category):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE brain_dump SET processed=1, category=? WHERE id=?", (category, item_id))
            conn.commit()
    except Exception as e: logging.error(e)

def delete_brain_dump(item_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM brain_dump WHERE id=?", (item_id,))
            conn.commit()
    except Exception as e: logging.error(e)

# ====================================================
# СЧЁТ ФОКУСА (НОВОЕ)
# ====================================================

def calculate_daily_focus_score():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = get_all_tasks_raw()
        today_done = len([t for t in tasks if t.get('completed_date') == today])

        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM habit_logs WHERE date=? AND completed=1", (today,))
            habits_done = c.fetchone()['cnt']

            c.execute("SELECT COUNT(*) as cnt FROM pomodoro_sessions WHERE date=? AND completed=1", (today,))
            pomodoros = c.fetchone()['cnt']

        mood_data = get_today_mood()
        mood_score = mood_data['mood'] if mood_data else 5

        # Формула очков
        score = min(100, today_done * 10 + habits_done * 8 + pomodoros * 5 + mood_score * 2)

        # Сохранить
        with get_connection() as conn:
            conn.execute("""INSERT OR REPLACE INTO focus_scores (date, score, tasks_done, pomodoros, habits_done, mood)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (today, score, today_done, pomodoros, habits_done, mood_score))
            conn.commit()

        return score, today_done, pomodoros, habits_done
    except: return 0, 0, 0, 0

def get_focus_score_history(days=14):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("SELECT * FROM focus_scores WHERE date>=? ORDER BY date ASC", (start,))
            return [dict(row) for row in c.fetchall()]
    except: return []

# ====================================================
# ОНБОРДИНГ И ЭКСПОРТ
# ====================================================

def is_onboarding_completed():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key='onboarding_completed'")
            row = c.fetchone()
            return row is not None and row["value"] == "True"
    except: return False

def seed_demo_tour():
    if not is_onboarding_completed():
        add_task("🪐 Изучить возможности Пространства Фокуса", "Работа", "Понедельник",
                 "Пройдите все разделы и протестируйте функционал!", "Высокий 🔥",
                 estimated_minutes=30, tags="demo,start", energy_level="Высокий")
        add_task("🧠 Провести первый Brain Dump", "Личное", "Вторник",
                 "Выгрузите все мысли в раздел Brain Dump", "Средний ⚡",
                 energy_level="Низкий")
        add_note("💡 Добро пожаловать!", "**Пространство Фокуса v2** — ваша система управления жизнью.\n\n*Новые функции:*\n- 🧠 Brain Dump — выгружайте мысли\n- 📅 Тайм-блокинг\n- 😊 Дневник настроения\n- 🔄 Ретроспективы\n- ⚡ Счёт Фокуса", "Идеи", color="purple")
        add_transaction("Доход", 150000, "Бизнес/SaaS 🚀", "Первая подписка на систему")
        add_transaction("Расход", 12000, "Серверы/IT-Инструменты 🌐", "Оплата хостинга")
        add_habit("📚 Чтение 30 минут", "Обучение", "Ежедневно")
        add_habit("💪 Спорт/Зарядка", "Здоровье", "5 раз в неделю")
        add_goal("🚀 Запустить MVP продукта", "Разработать и выпустить MVP", "Бизнес", "2025-06-30", priority="Высокий")
        add_mood_entry(7, 8, "Начинаю работу с новой системой продуктивности!", "старт,мотивация")
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('onboarding_completed', 'True')")
            conn.commit()

def export_tasks_to_csv():
    try:
        tasks = get_all_tasks_raw()
        df = pd.DataFrame(tasks)
        return df.to_csv(index=False, encoding='utf-8-sig')
    except: return None

def export_all_data_json():
    try:
        data = {
            'tasks': get_all_tasks_raw(), 'notes': get_all_notes(),
            'transactions': get_all_transactions(), 'habits': get_all_habits(),
            'goals': get_all_goals(), 'mood_journal': get_mood_history(365),
            'exported_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    except: return None

def generate_weekly_report():
    try:
        tasks = get_all_tasks_raw()
        notes = get_all_notes()
        transactions = get_all_transactions()
        habits = get_all_habits()
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        weekly_tasks = [t for t in tasks if (t.get('created_date') or '') >= week_ago.strftime("%Y-%m-%d")]
        completed_tasks = [t for t in weekly_tasks if t['status'] == 'Выполнено']
        weekly_income = sum(t['amount'] for t in transactions if t['type'] == 'Доход')
        weekly_expense = sum(t['amount'] for t in transactions if t['type'] == 'Расход')
        return {
            'total_tasks': len(weekly_tasks), 'completed_tasks': len(completed_tasks),
            'completion_rate': len(completed_tasks) / len(weekly_tasks) * 100 if weekly_tasks else 0,
            'weekly_income': weekly_income, 'weekly_expense': weekly_expense,
            'net_balance': weekly_income - weekly_expense,
            'total_notes': len(notes), 'total_habits': len(habits)
        }
    except: return None

# ====================================================
# ЦИТАТЫ И МОТИВАЦИЯ
# ====================================================

MOTIVATIONAL_QUOTES = [
    ("Фокус — это умение сказать «нет».", "Стив Джобс"),
    ("Действие — это основной ключ к успеху.", "Пабло Пикассо"),
    ("Успех — это сумма небольших усилий, повторяющихся изо дня в день.", "Роберт Колье"),
    ("Мы то, что мы делаем постоянно. Совершенство — не действие, а привычка.", "Аристотель"),
    ("Лучшее время для посадки дерева — 20 лет назад. Второе лучшее время — сейчас.", "Китайская пословица"),
    ("Не ждите вдохновения. Оно появляется в процессе работы.", "Джек Лондон"),
    ("Сложные задачи делайте утром, пока мозг свеж.", "Марк Твен"),
    ("Каждый эксперт когда-то был новичком.", "Хелен Хейс"),
    ("Единственный способ сделать великую работу — любить то, что делаешь.", "Стив Джобс"),
    ("Прогресс, а не совершенство.", "Аноним"),
]

def get_daily_quote():
    idx = datetime.now().timetuple().tm_yday % len(MOTIVATIONAL_QUOTES)
    return MOTIVATIONAL_QUOTES[idx]

# ====================================================
# УТИЛИТЫ UI
# ====================================================

DAYS_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def pluralize_tasks(n):
    if n % 10 == 1 and n % 100 != 11: return f"{n} задача"
    elif n % 10 in [2,3,4] and n % 100 not in [12,13,14]: return f"{n} задачи"
    else: return f"{n} задач"

MOOD_EMOJIS = {1:"😞", 2:"😟", 3:"😐", 4:"🙂", 5:"😊", 6:"😄", 7:"🌟", 8:"🚀", 9:"🔥", 10:"⚡"}
ENERGY_EMOJIS = {1:"🪫", 2:"😴", 3:"😑", 4:"🌿", 5:"💡", 6:"⚡", 7:"🔥", 8:"💪", 9:"🦁", 10:"🌋"}

NOTE_COLORS = {
    'default': ('rgba(255,255,255,0.05)', 'rgba(255,255,255,0.08)'),
    'purple': ('rgba(139,92,246,0.08)', 'rgba(139,92,246,0.25)'),
    'blue': ('rgba(59,130,246,0.08)', 'rgba(59,130,246,0.25)'),
    'green': ('rgba(34,197,94,0.08)', 'rgba(34,197,94,0.25)'),
    'amber': ('rgba(245,158,11,0.08)', 'rgba(245,158,11,0.25)'),
    'red': ('rgba(239,68,68,0.08)', 'rgba(239,68,68,0.25)'),
}

BLOCK_COLORS = {
    'blue': '#3b82f6', 'purple': '#8b5cf6', 'green': '#22c55e',
    'amber': '#f59e0b', 'red': '#ef4444', 'pink': '#ec4899', 'cyan': '#06b6d4'
}

# ====================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ====================================================

st.set_page_config(page_title="Пространство Фокуса 2.0", page_icon="🪐", layout="wide", initial_sidebar_state="auto")
init_db()
seed_demo_tour()

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

html { overflow-y: auto !important; -webkit-text-size-adjust: 100%; }
body { overflow-x: hidden !important; min-height: 100vh; touch-action: pan-y; }
[data-testid="stAppViewContainer"] { overflow-x: hidden !important; min-height: 100vh; }

[data-testid="stSidebar"] {
    background: rgba(11, 15, 25, 0.85) !important;
    backdrop-filter: blur(25px) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}

/* === ЗАГОЛОВКИ === */
.saas-title {
    background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800; font-size: 2.6rem; letter-spacing: -0.04em; margin-bottom: 4px;
}
.saas-subtitle { color: #94a3b8; font-size: 1rem; margin-bottom: 20px; }

/* === QUOTE BLOCK === */
.quote-block {
    background: linear-gradient(135deg, rgba(50,121,255,0.08), rgba(123,62,255,0.08));
    border-left: 3px solid #7B3EFF;
    border-radius: 0 12px 12px 0;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-style: italic;
    color: #cbd5e1;
    font-size: 0.95rem;
}

/* === FOCUS SCORE === */
.focus-score-ring {
    width: 90px; height: 90px;
    border-radius: 50%;
    background: conic-gradient(#3279FF var(--score-deg, 0deg), rgba(255,255,255,0.08) 0deg);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; font-weight: 800; color: #fff;
    box-shadow: 0 0 24px rgba(50,121,255,0.3);
    margin: 0 auto;
}

/* === KPI === */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 14px; margin-bottom: 22px;
}
.kpi-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 14px 18px;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: rgba(50,121,255,0.3); }
.kpi-label { color: #94a3b8; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-val {
    font-size: 1.7rem; font-weight: 700; margin-top: 4px;
    background: linear-gradient(135deg, #3279FF 0%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

/* === ФОРМЫ === */
div[data-testid="stForm"] {
    background: rgba(15, 22, 42, 0.4) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 20px !important; padding: 26px !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="select"] > div {
    background-color: rgba(7, 10, 19, 0.7) !important;
    color: #ffffff !important; border-radius: 10px !important;
}

/* === КНОПКИ === */
.stButton button {
    background: rgba(255,255,255,0.06) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.13) !important;
    border-radius: 10px !important; min-height: 42px !important;
    font-weight: 500 !important; transition: all 0.2s ease !important;
}
.stButton button:hover {
    background: rgba(255,255,255,0.11) !important;
    transform: translateY(-1px);
    border-color: rgba(50,121,255,0.4) !important;
}
.stFormSubmitButton button {
    background: linear-gradient(135deg, #3279FF 0%, #7B3EFF 100%) !important;
    min-height: 46px !important; font-weight: 600 !important;
    border: none !important;
}

/* === КАРТОЧКИ === */
.task-box {
    background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 16px 18px; margin-bottom: 10px;
}
.task-completed {
    background: linear-gradient(135deg, rgba(16,185,129,0.04) 0%, rgba(0,0,0,0) 100%) !important;
    border-color: rgba(16,185,129,0.2) !important;
}
.task-overdue { border-color: rgba(239,68,68,0.4) !important; }

.habit-card {
    background: linear-gradient(135deg, rgba(34,197,94,0.05), rgba(15,23,42,0.3));
    border: 1px solid rgba(34,197,94,0.18);
    border-radius: 14px; padding: 14px; margin-bottom: 12px;
}
.goal-card {
    background: linear-gradient(135deg, rgba(249,115,22,0.05), rgba(15,23,42,0.3));
    border: 1px solid rgba(249,115,22,0.18);
    border-radius: 14px; padding: 14px; margin-bottom: 12px;
}
.mood-card {
    background: linear-gradient(135deg, rgba(236,72,153,0.05), rgba(15,23,42,0.3));
    border: 1px solid rgba(236,72,153,0.2);
    border-radius: 14px; padding: 16px; margin-bottom: 12px;
}
.brain-item {
    background: rgba(15,22,42,0.5);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 12px 16px; margin-bottom: 8px;
}
.review-card {
    background: linear-gradient(135deg, rgba(6,182,212,0.05), rgba(15,23,42,0.3));
    border: 1px solid rgba(6,182,212,0.2);
    border-radius: 14px; padding: 16px; margin-bottom: 12px;
}
.time-block-item {
    border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 12px;
}

/* === БЕЙДЖИ === */
.badge {
    background: rgba(15,23,42,0.8);
    border: 1px solid rgba(255,255,255,0.12);
    padding: 4px 10px; border-radius: 20px;
    font-size: 0.73rem; font-weight: 600;
    white-space: nowrap; display: inline-block;
}

/* === ПОМОДОРО === */
.pomo-container {
    background: rgba(30,27,75,0.4);
    border: 1px solid rgba(123,62,255,0.2);
    padding: 14px; border-radius: 14px;
    text-align: center; margin-top: 20px;
}
.pomo-time { font-size: 2.2rem; font-weight: 800; color: #ff4b4b; font-family: monospace; }

/* === ФИНАНСЫ === */
.finance-row {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 10px;
    background: rgba(15,22,42,0.3);
    border: 1px solid rgba(255,255,255,0.05);
    padding: 12px 16px; border-radius: 12px; margin-bottom: 8px;
}

/* === ТЕПЛОВАЯ КАРТА === */
.heatmap-cell {
    display: inline-block; width: 14px; height: 14px;
    border-radius: 3px; margin: 1px;
}

/* === ПРОГРЕСС === */
.stProgress > div > div > div > div {
    background: linear-gradient(to right, #3279FF, #7B3EFF) !important;
}

/* === РАЗДЕЛИТЕЛЬ === */
.section-title {
    font-size: 1.25rem; font-weight: 700; color: #fff;
    margin: 8px 0 16px 0;
    display: flex; align-items: center; gap: 8px;
}

/* === INSIGHT BOX === */
.insight-box {
    background: linear-gradient(135deg, rgba(50,121,255,0.06), rgba(123,62,255,0.06));
    border: 1px solid rgba(50,121,255,0.2);
    border-radius: 12px; padding: 14px 18px; margin: 12px 0;
}

/* === МОБИЛЬНАЯ ОПТИМИЗАЦИЯ === */
@media (max-width: 768px) {
    .saas-title { font-size: 1.75rem; }
    .kpi-container { grid-template-columns: repeat(2, 1fr); }
    .finance-row { flex-direction: column; align-items: flex-start; }
}
</style>
""", unsafe_allow_html=True)

# ====================================================
# ДАННЫЕ
# ====================================================

all_tasks = get_all_tasks_raw()
today_str = datetime.now().strftime("%Y-%m-%d")
quote_text, quote_author = get_daily_quote()
focus_score, score_tasks, score_pomos, score_habits = calculate_daily_focus_score()

# ====================================================
# HEADER
# ====================================================

col_title, col_score = st.columns([3, 1])
with col_title:
    st.markdown('<div class="saas-title">🪐 Пространство Фокуса</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="saas-subtitle">Интеллектуальная система управления жизнью и продуктивностью</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="quote-block">"{quote_text}" <br><span style="color:#7c86a2; font-size:0.82rem; font-style:normal;">— {quote_author}</span></div>', unsafe_allow_html=True)

with col_score:
    score_deg = int(focus_score / 100 * 360)
    score_color = "#3279FF" if focus_score >= 70 else ("#f59e0b" if focus_score >= 40 else "#f43f5e")
    st.markdown(f"""
    <div style="text-align:center; padding: 10px;">
        <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">Счёт Фокуса</div>
        <div style="width:80px; height:80px; border-radius:50%;
            background: conic-gradient({score_color} {score_deg}deg, rgba(255,255,255,0.07) 0deg);
            display:flex; align-items:center; justify-content:center;
            margin: 0 auto; box-shadow: 0 0 20px {score_color}44;">
            <div style="width:58px; height:58px; border-radius:50%;
                background: #0b0f19;
                display:flex; align-items:center; justify-content:center;
                font-size:1.3rem; font-weight:800; color:white;">
                {focus_score}
            </div>
        </div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:6px;">
            ✅{score_tasks} 🍅{score_pomos} ✨{score_habits}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ====================================================
# САЙДБАР
# ====================================================

with st.sidebar:
    st.markdown('<div style="font-size:0.7rem; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;">Навигация</div>', unsafe_allow_html=True)
    section = st.radio("", [
        "📝 Планшет задач",
        "⏰ Тайм-блокинг",
        "🧠 Brain Dump",
        "😊 Дневник настроения",
        "✅ Привычки",
        "🎯 Цели",
        "🧩 База мыслей",
        "💰 Финансовый хаб",
        "🔄 Ретроспектива",
        "📊 Аналитика",
        "📈 Отчёт недели",
    ], label_visibility="collapsed")

    st.markdown("---")

    # Помодоро
    st.markdown('<div style="font-size:0.8rem; color:#7B3EFF; font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">⏱ Pomodoro</div>', unsafe_allow_html=True)

    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
    if "pomo_time" not in st.session_state:
        st.session_state.pomo_time = 25 * 60
    if "pomo_mode" not in st.session_state:
        st.session_state.pomo_mode = "Фокус"

    if not st.session_state.pomo_running:
        pomo_preset = st.selectbox("Режим", ["Фокус (25 мин)", "Короткий (15 мин)", "Глубокий (50 мин)", "Перерыв (5 мин)"], label_visibility="collapsed")
        preset_map = {"Фокус (25 мин)": 25*60, "Короткий (15 мин)": 15*60, "Глубокий (50 мин)": 50*60, "Перерыв (5 мин)": 5*60}
        st.session_state.pomo_time = preset_map[pomo_preset]

    pomo_box = st.empty()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("▶️", use_container_width=True, disabled=st.session_state.pomo_running):
            st.session_state.pomo_running = True
            st.rerun()
    with col_p2:
        if st.button("⏹️", use_container_width=True):
            st.session_state.pomo_running = False
            st.session_state.pomo_time = 25 * 60
            st.rerun()

    if st.session_state.pomo_running and st.session_state.pomo_time > 0:
        mins, secs = divmod(st.session_state.pomo_time, 60)
        total = 25 * 60
        pct = int((1 - st.session_state.pomo_time / total) * 100)
        pomo_box.markdown(f"""
        <div class="pomo-container">
            <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">🔥 Сессия активна</div>
            <div class="pomo-time">{mins:02d}:{secs:02d}</div>
            <div style="height:4px; background:rgba(255,255,255,0.07); border-radius:2px; margin-top:8px;">
                <div style="width:{pct}%; height:4px; background:linear-gradient(90deg,#3279FF,#7B3EFF); border-radius:2px; transition:width 1s;"></div>
            </div>
        </div>""", unsafe_allow_html=True)
        time.sleep(1)
        st.session_state.pomo_time -= 1
        st.rerun()
    else:
        if st.session_state.pomo_time == 0:
            st.session_state.pomo_running = False
            st.toast("🔔 Сессия фокуса завершена! Отдохните.", icon="🏆")
        mins, secs = divmod(st.session_state.pomo_time, 60)
        pomo_box.markdown(f"""
        <div class="pomo-container">
            <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">Готов к работе</div>
            <div class="pomo-time" style="color:#10b981;">{mins:02d}:{secs:02d}</div>
        </div>""", unsafe_allow_html=True)

    # Быстрые мысли в сайдбаре
    st.markdown("---")
    st.markdown('<div style="font-size:0.8rem; color:#06b6d4; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">💭 Быстрая мысль</div>', unsafe_allow_html=True)
    quick_thought = st.text_area("", placeholder="Запишите мысль...", height=80, label_visibility="collapsed", key="quick_thought")
    if st.button("→ Сохранить", use_container_width=True):
        if quick_thought.strip():
            add_brain_dump(quick_thought.strip())
            st.session_state.quick_thought = ""
            st.toast("💭 Мысль сохранена!", icon="✅")
            st.rerun()

    # Сегодняшний статус
    st.markdown("---")
    today_mood = get_today_mood()
    if today_mood:
        mood_e = MOOD_EMOJIS.get(today_mood['mood'], "😊")
        energy_e = ENERGY_EMOJIS.get(today_mood['energy'], "⚡")
        st.markdown(f"""
        <div style="background:rgba(236,72,153,0.06); border:1px solid rgba(236,72,153,0.15); border-radius:10px; padding:10px; text-align:center;">
            <div style="font-size:0.7rem; color:#94a3b8; margin-bottom:4px;">СЕГОДНЯ</div>
            <div style="font-size:1.2rem;">{mood_e} {energy_e}</div>
            <div style="font-size:0.7rem; color:#94a3b8;">настроение · энергия</div>
        </div>""", unsafe_allow_html=True)

# ====================================================
# РАЗДЕЛ 1: ПЛАНШЕТ ЗАДАЧ (УЛУЧШЕН)
# ====================================================

if section == "📝 Планшет задач":
    total_t = len(all_tasks)
    done_t = len([t for t in all_tasks if t["status"] == "Выполнено"])
    prog = done_t / total_t if total_t > 0 else 0.0
    active_t = total_t - done_t

    # Задачи с дедлайном сегодня
    overdue = [t for t in all_tasks if t.get('due_date') and t['due_date'] < today_str and t['status'] != 'Выполнено']
    due_today = [t for t in all_tasks if t.get('due_date') == today_str and t['status'] != 'Выполнено']

    if overdue:
        st.error(f"⚠️ Просрочено задач: **{len(overdue)}** — требует внимания!")
    if due_today:
        st.warning(f"📅 Дедлайн сегодня: **{len(due_today)} задачи** — не упустите!")

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card"><div class="kpi-label">Эффективность</div><div class="kpi-val">{int(prog*100)}%</div></div>
        <div class="kpi-card"><div class="kpi-label">Закрыто</div><div class="kpi-val" style="background:linear-gradient(135deg,#10b981,#6ee7b7);-webkit-background-clip:text;">{done_t}/{total_t}</div></div>
        <div class="kpi-card"><div class="kpi-label">Активных</div><div class="kpi-val" style="background:linear-gradient(135deg,#f59e0b,#fcd34d);-webkit-background-clip:text;">{active_t}</div></div>
        <div class="kpi-card"><div class="kpi-label">Просрочено</div><div class="kpi-val" style="background:linear-gradient(135deg,#f43f5e,#fb7185);-webkit-background-clip:text;">{len(overdue)}</div></div>
    </div>""", unsafe_allow_html=True)

    st.progress(prog)

    # Фильтры и поиск
    col_s, col_f1, col_f2, col_e = st.columns([2, 1, 1, 1])
    with col_s:
        search_q = st.text_input("🔍", placeholder="Поиск по задачам...", label_visibility="collapsed")
    with col_f1:
        filter_status = st.selectbox("Статус", ["Все", "В процессе", "Выполнено"], label_visibility="collapsed")
    with col_f2:
        filter_energy = st.selectbox("Энергия", ["Любая", "Высокий", "Средний", "Низкий"], label_visibility="collapsed")
    with col_e:
        sort_by = st.selectbox("Сортировка", ["По умолчанию", "По дедлайну", "По приоритету"], label_visibility="collapsed")

    # Форма добавления
    with st.expander("➕ Добавить новую задачу", expanded=False):
        with st.form("task_form", clear_on_submit=True):
            task_text = st.text_input("Название задачи *", placeholder="Например: Написать отчёт по проекту")
            col1, col2, col3 = st.columns(3)
            with col1:
                category = st.selectbox("Сфера", ["Работа", "Личное", "Учёба", "Спорт", "Другое"])
                priority = st.selectbox("Приоритет", ["Высокий 🔥", "Средний ⚡", "Низкий 🎯"])
            with col2:
                day_of_week = st.selectbox("День недели", DAYS_ORDER)
                energy_level = st.selectbox("Нужная энергия", ["Высокий", "Средний", "Низкий"])
            with col3:
                due_date = st.date_input("Дедлайн (опц.)", value=None)
                estimated_minutes = st.number_input("Оценка времени (мин)", min_value=0, max_value=480, value=30, step=15)
            task_notes = st.text_area("Заметки и контекст", height=80)
            task_tags = st.text_input("Теги (через запятую)", placeholder="проект, срочно, клиент")
            submitted = st.form_submit_button("✅ Добавить задачу", use_container_width=True)

    if submitted and task_text.strip():
        add_task(task_text.strip(), category, day_of_week, task_notes.strip(), priority,
                 due_date, estimated_minutes, task_tags.strip(), energy_level)
        st.rerun()

    # Рекомендатор по энергии
    today_mood_data = get_today_mood()
    if today_mood_data:
        curr_energy = today_mood_data['energy']
        if curr_energy <= 4:
            recommended_energy = "Низкий"
        elif curr_energy <= 7:
            recommended_energy = "Средний"
        else:
            recommended_energy = "Высокий"
        recommended = get_tasks_by_energy(recommended_energy)
        if recommended:
            with st.expander(f"⚡ Рекомендовано для вашей энергии ({recommended_energy}): {len(recommended)} задач"):
                for rt in recommended[:3]:
                    st.markdown(f"• **{rt['title']}** — {rt['category']}")

    # Применить фильтры
    filtered = all_tasks
    if search_q:
        filtered = [t for t in filtered if search_q.lower() in t['title'].lower() or search_q.lower() in (t.get('tags') or '').lower()]
    if filter_status != "Все":
        filtered = [t for t in filtered if t['status'] == filter_status]
    if filter_energy != "Любая":
        filtered = [t for t in filtered if t.get('energy_level') == filter_energy]
    if sort_by == "По дедлайну":
        filtered = sorted(filtered, key=lambda x: x.get('due_date') or '9999')
    elif sort_by == "По приоритету":
        prio_order = {"Высокий 🔥": 0, "Средний ⚡": 1, "Низкий 🎯": 2}
        filtered = sorted(filtered, key=lambda x: prio_order.get(x.get('priority', ''), 2))

    st.markdown(f'<div style="color:#94a3b8; font-size:0.85rem; margin-bottom:12px;">Показано {len(filtered)} задач</div>', unsafe_allow_html=True)

    if filtered:
        for t in filtered:
            is_done = t['status'] == 'Выполнено'
            is_overdue_task = t.get('due_date') and t['due_date'] < today_str and not is_done
            box_class = "task-box task-completed" if is_done else ("task-box task-overdue" if is_overdue_task else "task-box")
            prio = t.get('priority', 'Средний ⚡')
            prio_color = "#f43f5e" if "Высокий" in prio else ("#38bdf8" if "Средний" in prio else "#94a3b8")
            energy_icons = {"Высокий": "🔥", "Средний": "⚡", "Низкий": "🌿"}
            energy_icon = energy_icons.get(t.get('energy_level', 'Средний'), "⚡")

            # Оценка оставшегося времени
            due_display = ""
            if t.get('due_date'):
                days_diff = (datetime.strptime(t['due_date'], "%Y-%m-%d") - datetime.now()).days
                if is_done:
                    due_display = ""
                elif days_diff < 0:
                    due_display = f'<span class="badge" style="border-color:#f43f5e;color:#f43f5e;">⚠️ Просрочено {abs(days_diff)}д</span>'
                elif days_diff == 0:
                    due_display = '<span class="badge" style="border-color:#f59e0b;color:#f59e0b;">📅 Сегодня!</span>'
                else:
                    due_display = f'<span class="badge" style="border-color:#38bdf8;color:#38bdf8;">📅 {days_diff}д</span>'

            tags_html = ""
            if t.get('tags'):
                for tag in t['tags'].split(','):
                    tag = tag.strip()
                    if tag:
                        tags_html += f'<span class="badge" style="border-color:rgba(139,92,246,0.4);color:#c084fc;">#{tag}</span> '

            est_html = f'<span class="badge" style="color:#94a3b8;">⏱ {t["estimated_minutes"]}мин</span>' if t.get('estimated_minutes') else ""
            pomo_html = f'<span class="badge" style="border-color:rgba(255,75,75,0.4);color:#fca5a5;">🍅×{t["pomodoro_sessions"]}</span>' if t.get('pomodoro_sessions', 0) > 0 else ""

            with st.container():
                st.markdown(f"""
                <div class="{box_class}">
                    <div style="font-size:1.05rem; font-weight:600; color:{'#64748b' if is_done else '#fff'};
                        text-decoration:{'line-through' if is_done else 'none'}; margin-bottom:8px;">
                        {energy_icon} {t['title']}
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:6px;">
                        <span class="badge" style="border-color:{prio_color};color:{prio_color};">{prio}</span>
                        <span class="badge" style="color:#60a5fa;">🏷 {t['category']}</span>
                        <span class="badge" style="color:#c084fc;">📅 {t['day_of_week']}</span>
                        {due_display} {est_html} {pomo_html} {tags_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if t["status"] == "В процессе":
                        if st.button("✅ Закрыть", key=f"done_{t['id']}", use_container_width=True):
                            update_task_status(t['id'], "Выполнено")
                            st.rerun()
                    else:
                        if st.button("↩️ Вернуть", key=f"undo_{t['id']}", use_container_width=True):
                            update_task_status(t['id'], "В процессе")
                            st.rerun()
                with c2:
                    if st.button("🍅 +Pomodoro", key=f"pom_{t['id']}", use_container_width=True):
                        update_pomodoro_count(t['id'])
                        st.rerun()
                with c3:
                    if t.get("notes") and st.button("📖 Заметки", key=f"note_{t['id']}", use_container_width=True):
                        st.info(t["notes"])
                with c4:
                    if st.button("🗑️", key=f"del_{t['id']}", use_container_width=True):
                        delete_task(t['id'])
                        st.rerun()
                st.write("")
    else:
        st.info("📭 Задач не найдено по заданным фильтрам")

# ====================================================
# РАЗДЕЛ 2: ТАЙМ-БЛОКИНГ (НОВОЕ)
# ====================================================

elif section == "⏰ Тайм-блокинг":
    st.markdown('<div class="section-title">⏰ Тайм-блокинг</div>', unsafe_allow_html=True)

    # Выбор даты
    col_d, col_nav = st.columns([2, 1])
    with col_d:
        selected_date = st.date_input("Дата планирования", value=date.today())
    selected_date_str = selected_date.strftime("%Y-%m-%d")

    # Добавить блок
    with st.expander("➕ Добавить временной блок"):
        with st.form("time_block_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tb_title = st.text_input("Название блока", placeholder="Глубокая работа над проектом")
                tb_start = st.time_input("Начало", value=datetime.strptime("09:00", "%H:%M").time())
                tb_color = st.selectbox("Цвет", list(BLOCK_COLORS.keys()))
            with col2:
                tb_category = st.selectbox("Тип", ["Глубокая работа", "Встречи", "Обучение", "Перерыв", "Административное", "Личное", "Спорт"])
                tb_end = st.time_input("Конец", value=datetime.strptime("11:00", "%H:%M").time())
                # Привязка к задаче
                open_tasks = [t for t in all_tasks if t['status'] == 'В процессе']
                task_options = ["— Без привязки —"] + [f"{t['title'][:40]}" for t in open_tasks]
                tb_task_sel = st.selectbox("Привязать задачу", task_options)

            tb_submitted = st.form_submit_button("📌 Добавить блок", use_container_width=True)

        if tb_submitted and tb_title.strip():
            task_id = None
            if tb_task_sel != "— Без привязки —":
                idx = task_options.index(tb_task_sel) - 1
                task_id = open_tasks[idx]['id']
            add_time_block(tb_title.strip(), tb_start.strftime("%H:%M"), tb_end.strftime("%H:%M"),
                          selected_date_str, tb_category, tb_color, task_id)
            st.rerun()

    # Отображение расписания
    blocks = get_time_blocks(selected_date_str)

    # Заголовок дня
    day_name = selected_date.strftime("%A")
    day_names_ru = {"Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
                    "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"}
    day_ru = day_names_ru.get(day_name, day_name)
    total_planned_min = 0

    if blocks:
        for block in blocks:
            try:
                start_dt = datetime.strptime(block['start_time'], "%H:%M")
                end_dt = datetime.strptime(block['end_time'], "%H:%M")
                duration = int((end_dt - start_dt).seconds / 60)
                total_planned_min += duration
            except: duration = 0

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:20px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#fff;">📅 {day_ru}, {selected_date.strftime('%d.%m.%Y')}</div>
                <div style="display:flex; gap:12px; flex-wrap:wrap;">
                    <span class="badge" style="color:#a5b4fc;">⏱ {total_planned_min // 60}ч {total_planned_min % 60}мин запланировано</span>
                    <span class="badge" style="color:#6ee7b7;">{len([b for b in blocks if b['completed']])} / {len(blocks)} выполнено</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        for block in blocks:
            color = BLOCK_COLORS.get(block['color'], '#3b82f6')
            opacity = "0.4" if block['completed'] else "1"
            try:
                st_dt = datetime.strptime(block['start_time'], "%H:%M")
                en_dt = datetime.strptime(block['end_time'], "%H:%M")
                dur = int((en_dt - st_dt).seconds / 60)
                dur_text = f"{dur}мин" if dur < 60 else f"{dur//60}ч {dur%60}мин" if dur%60 else f"{dur//60}ч"
            except: dur_text = ""

            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:12px; padding:10px 14px; margin-bottom:8px;
                background:rgba(255,255,255,0.03); border-radius:10px;
                border-left: 3px solid {color}; opacity:{opacity};">
                <div style="color:{color}; font-size:0.85rem; font-weight:700; min-width:90px; font-family:monospace;">
                    {block['start_time']} – {block['end_time']}
                </div>
                <div style="flex:1;">
                    <div style="font-weight:600; color:#fff; text-decoration:{'line-through' if block['completed'] else 'none'};">
                        {block['title']}
                    </div>
                    <div style="font-size:0.78rem; color:#64748b; margin-top:2px;">{block['category']} · {dur_text}</div>
                </div>
                {'<span style="color:#10b981; font-size:1.1rem;">✓</span>' if block['completed'] else ''}
            </div>
            """, unsafe_allow_html=True)

            cb1, cb2 = st.columns([1, 4])
            with cb1:
                if st.button("✓" if not block['completed'] else "↩", key=f"tb_done_{block['id']}", use_container_width=True):
                    toggle_time_block(block['id'])
                    st.rerun()
            with cb2:
                if st.button("🗑️", key=f"tb_del_{block['id']}", use_container_width=True):
                    delete_time_block(block['id'])
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Статистика занятости
        busy_hours = total_planned_min / 60
        free_hours = 16 - busy_hours  # предполагаем 16 рабочих часов
        st.markdown(f"""
        <div class="insight-box">
            <div style="font-size:0.85rem; color:#94a3b8;">📊 Загрузка дня</div>
            <div style="display:flex; gap:16px; margin-top:8px; flex-wrap:wrap;">
                <span style="color:#3279FF; font-weight:600;">🔵 Занято: {busy_hours:.1f}ч</span>
                <span style="color:#10b981; font-weight:600;">🟢 Свободно: {free_hours:.1f}ч</span>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("📅 На этот день нет запланированных блоков. Добавьте первый выше!")

# ====================================================
# РАЗДЕЛ 3: BRAIN DUMP (НОВОЕ)
# ====================================================

elif section == "🧠 Brain Dump":
    st.markdown('<div class="section-title">🧠 Brain Dump — Разгрузка сознания</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="insight-box" style="margin-bottom:20px;">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            💡 <strong>Brain Dump</strong> — техника для выгрузки всех мыслей из головы.
            Запишите всё что беспокоит, крутится в голове или требует обдумывания.
            Потом обработайте каждый пункт: преобразуйте в задачу, заметку или удалите.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Быстрая запись
    with st.form("brain_dump_form", clear_on_submit=True):
        dump_content = st.text_area("Выгрузите мысль...", height=120,
            placeholder="Позвонить Ивану по поводу проекта...\nКупить подарок маме...\nПодумать над новой фичей...")
        bd_submitted = st.form_submit_button("🧠 Зафиксировать", use_container_width=True)

    if bd_submitted and dump_content.strip():
        # Разбить по строкам и сохранить каждую мысль
        lines = [l.strip() for l in dump_content.strip().split('\n') if l.strip()]
        for line in lines:
            add_brain_dump(line)
        st.success(f"✅ Сохранено {len(lines)} мыслей!")
        st.rerun()

    unprocessed = get_brain_dump_items(processed=0)
    processed = get_brain_dump_items(processed=1)

    col_u, col_p = st.columns([2, 1])
    with col_u:
        st.markdown(f'<div style="font-size:1rem; font-weight:700; color:#f59e0b; margin-bottom:12px;">⚡ Необработано ({len(unprocessed)})</div>', unsafe_allow_html=True)

        if unprocessed:
            for item in unprocessed:
                with st.container():
                    st.markdown(f"""
                    <div class="brain-item">
                        <div style="color:#fff; font-size:0.95rem;">{item['content']}</div>
                        <div style="color:#64748b; font-size:0.72rem; margin-top:4px;">🕒 {item['created_at']}</div>
                    </div>""", unsafe_allow_html=True)

                    cb1, cb2, cb3, cb4 = st.columns(4)
                    with cb1:
                        if st.button("📝→Задача", key=f"bd_task_{item['id']}", use_container_width=True):
                            add_task(item['content'], "Личное", "Понедельник", "Из Brain Dump", "Средний ⚡")
                            process_brain_dump(item['id'], "Задача")
                            st.toast("✅ Добавлено как задача!")
                            st.rerun()
                    with cb2:
                        if st.button("📌→Заметка", key=f"bd_note_{item['id']}", use_container_width=True):
                            add_note("Мысль из Brain Dump", item['content'], "Идеи")
                            process_brain_dump(item['id'], "Заметка")
                            st.toast("📌 Сохранено как заметка!")
                            st.rerun()
                    with cb3:
                        if st.button("✅ Готово", key=f"bd_done_{item['id']}", use_container_width=True):
                            process_brain_dump(item['id'], "Обработано")
                            st.rerun()
                    with cb4:
                        if st.button("🗑️", key=f"bd_del_{item['id']}", use_container_width=True):
                            delete_brain_dump(item['id'])
                            st.rerun()
                    st.write("")
        else:
            st.success("🌟 Голова свободна! Нет необработанных мыслей.")

    with col_p:
        st.markdown(f'<div style="font-size:1rem; font-weight:700; color:#10b981; margin-bottom:12px;">✅ Обработано ({len(processed)})</div>', unsafe_allow_html=True)
        if processed:
            category_counts = {}
            for p in processed:
                cat = p.get('category', 'Прочее')
                category_counts[cat] = category_counts.get(cat, 0) + 1
            for cat, cnt in category_counts.items():
                st.markdown(f"""
                <div style="background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.15);
                    border-radius:8px; padding:8px 12px; margin-bottom:6px;">
                    <span style="color:#6ee7b7; font-weight:600;">{cat}</span>
                    <span style="color:#94a3b8; font-size:0.85rem;"> × {cnt}</span>
                </div>""", unsafe_allow_html=True)

# ====================================================
# РАЗДЕЛ 4: ДНЕВНИК НАСТРОЕНИЯ (НОВОЕ)
# ====================================================

elif section == "😊 Дневник настроения":
    st.markdown('<div class="section-title">😊 Дневник настроения и энергии</div>', unsafe_allow_html=True)

    today_m = get_today_mood()

    col_form, col_history = st.columns([1, 1])

    with col_form:
        if today_m:
            mood_e = MOOD_EMOJIS.get(today_m['mood'], "😊")
            energy_e = ENERGY_EMOJIS.get(today_m['energy'], "⚡")
            st.markdown(f"""
            <div class="mood-card">
                <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:8px;">СЕГОДНЯ УЖЕ ЗАПИСАНО</div>
                <div style="display:flex; gap:24px; align-items:center;">
                    <div style="text-align:center;">
                        <div style="font-size:2rem;">{mood_e}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">Настроение {today_m['mood']}/10</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:2rem;">{energy_e}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">Энергия {today_m['energy']}/10</div>
                    </div>
                    <div style="flex:1; font-size:0.85rem; color:#cbd5e1; font-style:italic;">
                        "{today_m.get('notes', '')[:80]}"
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            st.caption("Вы уже записали настроение сегодня. Можете обновить:")

        with st.form("mood_form", clear_on_submit=False):
            st.markdown("**Как вы себя чувствуете сегодня?**")
            mood_val = st.slider("😊 Настроение", 1, 10, today_m['mood'] if today_m else 7,
                help="1 = Ужасно, 10 = Превосходно")
            energy_val = st.slider("⚡ Уровень энергии", 1, 10, today_m['energy'] if today_m else 7,
                help="1 = Полностью без сил, 10 = Готов свернуть горы")
            mood_notes = st.text_area("Что влияет на ваше состояние?",
                value=today_m.get('notes', '') if today_m else "",
                placeholder="Хорошо поспал, продуктивное утро...", height=80)
            mood_tags = st.text_input("Теги (через запятую)", value=today_m.get('tags', '') if today_m else "",
                placeholder="сфокусирован, тревожно, счастлив")
            mood_submitted = st.form_submit_button("💾 Сохранить состояние", use_container_width=True)

        if mood_submitted:
            add_mood_entry(mood_val, energy_val, mood_notes.strip(), mood_tags.strip())
            st.success(f"{MOOD_EMOJIS.get(mood_val, '😊')} Сохранено!")
            st.rerun()

    with col_history:
        mood_history = get_mood_history(14)
        if mood_history:
            st.markdown("**📈 Динамика за 14 дней**")

            # Таблица данных для графика
            chart_data = pd.DataFrame([{
                'Дата': m['date'][-5:],
                'Настроение': m['mood'],
                'Энергия': m['energy']
            } for m in mood_history]).set_index('Дата')
            st.line_chart(chart_data, color=["#ec4899", "#3279FF"])

            # Средние значения
            avg_mood = sum(m['mood'] for m in mood_history) / len(mood_history)
            avg_energy = sum(m['energy'] for m in mood_history) / len(mood_history)
            best_day = max(mood_history, key=lambda x: x['mood'])

            st.markdown(f"""
            <div class="insight-box">
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; text-align:center;">
                    <div>
                        <div style="font-size:1.4rem;">{MOOD_EMOJIS.get(round(avg_mood), '😊')}</div>
                        <div style="font-size:0.7rem; color:#94a3b8;">Среднее настроение</div>
                        <div style="font-weight:700; color:#ec4899;">{avg_mood:.1f}</div>
                    </div>
                    <div>
                        <div style="font-size:1.4rem;">{ENERGY_EMOJIS.get(round(avg_energy), '⚡')}</div>
                        <div style="font-size:0.7rem; color:#94a3b8;">Средняя энергия</div>
                        <div style="font-weight:700; color:#3279FF;">{avg_energy:.1f}</div>
                    </div>
                    <div>
                        <div style="font-size:1.4rem;">🌟</div>
                        <div style="font-size:0.7rem; color:#94a3b8;">Лучший день</div>
                        <div style="font-weight:700; color:#10b981;">{best_day['date'][-5:]}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

            # Последние записи
            st.markdown("**📝 Последние записи:**")
            for m in reversed(mood_history[-4:]):
                me = MOOD_EMOJIS.get(m['mood'], '😊')
                ee = ENERGY_EMOJIS.get(m['energy'], '⚡')
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:8px 12px; margin-bottom:6px; display:flex; align-items:center; gap:10px;">
                    <span style="font-family:monospace; color:#64748b; font-size:0.8rem; min-width:50px;">{m['date'][-5:]}</span>
                    <span>{me}{ee}</span>
                    <span style="color:#94a3b8; font-size:0.82rem; flex:1;">{(m.get('notes') or '')[:50]}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📊 Начните вести дневник настроения для отображения статистики")

# ====================================================
# РАЗДЕЛ 5: ПРИВЫЧКИ (УЛУЧШЕН)
# ====================================================

elif section == "✅ Привычки":
    st.markdown('<div class="section-title">✅ Трекер привычек</div>', unsafe_allow_html=True)

    habits = get_all_habits()

    # KPI привычек
    if habits:
        today_done_habits = 0
        total_streak = 0
        for h in habits:
            streak = get_habit_streak(h['id'])
            total_streak += streak
            rate = get_habit_completion_rate(h['id'], 7)
            if rate > 0:
                today_done_habits += 1

        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card"><div class="kpi-label">Привычек</div><div class="kpi-val">{len(habits)}</div></div>
            <div class="kpi-card"><div class="kpi-label">Суммарный стрик</div><div class="kpi-val" style="background:linear-gradient(135deg,#f59e0b,#fcd34d);-webkit-background-clip:text;">{total_streak}🔥</div></div>
        </div>""", unsafe_allow_html=True)

    with st.expander("➕ Добавить привычку"):
        with st.form("habit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                habit_name = st.text_input("Название привычки", placeholder="Медитация 10 минут")
                habit_category = st.selectbox("Категория", ["Здоровье", "Обучение", "Продуктивность", "Спорт", "Разное"])
            with col2:
                habit_frequency = st.selectbox("Частота", ["Ежедневно", "5 раз в неделю", "3 раза в неделю", "По выходным"])
                habit_goal = st.number_input("Целевое количество/повторений", min_value=1, max_value=100, value=1)
            habit_submitted = st.form_submit_button("✅ Добавить привычку", use_container_width=True)

    if habit_submitted and habit_name.strip():
        add_habit(habit_name.strip(), habit_category, habit_frequency, habit_goal)
        st.rerun()

    today_date = datetime.now().strftime("%Y-%m-%d")

    if habits:
        for habit in habits:
            streak = get_habit_streak(habit['id'])
            rate_30 = get_habit_completion_rate(habit['id'], 30)
            rate_7 = get_habit_completion_rate(habit['id'], 7)
            heatmap = get_habit_heatmap_data(habit['id'], 28)

            # Тепловая карта 4 недели
            heat_cells = ""
            for i in range(27, -1, -1):
                d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                done = heatmap.get(d, None)
                if done == 1:
                    color = "#22c55e"
                elif done == 0:
                    color = "#f43f5e44"
                else:
                    color = "rgba(255,255,255,0.05)"
                heat_cells += f'<span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{color};margin:1px;" title="{d}"></span>'

            with st.container():
                st.markdown(f"""
                <div class="habit-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
                        <div>
                            <div style="font-size:1.05rem; font-weight:700; color:#fff;">{habit['name']}</div>
                            <div style="font-size:0.8rem; color:#94a3b8; margin-top:2px;">
                                {habit['category']} · {habit['frequency']}
                            </div>
                        </div>
                        <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
                            <div style="text-align:center;">
                                <div style="font-size:1.4rem; font-weight:800; color:#22c55e;">🔥 {streak}</div>
                                <div style="font-size:0.68rem; color:#94a3b8;">стрик дней</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:1.1rem; font-weight:700; color:#3279FF;">{rate_7}%</div>
                                <div style="font-size:0.68rem; color:#94a3b8;">за 7 дней</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:1.1rem; font-weight:700; color:#a5b4fc;">{rate_30}%</div>
                                <div style="font-size:0.68rem; color:#94a3b8;">за 30 дней</div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-bottom:4px; font-size:0.72rem; color:#64748b;">28 дней:</div>
                    <div style="line-height:1;">{heat_cells}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button(f"✅ Выполнено", key=f"h_done_{habit['id']}", use_container_width=True):
                        log_habit(habit['id'], today_date, True)
                        st.toast(f"🔥 {habit['name']} — выполнено!")
                        st.rerun()
                with c2:
                    if st.button("⏭️ Пропустить", key=f"h_skip_{habit['id']}", use_container_width=True):
                        log_habit(habit['id'], today_date, False)
                        st.rerun()
                with c3:
                    if st.button("🗑️ Удалить", key=f"h_del_{habit['id']}", use_container_width=True):
                        delete_habit(habit['id'])
                        st.rerun()
                st.write("")
    else:
        st.info("🌱 Нет привычек. Создайте первую!")

# ====================================================
# РАЗДЕЛ 6: ЦЕЛИ (УЛУЧШЕН)
# ====================================================

elif section == "🎯 Цели":
    st.markdown('<div class="section-title">🎯 Система целей и вех</div>', unsafe_allow_html=True)

    goals = get_all_goals()

    with st.expander("➕ Создать новую цель"):
        with st.form("goal_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                goal_title = st.text_input("Название цели *", placeholder="Запустить стартап")
                goal_category = st.selectbox("Категория", ["Бизнес", "Карьера", "Личное развитие", "Здоровье", "Финансы", "Отношения", "Хобби"])
                goal_priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
            with col2:
                goal_target = st.date_input("Целевая дата")
                goal_desc = st.text_area("Описание и «зачем»", height=80, placeholder="Опишите цель и мотивацию...")
            goal_submitted = st.form_submit_button("🎯 Создать цель", use_container_width=True)

    if goal_submitted and goal_title.strip():
        add_goal(goal_title.strip(), goal_desc.strip(), goal_category, goal_target.strftime("%Y-%m-%d"), goal_priority)
        st.rerun()

    if goals:
        active_goals = [g for g in goals if g['status'] == 'Активна']
        completed_goals = [g for g in goals if g['status'] == 'Завершена']

        # Обзор
        if active_goals:
            avg_progress = sum(g['progress'] for g in active_goals) / len(active_goals)
            st.markdown(f"""
            <div class="insight-box" style="margin-bottom:20px;">
                <div style="display:flex; gap:24px; align-items:center; flex-wrap:wrap;">
                    <div><span style="color:#94a3b8; font-size:0.8rem;">Активных целей:</span>
                        <span style="color:#fb923c; font-weight:700; font-size:1.1rem; margin-left:6px;">{len(active_goals)}</span></div>
                    <div><span style="color:#94a3b8; font-size:0.8rem;">Средний прогресс:</span>
                        <span style="color:#3279FF; font-weight:700; font-size:1.1rem; margin-left:6px;">{avg_progress:.0f}%</span></div>
                    <div><span style="color:#94a3b8; font-size:0.8rem;">Завершено:</span>
                        <span style="color:#10b981; font-weight:700; font-size:1.1rem; margin-left:6px;">{len(completed_goals)}</span></div>
                </div>
            </div>""", unsafe_allow_html=True)

        if active_goals:
            st.markdown("### 🚀 Активные цели")
            for goal in active_goals:
                days_left = (datetime.strptime(goal['target_date'], "%Y-%m-%d") - datetime.now()).days
                prio_c = {"Высокий": "#f43f5e", "Средний": "#f59e0b", "Низкий": "#94a3b8"}.get(goal.get('priority', 'Средний'), '#94a3b8')

                # Вехи
                try:
                    milestones = json.loads(goal.get('milestones', '[]'))
                except: milestones = []

                with st.container():
                    st.markdown(f"""
                    <div class="goal-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
                            <div style="flex:1; min-width:0;">
                                <div style="font-size:1.05rem; font-weight:700; color:#fff; word-break:break-word;">{goal['title']}</div>
                                <div style="font-size:0.82rem; color:#94a3b8; margin-top:3px;">{(goal.get('description') or '')[:80]}</div>
                            </div>
                            <div style="text-align:right; flex-shrink:0;">
                                <span class="badge" style="border-color:{prio_c}; color:{prio_c};">{goal.get('priority','')}</span>
                                <span class="badge" style="color:#fb923c; margin-left:4px;">{goal['category']}</span>
                                <div style="font-size:0.75rem; margin-top:4px; font-weight:600; color:{'#f43f5e' if days_left < 0 else '#10b981' if days_left > 30 else '#f59e0b'}">
                                    {'⚠️ Просрочено!' if days_left < 0 else f'📅 {days_left} дней осталось'}
                                </div>
                            </div>
                        </div>
                        <div style="background:rgba(0,0,0,0.3); border-radius:6px; height:8px; margin-bottom:6px; overflow:hidden;">
                            <div style="width:{goal['progress']}%; height:8px; background:linear-gradient(90deg,#f59e0b,#ef4444); border-radius:6px; transition:width 0.5s;"></div>
                        </div>
                        <div style="font-size:0.78rem; color:#94a3b8;">{goal['progress']}% выполнено</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Вехи
                    if milestones:
                        st.markdown("**📍 Вехи:**")
                        for i, ms in enumerate(milestones):
                            mc1, mc2 = st.columns([4, 1])
                            with mc1:
                                done_ms = ms.get('done', False)
                                st.markdown(f"{'~~' if done_ms else ''}{ms['text']}{'~~' if done_ms else ''} {'✅' if done_ms else '○'}")
                            with mc2:
                                if st.button("✓" if not ms.get('done') else "↩", key=f"ms_{goal['id']}_{i}", use_container_width=True):
                                    milestones[i]['done'] = not ms.get('done', False)
                                    update_goal_milestones(goal['id'], milestones)
                                    # Автообновление прогресса
                                    done_count = sum(1 for m in milestones if m.get('done'))
                                    auto_progress = int(done_count / len(milestones) * 100)
                                    update_goal_progress(goal['id'], auto_progress)
                                    st.rerun()

                    # Добавить веху
                    with st.expander(f"➕ Добавить веху к цели"):
                        new_ms = st.text_input("Название вехи", key=f"new_ms_{goal['id']}", placeholder="Например: Написать бизнес-план")
                        if st.button("Добавить веху", key=f"add_ms_{goal['id']}", use_container_width=True):
                            if new_ms.strip():
                                milestones.append({'text': new_ms.strip(), 'done': False})
                                update_goal_milestones(goal['id'], milestones)
                                st.rerun()

                    gc1, gc2, gc3 = st.columns(3)
                    with gc1:
                        new_prog = st.slider("Прогресс %", 0, 100, goal['progress'], key=f"gp_{goal['id']}")
                    with gc2:
                        if st.button("💾 Сохранить", key=f"gs_{goal['id']}", use_container_width=True):
                            update_goal_progress(goal['id'], new_prog)
                            st.rerun()
                    with gc3:
                        if st.button("🗑️ Удалить", key=f"gd_{goal['id']}", use_container_width=True):
                            delete_goal(goal['id'])
                            st.rerun()
                    st.write("")

        if completed_goals:
            with st.expander(f"🏆 Завершённые цели ({len(completed_goals)})"):
                for goal in completed_goals:
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2);
                        border-radius:10px; padding:10px 14px; margin-bottom:8px;">
                        <span style="color:#6ee7b7; font-weight:600;">🏆 {goal['title']}</span>
                        <span class="badge" style="color:#94a3b8; margin-left:8px;">{goal['category']}</span>
                    </div>""", unsafe_allow_html=True)
    else:
        st.info("🎯 Нет активных целей. Создайте первую!")

# ====================================================
# РАЗДЕЛ 7: БАЗА МЫСЛЕЙ (УЛУЧШЕНА)
# ====================================================

elif section == "🧩 База мыслей":
    st.markdown('<div class="section-title">🧩 База мыслей и знаний</div>', unsafe_allow_html=True)

    # Поиск по заметкам
    notes_search = st.text_input("🔍 Поиск по заметкам", placeholder="Введите ключевое слово...")

    col_n1, col_n2 = st.columns([2, 1])
    with col_n1:
        with st.form("note_form", clear_on_submit=True):
            note_title = st.text_input("Заголовок", placeholder="Название идеи или инсайта")
            col_nt1, col_nt2 = st.columns(2)
            with col_nt1:
                note_tag = st.selectbox("Тег", ["Идеи", "Инсайты", "Учёба", "Проекты", "Цитаты", "Разное"])
            with col_nt2:
                note_color = st.selectbox("Цвет карточки", list(NOTE_COLORS.keys()))
            note_content = st.text_area("Содержание (поддерживает Markdown)", height=150)
            note_submitted = st.form_submit_button("📌 Сохранить заметку", use_container_width=True)

        if note_submitted and note_content.strip():
            add_note(note_title.strip() or "Без заголовка", note_content.strip(), note_tag, note_color)
            st.rerun()

    with col_n2:
        saved_notes = get_all_notes()
        tags_count = {}
        for n in saved_notes:
            t = n.get('tag', 'Разное')
            tags_count[t] = tags_count.get(t, 0) + 1

        st.markdown("**📊 Теги:**")
        for tag, cnt in sorted(tags_count.items(), key=lambda x: -x[1]):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:4px 10px; background:rgba(255,255,255,0.03); border-radius:6px; margin-bottom:4px;">
                <span style="color:#a5b4fc;">📌 {tag}</span>
                <span class="badge" style="color:#94a3b8;">{cnt}</span>
            </div>""", unsafe_allow_html=True)

    # Показать заметки
    saved_notes = get_all_notes()
    if notes_search:
        saved_notes = [n for n in saved_notes if notes_search.lower() in n['title'].lower() or notes_search.lower() in n['content'].lower()]

    if saved_notes:
        pinned = [n for n in saved_notes if n.get('pinned')]
        unpinned = [n for n in saved_notes if not n.get('pinned')]

        for notes_group, label in [(pinned, "📌 Закреплённые"), (unpinned, "📝 Все заметки")]:
            if notes_group:
                st.markdown(f"**{label}:**")
                for note in notes_group:
                    bg, border = NOTE_COLORS.get(note.get('color', 'default'), NOTE_COLORS['default'])
                    pin_icon = "📌" if note.get('pinned') else ""
                    with st.container():
                        st.markdown(f"""
                        <div style="background:{bg}; border:1px solid {border}; border-radius:14px; padding:14px 16px; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                                <span style="font-size:1rem; font-weight:700; color:#a5b4fc;">{pin_icon} {note['title']}</span>
                                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                                    <span class="badge" style="color:#94a3b8;">🕒 {note['created_at']}</span>
                                    <span class="badge" style="color:#c084fc;">📌 {note['tag']}</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(note['content'])

                        nc1, nc2 = st.columns(2)
                        with nc1:
                            if st.button("📌 Закрепить" if not note.get('pinned') else "📌 Открепить",
                                        key=f"pin_{note['id']}", use_container_width=True):
                                toggle_pin_note(note['id'], note.get('pinned', 0))
                                st.rerun()
                        with nc2:
                            if st.button("🗑️ Удалить", key=f"del_n_{note['id']}", use_container_width=True):
                                delete_note(note['id'])
                                st.rerun()
                        st.write("")
    else:
        st.info("💡 Нет заметок. Создайте первую!")

# ====================================================
# РАЗДЕЛ 8: ФИНАНСОВЫЙ ХАБ (УЛУЧШЕН)
# ====================================================

elif section == "💰 Финансовый хаб":
    st.markdown('<div class="section-title">💰 Финансовый хаб</div>', unsafe_allow_html=True)

    transactions = get_all_transactions()
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'Доход')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'Расход')
    balance = total_income - total_expense
    savings_rate = (balance / total_income * 100) if total_income > 0 else 0

    balance_color = "#10b981" if balance >= 0 else "#f43f5e"
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card"><div class="kpi-label">Баланс</div>
            <div class="kpi-val" style="background:linear-gradient(135deg,{balance_color},{'#34d399' if balance>=0 else '#fb7185'});-webkit-background-clip:text;">{balance:,.0f} ₸</div></div>
        <div class="kpi-card"><div class="kpi-label">Доходы</div>
            <div class="kpi-val" style="background:linear-gradient(135deg,#3279FF,#60a5fa);-webkit-background-clip:text;">{total_income:,.0f} ₸</div></div>
        <div class="kpi-card"><div class="kpi-label">Расходы</div>
            <div class="kpi-val" style="background:linear-gradient(135deg,#f43f5e,#fb7185);-webkit-background-clip:text;">{total_expense:,.0f} ₸</div></div>
        <div class="kpi-card"><div class="kpi-label">Норма сбережений</div>
            <div class="kpi-val" style="background:linear-gradient(135deg,#f59e0b,#fcd34d);-webkit-background-clip:text;">{savings_rate:.0f}%</div></div>
    </div>""", unsafe_allow_html=True)

    # Быстрый анализ по категориям
    if transactions:
        expenses_by_cat = {}
        income_by_cat = {}
        for t in transactions:
            if t['type'] == 'Расход':
                expenses_by_cat[t['category']] = expenses_by_cat.get(t['category'], 0) + t['amount']
            else:
                income_by_cat[t['category']] = income_by_cat.get(t['category'], 0) + t['amount']

        col_exp, col_inc = st.columns(2)
        with col_exp:
            if expenses_by_cat:
                top_expense = max(expenses_by_cat, key=expenses_by_cat.get)
                st.markdown(f"""
                <div class="insight-box">
                    <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:6px;">💸 Топ расход</div>
                    <div style="color:#fb7185; font-weight:700;">{top_expense}</div>
                    <div style="color:#fff; font-size:1.1rem; font-weight:700;">{expenses_by_cat[top_expense]:,.0f} ₸</div>
                </div>""", unsafe_allow_html=True)
        with col_inc:
            if income_by_cat:
                top_income = max(income_by_cat, key=income_by_cat.get)
                st.markdown(f"""
                <div class="insight-box">
                    <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:6px;">💰 Топ доход</div>
                    <div style="color:#6ee7b7; font-weight:700;">{top_income}</div>
                    <div style="color:#fff; font-size:1.1rem; font-weight:700;">{income_by_cat[top_income]:,.0f} ₸</div>
                </div>""", unsafe_allow_html=True)

    with st.form("finance_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            t_type = st.radio("Тип", ["Доход", "Расход"], horizontal=True)
            amount = st.number_input("Сумма (₸)", min_value=0.0, step=1000.0)
            recurring = st.checkbox("Повторяющийся платёж")
        with col2:
            category = st.selectbox("Категория", ["Зарплата/Оклад 💼", "Бизнес/SaaS 🚀", "Фриланс 💻", "Инвестиции 📈",
                "Серверы/IT 🌐", "Маркетинг 📊", "Питание 🍕", "Транспорт 🚗", "Здоровье 🏥",
                "Обучение 📚", "Развлечения 🎮", "Личное 🛍", "Другое 💎"])
            description = st.text_input("Описание", placeholder="Комментарий...")
            rec_period = st.selectbox("Период", ["Ежемесячно", "Еженедельно", "Ежегодно"]) if recurring else ""
        fin_submitted = st.form_submit_button("💾 Зарегистрировать", use_container_width=True)

    if fin_submitted and amount > 0:
        add_transaction(t_type, amount, category, description.strip(), recurring, rec_period)
        st.rerun()

    # Фильтр транзакций
    if transactions:
        col_ftype, col_fcat = st.columns(2)
        with col_ftype:
            ftype = st.selectbox("Тип", ["Все", "Доход", "Расход"])
        with col_fcat:
            all_cats = list(set(t['category'] for t in transactions))
            fcat = st.selectbox("Категория", ["Все"] + all_cats)

        filtered_trans = transactions
        if ftype != "Все":
            filtered_trans = [t for t in filtered_trans if t['type'] == ftype]
        if fcat != "Все":
            filtered_trans = [t for t in filtered_trans if t['category'] == fcat]

        st.markdown(f'### 📜 История ({len(filtered_trans)} операций)')
        for t in filtered_trans:
            color = "#10b981" if t['type'] == "Доход" else "#f43f5e"
            prefix = "+" if t['type'] == "Доход" else "−"
            rec_badge = ' <span class="badge" style="color:#f59e0b;">🔄 Регулярный</span>' if t.get('recurring') else ""
            with st.container():
                st.markdown(f"""
                <div class="finance-row">
                    <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap; flex:1; min-width:0;">
                        <span class="badge" style="border-color:{color}; color:{color};">{t['type']}</span>
                        <span style="font-weight:600;">{t['category']}</span>
                        <span style="color:#94a3b8; font-size:0.82rem;">— {t.get('description', '')}</span>
                        {rec_badge}
                    </div>
                    <div style="text-align:right; flex-shrink:0;">
                        <div style="color:{color}; font-weight:700; font-size:1.05rem;">{prefix}{t['amount']:,.0f} ₸</div>
                        <div style="font-size:0.7rem; color:#64748b;">{t['date']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
                if st.button("🗑️", key=f"df_{t['id']}", use_container_width=True):
                    delete_transaction(t['id'])
                    st.rerun()
                st.write("")

# ====================================================
# РАЗДЕЛ 9: РЕТРОСПЕКТИВА (НОВОЕ)
# ====================================================

elif section == "🔄 Ретроспектива":
    st.markdown('<div class="section-title">🔄 Ретроспектива и рефлексия</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="insight-box" style="margin-bottom:20px;">
        <div style="font-size:0.9rem; color:#cbd5e1;">
            🔄 <strong>Ретроспектива</strong> — регулярный процесс рефлексии для постоянного улучшения.
            Анализируйте прошедшую неделю/месяц: что сработало, что нет, и что изменить.
        </div>
    </div>""", unsafe_allow_html=True)

    with st.form("review_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            review_type = st.selectbox("Тип ретроспективы", ["🗓 Еженедельная", "📅 Ежемесячная", "📆 Квартальная", "🎯 По проекту"])
            review_rating = st.slider("Общая оценка периода", 1, 10, 7)
        with col2:
            st.markdown("**Формат «Что сработало / Что нет / Что изменить»**")

        rev_wins = st.text_area("🏆 Победы и достижения", height=80,
            placeholder="Завершил проект X, улучшил навык Y, завёл полезную привычку...")
        rev_challenges = st.text_area("🚧 Трудности и препятствия", height=80,
            placeholder="Потерял фокус в середине недели, прокрастинировал задачу Z...")
        rev_insights = st.text_area("💡 Ключевые инсайты", height=80,
            placeholder="Понял что утром работаю эффективнее, важно планировать вечером...")
        rev_actions = st.text_area("➡️ Действия на следующий период", height=80,
            placeholder="Внедрить утренний ритуал, ограничить соцсети до 30мин/день...")
        rev_submitted = st.form_submit_button("💾 Сохранить ретроспективу", use_container_width=True)

    if rev_submitted:
        add_review(review_type, rev_wins, rev_challenges, rev_insights, rev_actions, review_rating)
        st.success("✅ Ретроспектива сохранена!")
        st.rerun()

    # История ретроспектив
    reviews = get_all_reviews()
    if reviews:
        st.markdown("### 📚 История ретроспектив")
        for rev in reviews:
            rating_stars = "⭐" * rev['rating'] + "·" * (10 - rev['rating'])
            with st.expander(f"{rev['type']} — {rev['date']} | {rating_stars[:rev['rating']]} ({rev['rating']}/10)"):
                if rev.get('wins'):
                    st.markdown(f"**🏆 Победы:** {rev['wins']}")
                if rev.get('challenges'):
                    st.markdown(f"**🚧 Трудности:** {rev['challenges']}")
                if rev.get('insights'):
                    st.markdown(f"**💡 Инсайты:** {rev['insights']}")
                if rev.get('next_actions'):
                    st.markdown(f"**➡️ Действия:** {rev['next_actions']}")
    else:
        st.info("📝 Нет сохранённых ретроспектив. Проведите первую!")

# ====================================================
# РАЗДЕЛ 10: АНАЛИТИКА (УЛУЧШЕНА)
# ====================================================

elif section == "📊 Аналитика":
    st.markdown('<div class="section-title">📊 Аналитика продуктивности</div>', unsafe_allow_html=True)

    tasks_data = get_all_tasks_raw()
    mood_data = get_mood_history(30)
    focus_scores = get_focus_score_history(14)

    if tasks_data:
        df = pd.DataFrame(tasks_data)

        # Счёт фокуса по дням
        if focus_scores:
            st.markdown("#### ⚡ Счёт Фокуса — динамика (14 дней)")
            fs_df = pd.DataFrame(focus_scores).set_index('date')[['score']]
            st.area_chart(fs_df, color=["#3279FF"])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🎯 Задачи по категориям")
            if "category" in df.columns:
                st.bar_chart(df["category"].value_counts())
        with col2:
            st.markdown("#### ⚡ Статусы задач")
            if "status" in df.columns:
                st.bar_chart(df["status"].value_counts())

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### 🔥 По приоритету")
            if "priority" in df.columns:
                st.bar_chart(df["priority"].value_counts())
        with col4:
            st.markdown("#### 🌿 По уровню энергии")
            if "energy_level" in df.columns:
                st.bar_chart(df["energy_level"].value_counts())

        # Динамика настроения
        if mood_data:
            st.markdown("#### 😊 Настроение и энергия (30 дней)")
            mood_df = pd.DataFrame([{
                'Дата': m['date'],
                'Настроение': m['mood'],
                'Энергия': m['energy']
            } for m in mood_data]).set_index('Дата')
            st.line_chart(mood_df, color=["#ec4899", "#3279FF"])

        # Финансовый тренд
        monthly = get_monthly_summary()
        if monthly:
            st.markdown("#### 💰 Финансы по месяцам")
            fin_df = pd.DataFrame([
                {'Месяц': k, 'Доход': v['income'], 'Расход': v['expense']}
                for k, v in sorted(monthly.items())
            ]).set_index('Месяц')
            if not fin_df.empty:
                st.bar_chart(fin_df, color=["#10b981", "#f43f5e"])

        # Taблица задач
        st.markdown("#### 📋 Таблица всех задач")
        cols_show = [c for c in ['title', 'category', 'status', 'priority', 'energy_level', 'estimated_minutes', 'pomodoro_sessions', 'due_date'] if c in df.columns]
        st.dataframe(df[cols_show], use_container_width=True)

        # Инсайты
        done_pct = len(df[df['status'] == 'Выполнено']) / len(df) * 100 if len(df) > 0 else 0
        high_pri_done = len(df[(df['priority'].str.contains('Высокий', na=False)) & (df['status'] == 'Выполнено')])
        st.markdown(f"""
        <div class="insight-box" style="margin-top:16px;">
            <div style="font-size:0.9rem; font-weight:700; color:#a5b4fc; margin-bottom:8px;">🔍 Автоматические инсайты</div>
            <ul style="color:#cbd5e1; font-size:0.88rem; margin:0; padding-left:16px;">
                <li>Процент выполнения задач: <strong style="color:#3279FF;">{done_pct:.0f}%</strong></li>
                <li>Выполнено приоритетных задач: <strong style="color:#f43f5e;">{high_pri_done}</strong></li>
                <li>Средняя оценка Pomodoro на задачу: <strong style="color:#f59e0b;">{df.get('pomodoro_sessions', pd.Series([0])).mean():.1f}</strong></li>
                {'<li style="color:#10b981;">✅ Высокая продуктивность! Продолжайте в том же духе.</li>' if done_pct > 70 else '<li style="color:#f59e0b;">⚡ Есть куда расти. Попробуйте разбить задачи на меньшие части.</li>' if done_pct > 40 else '<li style="color:#f43f5e;">🚀 Начните с одной задачи прямо сейчас!</li>'}
            </ul>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("📊 Добавьте задачи для получения аналитики.")

# ====================================================
# РАЗДЕЛ 11: ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ (УЛУЧШЕН)
# ====================================================

elif section == "📈 Отчёт недели":
    st.markdown('<div class="section-title">📈 Еженедельный отчёт</div>', unsafe_allow_html=True)

    report = generate_weekly_report()
    focus_scores = get_focus_score_history(7)
    avg_focus = sum(s['score'] for s in focus_scores) / len(focus_scores) if focus_scores else 0

    if report:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("📋 Задач", report['total_tasks'])
        with col2: st.metric("✅ Завершено", report['completed_tasks'])
        with col3: st.metric("⚡ Эффективность", f"{int(report['completion_rate'])}%")
        with col4: st.metric("🔥 Счёт фокуса", f"{avg_focus:.0f}/100")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("💰 Доходы", f"{report['weekly_income']:,.0f} ₸")
        with col2: st.metric("💸 Расходы", f"{report['weekly_expense']:,.0f} ₸")
        with col3:
            net = report['net_balance']
            st.metric("📊 Баланс", f"{net:,.0f} ₸", delta="Прибыль" if net > 0 else "Убыток")

        # Интеллектуальные рекомендации
        st.markdown("---")
        st.markdown("### 🤖 Умные рекомендации")

        recs = []
        if report['completion_rate'] < 50:
            recs.append(("⚠️", "Эффективность ниже 50%", "Попробуйте технику «2 минуты» — если задача займёт меньше 2 минут, сделайте её сразу.", "#f59e0b"))
        elif report['completion_rate'] > 80:
            recs.append(("🏆", "Отличная эффективность!", "Вы выполнили более 80% задач. Возможно, стоит увеличить амбициозность целей.", "#10b981"))

        mood_hist = get_mood_history(7)
        if mood_hist:
            avg_mood = sum(m['mood'] for m in mood_hist) / len(mood_hist)
            if avg_mood < 5:
                recs.append(("😟", "Настроение ниже среднего", "Обратите внимание на базовые потребности: сон, физическая активность, социальные связи.", "#ec4899"))
            if avg_mood >= 8:
                recs.append(("🌟", "Прекрасное настроение!", "Используйте этот энергетический пик для сложных задач и важных решений.", "#a5b4fc"))

        habits = get_all_habits()
        if habits:
            total_streaks = sum(get_habit_streak(h['id']) for h in habits)
            if total_streaks < len(habits):
                recs.append(("🌱", "Укрепите привычки", "Некоторые привычки не имеют стрика. Начните с самой простой и наращивайте.", "#22c55e"))

        for icon, title, text, color in recs:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-left:3px solid {color};
                border-radius:0 12px 12px 0; padding:12px 16px; margin-bottom:10px;">
                <div style="font-weight:700; color:{color};">{icon} {title}</div>
                <div style="color:#94a3b8; font-size:0.88rem; margin-top:4px;">{text}</div>
            </div>""", unsafe_allow_html=True)

        if not recs:
            st.success("🌟 Всё идёт хорошо! Продолжайте в том же духе.")

        st.markdown("---")
        st.markdown("### 💾 Экспорт данных")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            csv_data = export_tasks_to_csv()
            if csv_data:
                st.download_button("📥 Задачи (CSV)", csv_data,
                    f"tasks_{datetime.now().strftime('%Y-%m-%d')}.csv", "text/csv")
        with col_e2:
            json_data = export_all_data_json()
            if json_data:
                st.download_button("📥 Все данные (JSON)", json_data,
                    f"focus_space_backup_{datetime.now().strftime('%Y-%m-%d')}.json", "application/json")