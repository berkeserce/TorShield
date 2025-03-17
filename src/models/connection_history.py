import json
from datetime import datetime
import os

class ConnectionHistory:
    def __init__(self, max_entries=10):
        self.max_entries = max_entries
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'connection_history.json')
        self.connections = self.load_history()
        
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except:
            return []
            
    def save_history(self):
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.connections, f, indent=4)
        except Exception as e:
            print(f"Error saving connection history: {e}")
            
    def add_connection(self, ip, duration):
        connection = {
            'ip': ip,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration
        }
        
        self.connections.append(connection)
        
        if len(self.connections) > self.max_entries:
            self.connections = self.connections[-self.max_entries:]
            
        self.save_history()
        
    def get_last_connections(self, count=None):
        if count is None:
            count = self.max_entries
        return self.connections[-count:]
        
    def clear_history(self):
        """Clear all connection history"""
        self.connections = []
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False 