import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

THEATERS = [
    {
        "name": "Большой театр",
        "address": "Театральная пл., 1",
        "lat": 55.760241,
        "lon": 37.618644,
        "performances": ["Лебединое озеро", "Щелкунчик", "Спящая красавица", "Борис Годунов", "Евгений Онегин"]
    },
    {
        "name": "МХТ им. Чехова",
        "address": "Камергерский пер., 3",
        "lat": 55.760692,
        "lon": 37.613640,
        "performances": ["Вишневый сад", "Три сестры", "Чайка", "Дядя Ваня", "Иванов"]
    },
    {
        "name": "Театр Ленком",
        "address": "Малая Дмитровка ул., 6",
        "lat": 55.766333,
        "lon": 37.610321,
        "performances": ["Юнона и Авось", "Поминальная молитва", "Шут Балакирев", "Безумный день, или Женитьба Фигаро"]
    },
    {
        "name": "Современник",
        "address": "Чистопрудный бульвар, 19",
        "lat": 55.764977,
        "lon": 37.640536,
        "performances": ["Гроза", "Три товарища", "Крутой маршрут", "Антоний & Клеопатра"]
    },
    {
        "name": "Театр Сатиры",
        "address": "Триумфальная пл., 2",
        "lat": 55.769669,
        "lon": 37.595932,
        "performances": ["Ревизор", "Горе от ума", "Свадьба Кречинского", "Двенадцатая ночь"]
    }
]


def init_db():
    conn = None
    try:
        conn = sqlite3.connect("theater_tickets.db")
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS theaters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            address TEXT NOT NULL,
            latitude REAL,
            longitude REAL
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theater_id INTEGER,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            price INTEGER NOT NULL,
            tickets_available INTEGER DEFAULT 250,
            FOREIGN KEY(theater_id) REFERENCES theaters(id)
        )""")

        cursor.execute("SELECT COUNT(*) FROM theaters")
        if cursor.fetchone()[0] == 0:
            today = datetime.now().date()
            for theater in THEATERS:
                if "performances" not in theater:
                    logger.warning(f"У театра {theater['name']} нет списка спектаклей!")
                    continue

                cursor.execute(
                    "INSERT INTO theaters (name, address, latitude, longitude) VALUES (?, ?, ?, ?)",
                    (theater["name"], theater["address"], theater["lat"], theater["lon"])
                )
                theater_id = cursor.lastrowid

                for day in range(7):
                    performance_date = today + timedelta(days=day)  # Определяем переменную перед использованием
                    performance_name = theater["performances"][day % len(theater["performances"])]
                    cursor.execute(
                        """INSERT INTO performances 
                        (theater_id, name, date, time, price, tickets_available) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (theater_id, performance_name, performance_date.strftime("%Y-%m-%d"),
                         "19:00", 2000 + (day % 3) * 500, 250)
                    )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Ошибка БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_theaters():
    conn = sqlite3.connect("theater_tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM theaters ORDER BY name")
    theaters = cursor.fetchall()
    conn.close()

    logger.info(f"Получено театров из БД: {theaters}")

    return theaters


def get_performances(theater_id):
    conn = sqlite3.connect("theater_tickets.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.id, p.name, p.date, p.time, p.price, p.tickets_available, t.name
    FROM performances p
    JOIN theaters t ON p.theater_id = t.id
    WHERE p.theater_id = ? AND p.tickets_available > 0
    ORDER BY p.date, p.time
    """, (theater_id,))
    performances = cursor.fetchall()
    conn.close()
    return performances


def buy_ticket(performance_id):
    conn = sqlite3.connect("theater_tickets.db")
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE performances 
    SET tickets_available = tickets_available - 1 
    WHERE id = ? AND tickets_available > 0
    """, (performance_id,))
    conn.commit()
    updated = cursor.rowcount
    conn.close()
    return updated > 0
