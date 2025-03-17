import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import QTimer
from src.ui.main_window import MainWindow

class TorController(MainWindow):
    def __init__(self):
        super().__init__()
        
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection)
        self.connection_check_timer.start(5000)
        
        self.auto_reconnect_timer = QTimer()
        self.auto_reconnect_timer.timeout.connect(self.connect_to_tor)
        
    def check_connection(self):
        if not self.is_connected:
            return
            
        try:
            if not self.controller or not self.controller.is_alive():
                self.disconnect_from_tor()
                if self.settings.get('auto_reconnect', 0) > 0:
                    self.auto_reconnect_timer.start(self.settings.get('auto_reconnect', 0) * 60 * 1000)
        except:
            self.disconnect_from_tor()