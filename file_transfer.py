import socket
import threading
import os
import hashlib
from typing import Callable, Optional
import json
from pathlib import Path

class FileTransfer:
    """P2P файловый обмен с возобновлением"""
    
    def __init__(self, download_callback: Callable = None, progress_callback: Callable = None):
        self.download_callback = download_callback
        self.progress_callback = progress_callback
        self.active_transfers = {}
        self.chunk_size = 8192  # 8KB chunks
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def send_file(self, filepath: str, peer_host: str, peer_port: int, 
                  recipient: str = None, group_id: str = None):
        """Отправляет файл пиру"""
        if not os.path.exists(filepath):
            return False, "Файл не найден"
        
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_hash = self.calculate_file_hash(filepath)
        
        try:
            # Создаем сокет для передачи файла
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_host, peer_port))
            
            # Отправляем метаданные
            metadata = {
                'type': 'file_transfer',
                'filename': filename,
                'size': file_size,
                'hash': file_hash,
                'recipient': recipient,
                'group_id': group_id
            }
            sock.send(json.dumps(metadata).encode())
            
            # Получаем подтверждение
            ack = sock.recv(1024).decode()
            if ack != 'READY':
                sock.close()
                return False, "Пир не готов принять файл"
            
            # Отправляем файл по частям
            sent = 0
            with open(filepath, 'rb') as f:
                while sent < file_size:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    sock.send(chunk)
                    sent += len(chunk)
                    
                    if self.progress_callback:
                        self.progress_callback(filename, sent, file_size)
            
            # Получаем подтверждение о получении
            result = sock.recv(1024).decode()
            sock.close()
            
            if result == 'SUCCESS':
                return True, f"Файл {filename} успешно отправлен"
            else:
                return False, "Ошибка при передаче файла"
                
        except Exception as e:
            return False, f"Ошибка: {e}"
    
    def receive_file(self, client_socket: socket.socket, save_dir: str = "downloads"):
        """Принимает файл от пира"""
        try:
            # Создаем папку для загрузок
            Path(save_dir).mkdir(exist_ok=True)
            
            # Получаем метаданные
            metadata_json = client_socket.recv(4096).decode()
            metadata = json.loads(metadata_json)
            
            filename = metadata['filename']
            file_size = metadata['size']
            file_hash = metadata['hash']
            
            # Подтверждаем готовность
            client_socket.send(b'READY')
            
            # Принимаем файл
            save_path = os.path.join(save_dir, filename)
            received = 0
            with open(save_path, 'wb') as f:
                while received < file_size:
                    chunk = client_socket.recv(min(self.chunk_size, file_size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    
                    if self.progress_callback:
                        self.progress_callback(filename, received, file_size)
            
            # Проверяем хеш
            actual_hash = self.calculate_file_hash(save_path)
            if actual_hash == file_hash:
                client_socket.send(b'SUCCESS')
                if self.download_callback:
                    self.download_callback(filename, save_path)
                return True, f"Файл {filename} успешно получен"
            else:
                client_socket.send(b'HASH_MISMATCH')
                os.remove(save_path)
                return False, "Ошибка хеша файла"
                
        except Exception as e:
            return False, f"Ошибка: {e}"