import time
import random
import hashlib
from collections import deque
from threading import Lock

class MixNode:
    
    def __init__(self):
        self.message_queue = deque()
        self.lock = Lock()
        self.batch_size = 5
        self.delay_range = (1, 5)  
    def add_message(self, message: bytes, destination: str):
        with self.lock:
            self.message_queue.append((message, destination, time.time()))
        return True
    
    def mix_messages(self):
        while True:
            time.sleep(random.uniform(*self.delay_range))
            
            with self.lock:
                if len(self.message_queue) >= self.batch_size:
                    batch = [self.message_queue.popleft() 
                            for _ in range(min(self.batch_size, len(self.message_queue)))]
                    
                    random.shuffle(batch)
                    
                    for msg, dest, timestamp in batch:
                        delay = random.uniform(0.5, 2)
                        time.sleep(delay)
                        self.send_mixed_message(msg, dest)
    
    def send_mixed_message(self, message: bytes, destination: str):
        pass