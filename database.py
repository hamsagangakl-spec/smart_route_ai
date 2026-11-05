import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routes.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: Search history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_place TEXT NOT NULL,
            destination TEXT NOT NULL,
            distance_km REAL NOT NULL,
            duration_min REAL NOT NULL,
            selected_personality TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            fuel_cost REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table 2: Favourite journeys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favourite_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_place TEXT NOT NULL,
            destination TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table 3: Safety check-in tracker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safety_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            traveler_name TEXT NOT NULL,
            emergency_contact TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            destination TEXT NOT NULL,
            expected_arrival TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table 4: Road and weather alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS road_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_zone TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL, -- Low, Medium, High
            alert_type TEXT NOT NULL, -- Roadwork, Weather, Hazard, Traffic
            is_verified INTEGER DEFAULT 0, -- 1 = Verified live, 0 = Sample demonstration
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed default alerts if empty
    cursor.execute('SELECT COUNT(*) FROM road_alerts')
    if cursor.fetchone()[0] == 0:
        sample_alerts = [
            ("Bengaluru - Mysuru Expressway", "Pavement & Drainage Maintenance", "Ongoing resurfacing near Bidadi. Right lane restricted.", "Medium", "Roadwork", 1),
            ("Western Ghats (Shiradi Ghat)", "Monsoon Fog & Landslide Caution", "Heavy mist reducing visibility below 30m. Speed limit 30 km/h.", "High", "Weather", 1),
            ("NH 48 Nelamangala Flyover", "Peak Hour Freight Congestion", "Slow moving cargo vehicles towards Tumakuru.", "Medium", "Traffic", 1),
            ("Hubballi - Dharwad Bypass", "Night Travel Poor Lighting Alert", "Single carriageway segment without streetlamps. High beam care needed.", "Medium", "Hazard", 0), # Sample simulation
            ("Coastal NH 66 Karwar", "High Tide Wave Spray Demo", "Simulated demo alert for coastal water spray during monsoon high tides.", "Low", "Weather", 0), # Sample simulation
            ("Bengaluru Outer Ring Road", "Metro Construction Lane Narrowing", "Barricades near Silk Board junction causing 15 min delay.", "High", "Roadwork", 1)
        ]
        cursor.executemany('''
            INSERT INTO road_alerts (route_zone, title, description, severity, alert_type, is_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_alerts)

    conn.commit()
    conn.close()

def add_search_history(start_place, destination, distance_km, duration_min, personality, risk_score, fuel_cost):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO search_history (start_place, destination, distance_km, duration_min, selected_personality, risk_score, fuel_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (start_place, destination, distance_km, duration_min, personality, risk_score, fuel_cost))
    conn.commit()
    conn.close()

def get_search_history(limit=25):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, start_place, destination, distance_km, duration_min, selected_personality, risk_score, fuel_cost,
               datetime(created_at, 'localtime') as created_at_local
        FROM search_history
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def clear_search_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM search_history')
    conn.commit()
    conn.close()

def add_favourite(name, start_place, destination, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO favourite_places (name, start_place, destination, notes)
        VALUES (?, ?, ?, ?)
    ''', (name, start_place, destination, notes))
    conn.commit()
    fav_id = cursor.lastrowid
    conn.close()
    return fav_id

def get_favourites():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, start_place, destination, notes, datetime(created_at, 'localtime') as created_at_local
        FROM favourite_places
        ORDER BY id DESC
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def delete_favourite(fav_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM favourite_places WHERE id = ?', (fav_id,))
    conn.commit()
    conn.close()

def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, route_zone, title, description, severity, alert_type, is_verified,
               datetime(created_at, 'localtime') as created_at_local
        FROM road_alerts
        ORDER BY id ASC
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def add_safety_checkin(traveler_name, emergency_contact, contact_phone, destination, expected_arrival):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO safety_checkins (traveler_name, emergency_contact, contact_phone, destination, expected_arrival, status)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE')
    ''', (traveler_name, emergency_contact, contact_phone, destination, expected_arrival))
    conn.commit()
    checkin_id = cursor.lastrowid
    conn.close()
    return checkin_id

def get_safety_checkins():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, traveler_name, emergency_contact, contact_phone, destination, expected_arrival, status,
               datetime(created_at, 'localtime') as created_at_local
        FROM safety_checkins
        ORDER BY id DESC
        LIMIT 10
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def update_safety_checkin_status(checkin_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE safety_checkins SET status = ? WHERE id = ?', (status, checkin_id))
    conn.commit()
    conn.close()
