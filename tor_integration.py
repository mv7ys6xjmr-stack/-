import socks
import socket
import requests
import threading
from typing import Optional

class TorProxy:
    """Интеграция с Tor для анонимности"""
    
    def __init__(self, tor_port: int = 9050):
        self.tor_port = tor_port
        self.is_available = False
        self.session = None
        
    def check_tor(self) -> bool:
        """Проверяет доступность Tor"""
        try:
            test_socket = socks.socksocket()
            test_socket.set_proxy(socks.SOCKS5, "127.0.0.1", self.tor_port)
            test_socket.settimeout(5)
            test_socket.connect(("check.torproject.org", 80))
            test_socket.send(b"GET / HTTP/1.0\r\nHost: check.torproject.org\r\n\r\n")
            response = test_socket.recv(1024)
            test_socket.close()
            
            self.is_available = True
            return True
        except:
            self.is_available = False
            return False
    
    def create_tor_socket(self) -> socks.socksocket:
        """Создает сокет через Tor"""
        if not self.is_available:
            raise Exception("Tor не доступен")
        
        tor_socket = socks.socksocket()
        tor_socket.set_proxy(socks.SOCKS5, "127.0.0.1", self.tor_port)
        return tor_socket
    
    def get_onion_address(self) -> Optional[str]:
        """Получает .onion адрес (требуется запущенный Tor с HiddenService)"""
        # Это упрощенная версия, в реальности нужно читать hostname файл
        try:
            with open('/var/lib/tor/hidden_service/hostname', 'r') as f:
                return f.read().strip()
        except:
            return None
    
    def anonymize_request(self, url: str) -> Optional[bytes]:
        """Делает анонимный HTTP запрос через Tor"""
        if not self.is_available:
            return None
        
        try:
            self.session = requests.Session()
            self.session.proxies = {
                'http': f'socks5h://127.0.0.1:{self.tor_port}',
                'https': f'socks5h://127.0.0.1:{self.tor_port}'
            }
            response = self.session.get(url, timeout=10)
            return response.content
        except:
            return None