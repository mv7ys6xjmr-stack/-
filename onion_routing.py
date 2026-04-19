import socket
import threading
import json
from typing import List, Tuple
from cryptography.fernet import Fernet
import random

class OnionRouter:
    def __init__(self, node):
        self.node = node
        self.relay_peers = {}  
        self.routing_table = {}
        
    def create_onion_path(self, target_peer: str, path_length: int = 3) -> List[Tuple]:
        available_relays = list(self.node.peers)
        if len(available_relays) < path_length:
            return None
        
        relays = random.sample(available_relays, path_length)
        
        layers = []
        current_target = target_peer
        
        for relay in reversed(relays):
            layer = {
                'next_hop': current_target,
                'relay': relay
            }
            encrypted_layer = self.node.crypto.encrypt(json.dumps(layer))
            layers.insert(0, encrypted_layer)
            current_target = relay
        
        return {
            'entry_node': relays[0],
            'layers': layers,
            'final_target': target_peer
        }
    
    def send_onion_message(self, message: str, target_peer: str):
        onion = self.create_onion_path(target_peer)
        if not onion:
            return False, "Недостаточно пиров для создания анонимного маршрута"
        
        entry_node = onion['entry_node']
        
        packet = {
            'type': 'onion',
            'layers': onion['layers'],
            'final_target': onion['final_target']
        }
        
        self.node.send_raw_packet(packet, entry_node[0], entry_node[1])
        return True, "Анонимное сообщение отправлено"


class RelayNode:
    def __init__(self):
        self.relay_enabled = True
        self.max_relays = 5 
    def handle_relay_request(self, encrypted_layer: bytes, next_hop: Tuple):
        try:
            decrypted = self.node.crypto.decrypt(encrypted_layer)
            layer = json.loads(decrypted)
            
            if 'next_hop' in layer:
                self.relay_packet(layer['next_hop'], layer.get('remaining_layers', []))
            else:
                self.deliver_final_message(layer['message'])
                
        except Exception as e:
            print(f"Ошибка ретрансляции: {e}")