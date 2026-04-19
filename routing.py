import heapq
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Route:
    target: str
    next_hop: str
    cost: int
    hops: List[str]

class RoutingTable:
    """DHT-подобная маршрутизация для P2P сети"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.routes: Dict[str, Route] = {}  # target -> Route
        self.neighbors: Dict[str, int] = {}  # neighbor -> latency
        self.sequence = 0
    
    def update_route(self, target: str, next_hop: str, cost: int, hops: List[str]):
        """Обновляет маршрут к цели"""
        current = self.routes.get(target)
        if not current or cost < current.cost:
            self.routes[target] = Route(target, next_hop, cost, hops)
            return True
        return False
    
    def add_neighbor(self, neighbor_id: str, latency: int = 1):
        """Добавляет соседа"""
        self.neighbors[neighbor_id] = latency
        # Обновляем прямой маршрут
        self.update_route(neighbor_id, neighbor_id, latency, [neighbor_id])
    
    def find_path(self, target: str) -> List[str]:
        """Находит путь к цели (алгоритм Дейкстры)"""
        if target == self.node_id:
            return [self.node_id]
        
        if target in self.routes:
            return [self.node_id] + self.routes[target].hops
        
        # Поиск через соседей
        distances = {self.node_id: 0}
        previous = {}
        visited = set()
        pq = [(0, self.node_id)]
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current == target:
                # Восстанавливаем путь
                path = []
                while current in previous:
                    path.append(current)
                    current = previous[current]
                path.append(self.node_id)
                return path[::-1]
            
            if current in visited:
                continue
            visited.add(current)
            
            # Проверяем соседей текущего узла
            if current in self.routes:
                for neighbor in self.routes[current].hops:
                    if neighbor not in visited:
                        new_dist = current_dist + 1
                        if new_dist < distances.get(neighbor, float('inf')):
                            distances[neighbor] = new_dist
                            previous[neighbor] = current
                            heapq.heappush(pq, (new_dist, neighbor))
        
        return []
    
    def get_next_hop(self, target: str) -> str:
        """Возвращает следующий узел для отправки сообщения"""
        path = self.find_path(target)
        return path[1] if len(path) > 1 else None
    
    def broadcast_route(self):
        """Генерирует broadcast сообщение о маршрутах"""
        self.sequence += 1
        route_update = {
            'type': 'route_update',
            'source': self.node_id,
            'sequence': self.sequence,
            'routes': {target: route.cost for target, route in self.routes.items()}
        }
        return route_update
    
    def process_route_update(self, update: dict, sender: str):
        """Обрабатывает обновление маршрутов от соседа"""
        if update['sequence'] <= getattr(self, f"last_seq_{sender}", 0):
            return False
        
        setattr(self, f"last_seq_{sender}", update['sequence'])
        
        updated = False
        for target, cost in update['routes'].items():
            new_cost = cost + self.neighbors.get(sender, 1)
            if self.update_route(target, sender, new_cost, [sender]):
                updated = True
        
        return updated
    
    def get_routing_info(self) -> str:
        """Возвращает информацию о маршрутизации для отладки"""
        info = f"Узел {self.node_id}\n"
        info += f"Соседи: {', '.join(self.neighbors.keys())}\n"
        info += "Маршруты:\n"
        for target, route in list(self.routes.items())[:10]:
            info += f"  → {target}: {route.next_hop} (cost={route.cost}, hops={len(route.hops)})\n"
        return info