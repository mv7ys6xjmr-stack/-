import sqlite3
from datetime import datetime
from typing import List, Dict
import json

class MessageDatabase:
    def __init__(self, db_path: str = "messages.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Создает все необходимые таблицы"""
        # Таблица личных сообщений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                signature TEXT
            )
        ''')
        
        # Таблица групповых сообщений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Таблица групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                members TEXT NOT NULL,  -- JSON список
                created_at TEXT NOT NULL,
                admin TEXT NOT NULL
            )
        ''')
        
        # Таблица файлов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                size INTEGER NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT,
                group_id TEXT,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        self.conn.commit()
    
    def save_private_message(self, sender: str, recipient: str, message: str, signature: str = ""):
        """Сохраняет личное сообщение"""
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO private_messages (sender, recipient, message, timestamp, signature)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender, recipient, message, timestamp, signature))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_conversation(self, user1: str, user2: str, limit: int = 100) -> List[Dict]:
        """Получает историю переписки между двумя пользователями"""
        self.cursor.execute('''
            SELECT sender, recipient, message, timestamp, is_read
            FROM private_messages
            WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user1, user2, user2, user1, limit))
        
        messages = []
        for row in self.cursor.fetchall():
            messages.append({
                'sender': row[0],
                'recipient': row[1],
                'message': row[2],
                'timestamp': row[3],
                'is_read': bool(row[4])
            })
        return messages[::-1]  # В хронологическом порядке
    
    def create_group(self, group_id: str, group_name: str, members: List[str], admin: str):
        """Создает новую группу"""
        members_json = json.dumps(members)
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO groups (group_id, group_name, members, created_at, admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (group_id, group_name, members_json, timestamp, admin))
        self.conn.commit()
    
    def save_group_message(self, group_id: str, sender: str, message: str):
        """Сохраняет сообщение в группе"""
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO group_messages (group_id, sender, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (group_id, sender, message, timestamp))
        self.conn.commit()
    
    def get_group_messages(self, group_id: str, limit: int = 200) -> List[Dict]:
        """Получает историю сообщений группы"""
        self.cursor.execute('''
            SELECT sender, message, timestamp
            FROM group_messages
            WHERE group_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (group_id, limit))
        
        messages = []
        for row in self.cursor.fetchall():
            messages.append({
                'sender': row[0],
                'message': row[1],
                'timestamp': row[2]
            })
        return messages[::-1]
    
    def search_messages(self, keyword: str, username: str) -> List[Dict]:
        """Поиск сообщений по ключевому слову"""
        self.cursor.execute('''
            SELECT sender, recipient, message, timestamp
            FROM private_messages
            WHERE (sender = ? OR recipient = ?) AND message LIKE ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (username, username, f'%{keyword}%'))
        
        return [{'sender': r[0], 'recipient': r[1], 'message': r[2], 'timestamp': r[3]} 
                for r in self.cursor.fetchall()]
    
    def close(self):
        self.conn.close()