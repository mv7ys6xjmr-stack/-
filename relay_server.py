import socket
import threading
import json

class RelayServer:
    def __init__(self, port=5000):
        self.port = port
        self.peers = {}  #
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.port))
        server.listen(100)
        print(f"Relay сервер запущен на порту {self.port}")
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client, addr)).start()
    
    def handle_client(self, client, addr):
        data = client.recv(4096).decode()
        request = json.loads(data)
        
        if request['type'] == 'register':
            self.peers[request['username']] = (request['ip'], request['port'])
            client.send(json.dumps({'status': 'ok'}).encode())
            
        elif request['type'] == 'find':
            peer = self.peers.get(request['username'])
            if peer:
                client.send(json.dumps({'found': True, 'ip': peer[0], 'port': peer[1]}).encode())
            else:
                client.send(json.dumps({'found': False}).encode())
        
        client.close()
