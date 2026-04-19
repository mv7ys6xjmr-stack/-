import uuid
import json
from typing import List, Dict, Set
from datetime import datetime

class GroupChat:
    """Управление групповыми чатами"""
    
    def __init__(self, database, crypto):
        self.db = database
        self.crypto = crypto
        self.active_groups: Dict[str, Set[str]] = {}  # group_id -> members
        self.group_keys: Dict[str, bytes] = {}  # group_id -> symmetric key
    
    def create_group(self, group_name: str, creator: str, members: List[str]) -> str:
        """Создает новую группу"""
        group_id = str(uuid.uuid4())[:8]
        
        # Уникальные члены группы
        all_members = list(set(members + [creator]))
        
        # Генерируем групповой ключ
        group_key = self.crypto.cipher._encryption_key  # Используем Fernet ключ
        self.group_keys[group_id] = group_key
        
        # Сохраняем в БД
        self.db.create_group(group_id, group_name, all_members, creator)
        self.active_groups[group_id] = set(all_members)
        
        return group_id
    
    def join_group(self, group_id: str, username: str) -> bool:
        """Присоединяется к группе"""
        # Проверяем существование группы
        self.db.cursor.execute('SELECT members FROM groups WHERE group_id = ?', (group_id,))
        result = self.db.cursor.fetchone()
        
        if result:
            members = json.loads(result[0])
            if username not in members:
                members.append(username)
                self.db.cursor.execute('''
                    UPDATE groups SET members = ? WHERE group_id = ?
                ''', (json.dumps(members), group_id))
                self.db.conn.commit()
            
            self.active_groups[group_id] = set(members)
            return True
        
        return False
    
    def send_group_message(self, group_id: str, sender: str, message: str) -> bool:
        """Отправляет сообщение в группу"""
        if group_id not in self.active_groups:
            return False
        
        # Шифруем сообщение групповым ключом
        if group_id in self.group_keys:
            from cryptography.fernet import Fernet
            cipher = Fernet(self.group_keys[group_id])
            encrypted_msg = cipher.encrypt(message.encode()).decode()
        else:
            encrypted_msg = message
        
        # Сохраняем в БД
        self.db.save_group_message(group_id, sender, encrypted_msg)
        return True
    
    def get_group_messages(self, group_id: str) -> List[Dict]:
        """Получает сообщения группы и расшифровывает их"""
        messages = self.db.get_group_messages(group_id)
        
        # Расшифровываем сообщения
        if group_id in self.group_keys:
            from cryptography.fernet import Fernet
            cipher = Fernet(self.group_keys[group_id])
            for msg in messages:
                try:
                    msg['message'] = cipher.decrypt(msg['message'].encode()).decode()
                except:
                    pass  # Оставляем как есть
        
        return messages
    
    def get_user_groups(self, username: str) -> List[Dict]:
        """Возвращает все группы пользователя"""
        self.db.cursor.execute('''
            SELECT group_id, group_name, members, admin, created_at
            FROM groups
            WHERE members LIKE ?
        ''', (f'%{username}%',))
        
        groups = []
        for row in self.db.cursor.fetchall():
            groups.append({
                'group_id': row[0],
                'group_name': row[1],
                'members': json.loads(row[2]),
                'admin': row[3],
                'created_at': row[4]
            })
        return groups
    
    def leave_group(self, group_id: str, username: str) -> bool:
        """Покидает группу"""
        if group_id in self.active_groups:
            self.active_groups[group_id].discard(username)
            
            # Обновляем в БД
            self.db.cursor.execute('SELECT members FROM groups WHERE group_id = ?', (group_id,))
            result = self.db.cursor.fetchone()
            if result:
                members = json.loads(result[0])
                if username in members:
                    members.remove(username)
                    self.db.cursor.execute('''
                        UPDATE groups SET members = ? WHERE group_id = ?
                    ''', (json.dumps(members), group_id))
                    self.db.conn.commit()
            
            return True
        return False