import threading
import time
import json
from collections import deque
from typing import Set

class OfflineMessageQueue:
  
    def __init__(self, node):
        self.node = node
        self.pending_messages = deque()  
        self.delivered_messages: Set[str] = set()  
        self.retry_delays = [5, 15, 30, 60, 120, 300]  
        self.delivery_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.delivery_thread.start()
    
    def send_offline_message(self, recipient: str, message: str, ttl_hours: int = 24):
        message_id = f"{self.node.username}_{recipient}_{time.time()}"
        
        message_data = {
            'id': message_id,
            'sender': self.node.username,
            'recipient': recipient,
            'message': message,
            'timestamp': time.time(),
            'ttl': ttl_hours * 3600,
            'attempts': 0
        }
        
        self.pending_messages.append(message_data)
        
        self.find_delivery_route(recipient, message_data)
        
        return message_id
    
    def find_delivery_route(self, recipient: str, message: Dict):
        for peer_host, peer_port in self.node.peers:
            try:
                query = {
                    'type': 'find_recipient',
                    'recipient': recipient,
                    'message_id': message['id']
                }
                response = self.send_query(peer_host, peer_port, query)
                
                if response and response.get('found'):
                    self.delegate_delivery(peer_host, peer_port, message)
                    return True
            except:
                continue
        
        return False
    
    def delegate_delivery(self, peer_host: str, peer_port: int, message: Dict):
        delivery_request = {
            'type': 'deliver_offline',
            'message': message
        }
        self.send_message(peer_host, peer_port, delivery_request)
    
    def process_queue(self):
        while True:
            if self.pending_messages:
                message = self.pending_messages[0]
                if time.time() - message['timestamp'] > message['ttl']:
                    self.pending_messages.popleft()
                    continue
                
                if self.try_deliver(message):
                    self.pending_messages.popleft()
                else:
                    message['attempts'] += 1
                    
                    if message['attempts'] >= len(self.retry_delays):
                        self.pending_messages.popleft()
                    else:
                        delay = self.retry_delays[min(message['attempts'] - 1, len(self.retry_delays) - 1)]
                        time.sleep(delay)
            else:
                time.sleep(5)
    
    def try_deliver(self, message: Dict) -> bool:
        recipient = message['recipient']
        
        for peer_host, peer_port in self.node.peers:
            if self.is_recipient_online(peer_host, peer_port, recipient):
                return self.send_direct_message(peer_host, peer_port, message)
        
        return False
    
    def is_recipient_online(self, host: str, port: int, recipient: str) -> bool:
        try:
            check = {
                'type': 'who_are_you',
                'expected': recipient
            }
            response = self.send_query(host, port, check)
            return response and response.get('is_recipient', False)
        except:
            return False