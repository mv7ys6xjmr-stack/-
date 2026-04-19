import socket
import threading
import json
import time
import requests
from typing import Set, Dict, Callable, List, Tuple
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

class P2PNode:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, username: str = None):
        self.host = host  # Слушаем все интерфейсы (0.0.0.0) или конкретный IP
        self.port = port
        self.username = username or f"User_{port}"
        
        # Сетевые настройки
        self.local_ip = get_local_ip()
        self.public_ip = None
        self.relay_registered = False
        
        self.peers: Set[Tuple[str, int]] = set()  # (ip, port)
        self.messages: List[Message] = []
        self.running = True
        self.crypto = MessageCrypto()
        self.message_callback: Callable = None
        
        # Настройки релей-сервера (по умолчанию)
        self.relay_host = None
        self.relay_port = 5000
        
        # Создаем сокет для прослушивания
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def start(self):
        """Запускает узел"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"✅ Узел запущен")
            print(f"   📍 Локальный IP: {self.local_ip}:{self.port}")
            
            # Показываем публичный IP если есть
            public = self.get_public_ip()
            if public and public != self.local_ip:
                print(f"   🌐 Внешний IP: {public}:{self.port}")
                print(f"   (для подключения через интернет используйте внешний IP)")
            
            # Запускаем поток для принятия соединений
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            # Запускаем поиск пиров в локальной сети
            self._discover_local_peers()
            
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
    
    def get_public_ip(self) -> str:
        """Узнает свой внешний IP через API"""
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            self.public_ip = response.text.strip()
            return self.public_ip
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Не удалось определить внешний IP: {e}")
            return self.local_ip
        except Exception as e:
            print(f"⚠️ Ошибка получения внешнего IP: {e}")
            return self.local_ip
    
    def register_with_relay(self, relay_host: str, relay_port: int = 5000) -> bool:
        """Регистрирует свой IP на релей-сервере (для соединения через интернет)"""
        self.relay_host = relay_host
        self.relay_port = relay_port
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((relay_host, relay_port))
            
            # Получаем публичный IP
            if not self.public_ip:
                self.public_ip = self.get_public_ip()
            
            request = {
                'type': 'register',
                'username': self.username,
                'ip': self.public_ip,
                'port': self.port
            }
            sock.send(json.dumps(request).encode())
            
            # Получаем ответ
            response = sock.recv(1024).decode()
            result = json.loads(response)
            
            sock.close()
            
            if result.get('status') == 'ok':
                self.relay_registered = True
                print(f"✅ Зарегистрирован на релей-сервере {relay_host}:{relay_port}")
                print(f"   Ваш публичный IP: {self.public_ip}:{self.port}")
                return True
            else:
                print(f"❌ Ошибка регистрации: {result.get('error', 'неизвестная ошибка')}")
                return False
                
        except Exception as e:
            print(f"❌ Не удалось подключиться к релей-серверу {relay_host}:{relay_port} - {e}")
            return False
    
    def find_peer_via_relay(self, username: str) -> Tuple[str, int]:
        """Находит пира через релей-сервер по его имени"""
        if not self.relay_host:
            print("⚠️ Релей-сервер не настроен. Сначала зарегистрируйтесь.")
            return None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.relay_host, self.relay_port))
            
            request = {
                'type': 'find',
                'username': username
            }
            sock.send(json.dumps(request).encode())
            
            response = sock.recv(1024).decode()
            result = json.loads(response)
            sock.close()
            
            if result.get('found'):
                ip = result.get('ip')
                port = result.get('port')
                print(f"🔍 Пир {username} найден: {ip}:{port}")
                return (ip, port)
            else:
                print(f"❌ Пир {username} не найден на релей-сервере")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка поиска пира: {e}")
            return None
    
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
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Получаем сообщение
                message_data = json.loads(data.decode())
                
                # Расшифровываем если нужно
                if message_data.get('encrypted', False):
                    try:
                        decrypted_content = self.crypto.decrypt(message_data['content'].encode())
                        message_data['content'] = decrypted_content
                    except:
                        pass
                
                msg = Message(
                    sender=message_data['sender'],
                    content=message_data['content'],
                    timestamp=message_data['timestamp'],
                    is_encrypted=message_data.get('encrypted', False)
                )
                
                self.messages.append(msg)
                
                # Вызываем callback если есть
                if self.message_callback:
                    self.message_callback(msg)
                
                print(f"\n📨 [{msg.timestamp}] {msg.sender}: {msg.content}")
                
        except Exception as e:
            print(f"Ошибка соединения с {address}: {e}")
        finally:
            client_socket.close()
    
    def connect_to_peer(self, peer_host: str, peer_port: int) -> bool:
        """Подключается к другому узлу (можно любой IP)"""
        # Проверяем, не подключены ли уже
        if (peer_host, peer_port) in self.peers:
            print(f"🔗 Уже подключен к {peer_host}:{peer_port}")
            return True
        
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)  # Таймаут 5 секунд
            peer_socket.connect((peer_host, peer_port))
            
            self.peers.add((peer_host, peer_port))
            print(f"🔗 Подключен к {peer_host}:{peer_port}")
            
            # Отправляем приветственное сообщение
            welcome = {
                'sender': self.username,
                'content': f"{self.username} присоединился к сети",
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'encrypted': False
            }
            peer_socket.send(json.dumps(welcome).encode())
            peer_socket.close()
            return True
            
        except socket.timeout:
            print(f"❌ Таймаут подключения к {peer_host}:{peer_port}")
            return False
        except ConnectionRefusedError:
            print(f"❌ Соединение отклонено {peer_host}:{peer_port} (возможно, пир не запущен)")
            return False
        except Exception as e:
            print(f"❌ Не удалось подключиться к {peer_host}:{peer_port} - {e}")
            return False
    
    def connect_to_peer_by_username(self, username: str) -> bool:
        """Подключается к пиру по имени через релей-сервер"""
        peer_info = self.find_peer_via_relay(username)
        if peer_info:
            ip, port = peer_info
            return self.connect_to_peer(ip, port)
        return False
    
    def send_message(self, content: str, peer_host: str = None, peer_port: int = None):
        """Отправляет сообщение конкретному пиру или всем"""
        msg = Message(
            sender=self.username,
            content=content,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        
        # Шифруем сообщение
        try:
            encrypted_content = self.crypto.encrypt(msg.content)
            encrypted = True
        except:
            encrypted_content = msg.content.encode()
            encrypted = False
        
        message_data = {
            'sender': msg.sender,
            'content': encrypted_content.decode() if encrypted else msg.content,
            'timestamp': msg.timestamp,
            'encrypted': encrypted
        }
        
        # Отправляем конкретному пиру
        if peer_host and peer_port:
            self._send_to_peer(message_data, peer_host, peer_port)
        else:
            # Отправляем всем пирам
            for peer_host, peer_port in list(self.peers):
                self._send_to_peer(message_data, peer_host, peer_port)
        
        # Сохраняем сообщение локально
        self.messages.append(msg)
        if self.message_callback:
            self.message_callback(msg)
    
    def _send_to_peer(self, message_data: dict, peer_host: str, peer_port: int):
        """Отправляет данные конкретному пиру"""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(3)
            peer_socket.connect((peer_host, peer_port))
            peer_socket.send(json.dumps(message_data).encode())
            peer_socket.close()
        except Exception as e:
            # Если пир не отвечает, удаляем его из списка
            if (peer_host, peer_port) in self.peers:
                self.peers.discard((peer_host, peer_port))
                print(f"⚠️ Пир {peer_host}:{peer_port} недоступен, удалён из списка")
    
    def _discover_local_peers(self):
        """Автоматическое обнаружение пиров в локальной сети"""
        def discover():
            # Определяем сеть по локальному IP
            if self.local_ip and self.local_ip != '127.0.0.1':
                network_parts = self.local_ip.split('.')
                network_prefix = '.'.join(network_parts[:-1]) + '.'
            else:
                network_prefix = '192.168.1.'
            
            print(f"🔍 Сканирую локальную сеть {network_prefix}* в поиске пиров...")
            
            scanned = 0
            for i in range(1, 255):
                ip = f"{network_prefix}{i}"
                if ip != self.local_ip:
                    for port in range(5000, 5003):  # Сканируем первые 3 порта
                        try:
                            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            test_socket.settimeout(0.2)
                            result = test_socket.connect_ex((ip, port))
                            if result == 0:
                                self.connect_to_peer(ip, port)
                            test_socket.close()
                        except:
                            pass
                scanned += 1
                if scanned % 50 == 0:
                    print(f"   Сканирование: {scanned}/254 ...")
            
            print(f"✅ Поиск завершён. Найдено пиров: {len(self.peers)}")
        
        threading.Thread(target=discover, daemon=True).start()
    
    def send_file_to_peer(self, filepath: str, peer_host: str, peer_port: int, 
                          recipient: str = None, group_id: str = None) -> Tuple[bool, str]:
        """Отправляет файл пиру (упрощенная версия)"""
        import os
        
        if not os.path.exists(filepath):
            return False, "Файл не найден"
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer_host, peer_port))
            
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            # Отправляем метаданные
            metadata = f"FILE:{filename}:{file_size}"
            sock.send(metadata.encode())
            
            # Отправляем файл
            with open(filepath, 'rb') as f:
                sent = 0
                while sent < file_size:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    sock.send(chunk)
                    sent += len(chunk)
            
            sock.close()
            return True, f"Файл {filename} отправлен"
            
        except socket.timeout:
            return False, "Таймаут при отправке файла"
        except Exception as e:
            return False, f"Ошибка: {e}"
    
    def search_history(self, keyword: str) -> List[Dict]:
        """Поиск по истории сообщений"""
        results = []
        for msg in self.messages:
            if keyword.lower() in msg.content.lower():
                results.append({
                    'timestamp': msg.timestamp,
                    'sender': msg.sender,
                    'message': msg.content
                })
        return results
    
    def show_routing_table(self) -> str:
        info = f"╔══════════════════════════════════════════════════════════╗\n"
        info += f"║                    ИНФОРМАЦИЯ О УЗЛЕ                      ║\n"
        info += f"╚══════════════════════════════════════════════════════════╝\n\n"
        info += f"👤 Имя пользователя: {self.username}\n"
        info += f"🔌 Локальный порт: {self.port}\n"
        info += f"📍 Локальный IP: {self.local_ip}\n"
        if self.public_ip and self.public_ip != self.local_ip:
            info += f"🌐 Внешний IP: {self.public_ip}\n"
        if self.relay_registered:
            info += f"📡 Релей-сервер: {self.relay_host}:{self.relay_port}\n"
        info += f"\n👥 Подключенные пиры: {len(self.peers)}\n"
        
        if self.peers:
            info += f"\n{'─' * 50}\n"
            info += f"  IP адрес                 Порт     Статус\n"
            info += f"{'─' * 50}\n"
            for host, port in self.peers:
                info += f"  {host:<23} {port:<8}  ✅ онлайн\n"
        
        info += f"\n{'─' * 50}\n"
        info += f"💬 Всего сообщений: {len(self.messages)}\n"
        
        return info
    
    def get_peers_list(self) -> List[Tuple[str, int]]:
        return list(self.peers)
    
    def remove_peer(self, host: str, port: int):
        """Удаляет пира из списка"""
        self.peers.discard((host, port))
        print(f"🔌 Отключен от {host}:{port}")
    
    def stop(self):
        self.running = False
        self.server_socket.close()
        print("👋 Узел остановлен")
        if self.relay_registered:
            print("   (рекомендуется также отключиться от релей-сервера)")
    
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
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.host = host
        self.port = port
        self.peers = {}  
        self.running = True
    
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(100)
        
        print(f"🚀 Релей-сервер запущен на {self.host}:{self.port}")
        print(f"   Ожидание регистрации пиров...")
        
        while self.running:
            try:
                client, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()
            except:
                break
        
        server.close()
    
    def _handle_client(self, client: socket.socket, addr: tuple):
        try:
            data = client.recv(4096).decode()
            request = json.loads(data)
            
            if request['type'] == 'register':
                username = request['username']
                ip = request.get('ip', addr[0])  
                port = request['port']
                
                self.peers[username] = {
                    'ip': ip,
                    'port': port,
                    'last_seen': time.time()
                }
                
                self._cleanup_old_peers()
                
                client.send(json.dumps({'status': 'ok'}).encode())
                print(f"✅ Зарегистрирован пир: {username} ({ip}:{port})")
                
            elif request['type'] == 'find':
                username = request['username']
                peer = self.peers.get(username)
                
                if peer and (time.time() - peer['last_seen']) < 300:  
                    client.send(json.dumps({
                        'found': True,
                        'ip': peer['ip'],
                        'port': peer['port']
                    }).encode())
                    print(f"🔍 Найден пир: {username} ({peer['ip']}:{peer['port']})")
                else:
                    client.send(json.dumps({'found': False}).encode())
                    print(f"Пир не найден: {username}")
            
            elif request['type'] == 'unregister':
                username = request['username']
                if username in self.peers:
                    del self.peers[username]
                    print(f"👋 Пир отключился: {username}")
                client.send(json.dumps({'status': 'ok'}).encode())
            
            client.close()
            
        except Exception as e:
            print(f"Ошибка обработки клиента: {e}")
            client.close()
    
    def _cleanup_old_peers(self):
        now = time.time()
        to_remove = [name for name, info in self.peers.items() if now - info['last_seen'] > 300]
        for name in to_remove:
            del self.peers[name]
            print(f"🗑️ Удалён устаревший пир: {name}")
    
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