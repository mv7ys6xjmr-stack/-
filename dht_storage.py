import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class DHTStorage:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.stored_messages: Dict[str, List[Dict]] = {}  
        self.replication_factor = 3  
    def get_storage_nodes(self, user_id: str) -> List[str]:
        hash_value = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
        
        peers = list(self.get_all_peers())
        
        if not peers:
            return []
        
        storage_nodes = []
        for i in range(self.replication_factor):
            index = (hash_value + i) % len(peers)
            storage_nodes.append(peers[index])
        
        return storage_nodes
    
    def store_offline_message(self, sender: str, recipient: str, message: str, 
                              ttl_hours: int = 168):  
        message_data = {
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
            'message_id': hashlib.sha256(f"{sender}{recipient}{message}{datetime.now()}".encode()).hexdigest()
        }
        storage_nodes = self.get_storage_nodes(recipient)
        
        stored = 0
        for node in storage_nodes:
            if self.store_on_peer(node, recipient, message_data):
                stored += 1
        
        return stored >= self.replication_factor // 2  
    def retrieve_offline_messages(self, user_id: str) -> List[Dict]:
        storage_nodes = self.get_storage_nodes(user_id)
        
        all_messages = []
        for node in storage_nodes:
            messages = self.retrieve_from_peer(node, user_id)
            all_messages.extend(messages)
        
        unique_messages = {}
        for msg in all_messages:
            msg_id = msg.get('message_id')
            if msg_id and msg_id not in unique_messages:
                unique_messages[msg_id] = msg
        
        now = datetime.now()
        current_messages = [
            msg for msg in unique_messages.values()
            if datetime.fromisoformat(msg['expires']) > now
        ]
        
        return current_messages
    
    def store_on_peer(self, peer: str, user_id: str, message: Dict) -> bool:
        try:
            request = {
                'type': 'store_message',
                'user_id': user_id,
                'message': message
            }
            response = self.send_rpc_request(peer, request)
            return response.get('success', False)
        except:
            return False
    
    def retrieve_from_peer(self, peer: str, user_id: str) -> List[Dict]:
        try:
            request = {
                'type': 'retrieve_messages',
                'user_id': user_id
            }
            response = self.send_rpc_request(peer, request)
            return response.get('messages', [])
        except:
            return []
    
    def send_rpc_request(self, peer: str, request: Dict) -> Dict:
        pass