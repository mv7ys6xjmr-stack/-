import socket
import threading
import json
import time
import requests
import os
from typing import Set, Dict, Callable, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from crypto_utils import MessageCrypto

def get_local_ip():
    """Определяет локальный IP адрес компьютера"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

@dataclass
class Message:
    sender: str
    content: str
    timestamp: str
    is_encrypted: bool = True
    is_file: bool = False
    filename: str = None
    file_size: int = 0

class P2PNode:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, username: str = None):
        self.host = host
        self.port = port
        self.username = username or f"User_{port}"
        
        self.local_ip = get_local_ip()
        self.public_ip = None
        self.relay_registered = False
        self.relay_server_addr = None  # (host, port)
        
        self.peers: Set[Tuple[str, int]] = set()
        self.peer_info: Dict[str, Dict] = {}  # username -> {ip, port, last_seen}
        self.messages: List[Message] = []
        self.running = True
        self.crypto = MessageCrypto()
        self.message_callback: Callable = None
        self.file_callback: Callable = None
        
        self.relay_host = None
        self.relay_port = 5000
        
        self.downloads_dir = "downloads"
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def start(self):
        """Запускает узел"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            print(f"✅ Узел запущен")
            print(f"   📍 Локальный IP: {self.local_ip}:{self.port}")
            
            # Получаем публичный IP
            self.public_ip = self.get_public_ip()
            if self.public_ip and self.public_ip != self.local_ip:
                print(f"   🌐 Внешний IP: {self.public_ip}:{self.port}")
            
            # Запускаем потоки
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            # Запускаем UDP hole punching сервер (для NAT traversal)
            self._start_hole_punching()
            
            # Поиск пиров в локальной сети (опционально)
            self._discover_local_peers()
            
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
    
    def get_public_ip(self) -> str:
        """Узнаёт свой внешний IP через несколько API"""
        apis = [
            'https://api.ipify.org',
            'https://icanhazip.com',
            'https://checkip.amazonaws.com'
        ]
        for api in apis:
            try:
                response = requests.get(api, timeout=5)
                ip = response.text.strip()
                if ip and '.' in ip:
                    return ip
            except:
                continue
        return self.local_ip
    
    def _start_hole_punching(self):
        """Запускает UDP сервер для hole punching (обходит NAT)"""
        def udp_server():
            try:
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                udp_socket.bind((self.host, self.port))
                udp_socket.settimeout(1)
                
                while self.running:
                    try:
                        data, addr = udp_socket.recvfrom(1024)
                        # Ответ для hole punching
                        udp_socket.sendto(b"PONG", addr)
                    except socket.timeout:
                        continue
                    except:
                        break
                udp_socket.close()
            except:
                pass
        
        threading.Thread(target=udp_server, daemon=True).start()
    
    def register_with_relay(self, relay_host: str, relay_port: int = 5000) -> bool:
        """Регистрируется на релей-сервере для интернет-соединений"""
        self.relay_host = relay_host
        self.relay_port = relay_port
        
        # Пробуем разные способы подключения
        for attempt in range(3):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((relay_host, relay_port))
                
                if not self.public_ip:
                    self.public_ip = self.get_public_ip()
                
                request = {
                    'type': 'register',
                    'username': self.username,
                    'ip': self.public_ip,
                    'local_ip': self.local_ip,
                    'port': self.port,
                    'timestamp': time.time()
                }
                sock.send(json.dumps(request).encode())
                
                response = sock.recv(4096).decode()
                result = json.loads(response)
                sock.close()
                
                if result.get('status') == 'ok':
                    self.relay_registered = True
                    self.relay_server_addr = (relay_host, relay_port)
                    print(f"✅ Зарегистрирован на релей-сервере {relay_host}:{relay_port}")
                    print(f"   Ваш публичный IP: {self.public_ip}:{self.port}")
                    
                    # Получаем список других пиров
                    if 'peers' in result:
                        for peer in result['peers']:
                            if peer['username'] != self.username:
                                self.peer_info[peer['username']] = peer
                    return True
                    
            except socket.timeout:
                print(f"⚠️ Попытка {attempt + 1}: таймаут подключения к релей-серверу")
                time.sleep(2)
            except ConnectionRefusedError:
                print(f"⚠️ Попытка {attempt + 1}: соединение отклонено")
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Попытка {attempt + 1}: {e}")
                time.sleep(2)
        
        print(f"❌ Не удалось зарегистрироваться на релей-сервере {relay_host}:{relay_port}")
        return False
    
    def find_peer_via_relay(self, username: str) -> Optional[Tuple[str, int, str]]:
        """Находит пира через релей-сервер"""
        if not self.relay_host:
            print("⚠️ Релей-сервер не настроен")
            return None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.relay_host, self.relay_port))
            
            request = {
                'type': 'find',
                'username': username,
                'requester': self.username
            }
            sock.send(json.dumps(request).encode())
            
            response = sock.recv(4096).decode()
            result = json.loads(response)
            sock.close()
            
            if result.get('found'):
                ip = result.get('ip')
                port = result.get('port')
                local_ip = result.get('local_ip')
                print(f"🔍 Пир {username} найден: {ip}:{port}")
                return (ip, port, local_ip)
            else:
                print(f"❌ Пир {username} не найден")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка поиска пира: {e}")
            return None
    
    def connect_to_peer(self, peer_host: str, peer_port: int, use_hole_punching: bool = True) -> bool:
        """Подключается к пиру с поддержкой NAT traversal"""
        if (peer_host, peer_port) in self.peers:
            return True
        
        # Пробуем прямое подключение
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)
            peer_socket.connect((peer_host, peer_port))
            
            # Отправляем информацию о себе
            handshake = {
                'type': 'handshake',
                'username': self.username,
                'public_ip': self.public_ip,
                'port': self.port
            }
            peer_socket.send(json.dumps(handshake).encode())
            
            self.peers.add((peer_host, peer_port))
            peer_socket.close()
            print(f"🔗 Подключен к {peer_host}:{peer_port}")
            return True
            
        except (socket.timeout, ConnectionRefusedError):
            if use_hole_punching:
                return self._connect_via_hole_punching(peer_host, peer_port)
            return False
        except Exception as e:
            print(f"❌ Не удалось подключиться: {e}")
            return False
    
    def _connect_via_hole_punching(self, peer_host: str, peer_port: int) -> bool:
        """Пытается подключиться через UDP hole punching"""
        try:
            # Создаём UDP сокет
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(3)
            udp_socket.bind(('0.0.0.0', self.port))
            
            # Отправляем punch-пакеты
            for _ in range(5):
                udp_socket.sendto(b"PUNCH", (peer_host, peer_port))
                time.sleep(0.1)
            
            # Пробуем TCP подключение снова
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(3)
            tcp_socket.connect((peer_host, peer_port))
            
            self.peers.add((peer_host, peer_port))
            tcp_socket.close()
            udp_socket.close()
            print(f"🔗 Подключен через hole punching к {peer_host}:{peer_port}")
            return True
            
        except Exception as e:
            print(f"❌ Hole punching не удался: {e}")
            return False
    
    def connect_to_peer_by_username(self, username: str) -> bool:
        """Подключается к пиру по имени"""
        peer_info = self.find_peer_via_relay(username)
        if peer_info:
            ip, port, local_ip = peer_info
            # Пробуем сначала локальный IP, затем публичный
            if local_ip and self._is_same_network(local_ip):
                if self.connect_to_peer(local_ip, port):
                    return True
            return self.connect_to_peer(ip, port)
        return False
    
    def _is_same_network(self, ip: str) -> bool:
        """Проверяет, находится ли IP в той же локальной сети"""
        if not self.local_ip:
            return False
        local_parts = self.local_ip.split('.')
        ip_parts = ip.split('.')
        return len(local_parts) == 4 and len(ip_parts) == 4 and local_parts[:2] == ip_parts[:2]
    
    def _accept_connections(self):
        """Принимает входящие соединения"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_peer,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            except:
                break
    
    def _handle_peer(self, client_socket: socket.socket, address: tuple):
        """Обрабатывает сообщения от пира"""
        try:
            while self.running:
                # Сначала читаем заголовок (первые 4 байта - длина сообщения)
                header = client_socket.recv(4)
                if not header:
                    break
                
                msg_length = int.from_bytes(header, 'big')
                data = b''
                while len(data) < msg_length:
                    chunk = client_socket.recv(min(4096, msg_length - len(data)))
                    if not chunk:
                        break
                    data += chunk
                
                if not data:
                    break
                
                message_data = json.loads(data.decode())
                
                # Обработка разных типов сообщений
                msg_type = message_data.get('type', 'message')
                
                if msg_type == 'handshake':
                    # Добавляем пира в список
                    username = message_data.get('username')
                    if username:
                        self.peer_info[username] = {
                            'ip': address[0],
                            'port': address[1],
                            'last_seen': time.time()
                        }
                    self.peers.add((address[0], address[1]))
                    
                elif msg_type == 'file':
                    # Обработка файла
                    self._receive_file_data(client_socket, message_data)
                    
                elif msg_type == 'message' or msg_type == 'group_message':
                    # Расшифровываем если нужно
                    content = message_data['content']
                    if message_data.get('encrypted', False):
                        try:
                            content = self.crypto.decrypt(content.encode()).decode()
                        except:
                            pass
                    
                    msg = Message(
                        sender=message_data['sender'],
                        content=content,
                        timestamp=message_data['timestamp'],
                        is_encrypted=message_data.get('encrypted', False),
                        is_file=message_data.get('is_file', False),
                        filename=message_data.get('filename'),
                        file_size=message_data.get('file_size', 0)
                    )
                    
                    self.messages.append(msg)
                    if self.message_callback:
                        self.message_callback(msg)
                    
                    print(f"\n📨 [{msg.timestamp}] {msg.sender}: {msg.content}")
                
        except Exception as e:
            print(f"Ошибка соединения с {address}: {e}")
        finally:
            client_socket.close()
    
    def send_message(self, content: str, peer_host: str = None, peer_port: int = None, 
                     is_group: bool = False, group_id: str = None):
        """Отправляет сообщение"""
        msg = Message(
            sender=self.username,
            content=content,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        
        # Шифруем
        try:
            encrypted_content = self.crypto.encrypt(msg.content)
            encrypted = True
        except:
            encrypted_content = msg.content.encode()
            encrypted = False
        
        message_data = {
            'type': 'group_message' if is_group else 'message',
            'sender': msg.sender,
            'content': encrypted_content.decode() if encrypted else msg.content,
            'timestamp': msg.timestamp,
            'encrypted': encrypted
        }
        
        if is_group and group_id:
            message_data['group_id'] = group_id
        
        if peer_host and peer_port:
            self._send_to_peer(message_data, peer_host, peer_port)
        else:
            for peer_host, peer_port in list(self.peers):
                self._send_to_peer(message_data, peer_host, peer_port)
        
        self.messages.append(msg)
        if self.message_callback:
            self.message_callback(msg)
    
    def _send_to_peer(self, message_data: dict, peer_host: str, peer_port: int):
        """Отправляет данные пиру"""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)
            peer_socket.connect((peer_host, peer_port))
            
            json_data = json.dumps(message_data).encode()
            # Отправляем длину сообщения + данные
            peer_socket.send(len(json_data).to_bytes(4, 'big'))
            peer_socket.send(json_data)
            peer_socket.close()
            
        except Exception as e:
            if (peer_host, peer_port) in self.peers:
                self.peers.discard((peer_host, peer_port))
                print(f"⚠️ Пир {peer_host}:{peer_port} недоступен")
    
    def send_file(self, filepath: str, peer_host: str = None, peer_port: int = None, 
                  recipient_username: str = None) -> Tuple[bool, str]:
        """Отправляет файл пиру"""
        if not os.path.exists(filepath):
            return False, "Файл не найден"
        
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        # Ограничение размера файла (50MB)
        if file_size > 50 * 1024 * 1024:
            return False, "Файл слишком большой (макс. 50MB)"
        
        # Если указано имя пользователя, находим его адрес
        if recipient_username and not peer_host:
            peer_info = self.find_peer_via_relay(recipient_username)
            if peer_info:
                peer_host, peer_port, _ = peer_info
            else:
                return False, f"Пир {recipient_username} не найден"
        
        if not peer_host or not peer_port:
            return False, "Не указан получатель"
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((peer_host, peer_port))
            
            # Отправляем метаданные файла
            file_info = {
                'type': 'file',
                'filename': filename,
                'file_size': file_size,
                'sender': self.username,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            json_info = json.dumps(file_info).encode()
            sock.send(len(json_info).to_bytes(4, 'big'))
            sock.send(json_info)
            
            # Ждём подтверждение
            ack = sock.recv(4)
            if ack != b'OKAY':
                sock.close()
                return False, "Получатель не готов"
            
            # Отправляем файл
            with open(filepath, 'rb') as f:
                sent = 0
                while sent < file_size:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sock.send(chunk)
                    sent += len(chunk)
            
            sock.close()
            
            # Добавляем в историю
            self.messages.append(Message(
                sender=self.username,
                content=f"[Файл] {filename}",
                timestamp=datetime.now().strftime("%H:%M:%S"),
                is_file=True,
                filename=filename,
                file_size=file_size
            ))
            
            return True, f"Файл {filename} отправлен ({file_size/1024:.1f} KB)"
            
        except socket.timeout:
            return False, "Таймаут при отправке"
        except Exception as e:
            return False, f"Ошибка: {e}"
    
    def _receive_file_data(self, client_socket: socket.socket, file_info: dict):
        """Принимает файл от пира"""
        try:
            filename = file_info['filename']
            file_size = file_info['file_size']
            sender = file_info['sender']
            
            # Отправляем подтверждение
            client_socket.send(b'OKAY')
            
            # Сохраняем файл
            save_path = os.path.join(self.downloads_dir, filename)
            
            # Если файл с таким именем существует, добавляем номер
            counter = 1
            while os.path.exists(save_path):
                name, ext = os.path.splitext(filename)
                save_path = os.path.join(self.downloads_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            received = 0
            with open(save_path, 'wb') as f:
                while received < file_size:
                    chunk = client_socket.recv(min(8192, file_size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            
            print(f"📥 Файл получен: {filename} сохранён в {save_path}")
            
            # Уведомляем GUI
            if self.message_callback:
                msg = Message(
                    sender=sender,
                    content=f"📁 Получен файл: {filename}",
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    is_file=True,
                    filename=filename,
                    file_size=file_size
                )
                self.message_callback(msg)
            
        except Exception as e:
            print(f"Ошибка приёма файла: {e}")
    
    def _discover_local_peers(self):
        """Обнаружение пиров в локальной сети"""
        def discover():
            if self.local_ip and self.local_ip != '127.0.0.1':
                network_parts = self.local_ip.split('.')
                network_prefix = '.'.join(network_parts[:-1]) + '.'
            else:
                network_prefix = '192.168.1.'
            
            print(f"🔍 Сканирую локальную сеть {network_prefix}*...")
            
            for i in range(1, 255):
                ip = f"{network_prefix}{i}"
                if ip != self.local_ip:
                    for port in range(self.port, min(self.port + 3, 65535)):
                        try:
                            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            test_socket.settimeout(0.3)
                            if test_socket.connect_ex((ip, port)) == 0:
                                self.connect_to_peer(ip, port, use_hole_punching=False)
                            test_socket.close()
                        except:
                            pass
            
            print(f"✅ Поиск завершён. Найдено пиров: {len(self.peers)}")
        
        threading.Thread(target=discover, daemon=True).start()
    
    def search_history(self, keyword: str) -> List[Dict]:
        """Поиск по истории"""
        results = []
        for msg in self.messages:
            if keyword.lower() in msg.content.lower():
                results.append({
                    'timestamp': msg.timestamp,
                    'sender': msg.sender,
                    'message': msg.content,
                    'is_file': msg.is_file,
                    'filename': msg.filename
                })
        return results
    
    def show_routing_table(self) -> str:
        info = "╔══════════════════════════════════════════════════════════╗\n"
        info += "║                    ИНФОРМАЦИЯ О УЗЛЕ                     ║\n"
        info += "╚══════════════════════════════════════════════════════════╝\n\n"
        info += f"Имя: {self.username}\n"
        info += f"Порт: {self.port}\n"
        info += f"Локальный IP: {self.local_ip}\n"
        if self.public_ip and self.public_ip != self.local_ip:
            info += f"🌐 Внешний IP: {self.public_ip}\n"
        if self.relay_registered:
            info += f"📡 Релей-сервер: {self.relay_host}:{self.relay_port}\n"
        info += f"\n👥 Пиры: {len(self.peers)}\n"
        
        if self.peers:
            info += "\n" + "─" * 50 + "\n"
            info += "  IP адрес                 Порт     Статус\n"
            info += "─" * 50 + "\n"
            for host, port in self.peers:
                info += f"  {host:<23} {port:<8}  ✅ онлайн\n"
        
        info += f"\n💬 Сообщений: {len(self.messages)}\n"
        return info
    
    def get_peers_list(self) -> List[Tuple[str, int]]:
        return list(self.peers)
    
    def get_online_peers(self) -> List[Dict]:
        """Возвращает список онлайн пиров с их именами"""
        peers_list = []
        for username, info in self.peer_info.items():
            if time.time() - info.get('last_seen', 0) < 60:
                peers_list.append({
                    'username': username,
                    'ip': info['ip'],
                    'port': info['port']
                })
        return peers_list
    
    def remove_peer(self, host: str, port: int):
        self.peers.discard((host, port))
    
    def stop(self):
        self.running = False
        self.server_socket.close()
        
        # Отписываемся от релей-сервера
        if self.relay_registered and self.relay_host:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.relay_host, self.relay_port))
                request = {'type': 'unregister', 'username': self.username}
                sock.send(json.dumps(request).encode())
                sock.close()
            except:
                pass
        
        print("👋 Узел остановлен")
    
    def get_status(self) -> Dict:
        return {
            'username': self.username,
            'local_ip': self.local_ip,
            'public_ip': self.public_ip,
            'port': self.port,
            'peers_count': len(self.peers),
            'messages_count': len(self.messages),
            'relay_registered': self.relay_registered,
            'is_running': self.running
        }


class RelayServer:
    """Релейный сервер для соединения пиров через интернет"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.host = host
        self.port = port
        self.peers: Dict[str, Dict] = {}  # username -> info
        self.running = True
    
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(100)
        
        print(f"🚀 Релей-сервер запущен на {self.host}:{self.port}")
        print(f"   Ожидание регистрации пиров...")
        
        # Периодическая очистка устаревших пиров
        def cleanup():
            while self.running:
                time.sleep(60)
                now = time.time()
                to_remove = [name for name, info in self.peers.items() 
                           if now - info.get('last_seen', 0) > 300]
                for name in to_remove:
                    del self.peers[name]
                    print(f"🗑️ Удалён устаревший пир: {name}")
        
        threading.Thread(target=cleanup, daemon=True).start()
        
        while self.running:
            try:
                client, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()
            except:
                break
        
        server.close()
    
    def _handle_client(self, client: socket.socket, addr: tuple):
        try:
            # Читаем длину сообщения
            header = client.recv(4)
            if not header:
                client.close()
                return
            
            msg_length = int.from_bytes(header, 'big')
            data = b''
            while len(data) < msg_length:
                chunk = client.recv(min(4096, msg_length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                client.close()
                return
            
            request = json.loads(data.decode())
            response = None
            
            if request['type'] == 'register':
                username = request['username']
                self.peers[username] = {
                    'ip': request.get('ip', addr[0]),
                    'local_ip': request.get('local_ip', addr[0]),
                    'port': request['port'],
                    'last_seen': time.time()
                }
                
                # Возвращаем список других пиров
                other_peers = []
                for name, info in self.peers.items():
                    if name != username:
                        other_peers.append({
                            'username': name,
                            'ip': info['ip'],
                            'local_ip': info.get('local_ip', info['ip']),
                            'port': info['port']
                        })
                
                response = {'status': 'ok', 'peers': other_peers}
                print(f"✅ Зарегистрирован: {username} ({self.peers[username]['ip']}:{self.peers[username]['port']})")
                
            elif request['type'] == 'find':
                username = request['username']
                peer = self.peers.get(username)
                
                if peer and (time.time() - peer['last_seen']) < 300:
                    response = {
                        'found': True,
                        'ip': peer['ip'],
                        'local_ip': peer.get('local_ip', peer['ip']),
                        'port': peer['port']
                    }
                    print(f"🔍 Найден: {username}")
                else:
                    response = {'found': False}
                    print(f"❌ Не найден: {username}")
            
            elif request['type'] == 'unregister':
                username = request['username']
                if username in self.peers:
                    del self.peers[username]
                    print(f"👋 Отключился: {username}")
                response = {'status': 'ok'}
            
            elif request['type'] == 'heartbeat':
                username = request['username']
                if username in self.peers:
                    self.peers[username]['last_seen'] = time.time()
                response = {'status': 'ok'}
            
            if response:
                json_response = json.dumps(response).encode()
                client.send(len(json_response).to_bytes(4, 'big'))
                client.send(json_response)
            
            client.close()
            
        except Exception as e:
            print(f"Ошибка обработки: {e}")
            client.close()
    
    def stop(self):
        self.running = False
        print("Релей-сервер остановлен")
    
    def get_stats(self) -> Dict:
        return {
            'active_peers': len(self.peers),
            'peers_list': list(self.peers.keys())
        }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--relay':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        server = RelayServer(port=port)
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
            print("\n👋 Релей-сервер остановлен")
    else:
        print("Запуск тестового узла...")
        node = P2PNode()
        node.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            node.stop()
