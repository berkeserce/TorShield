import sys
import os
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        python_exe = sys.executable
        script = os.path.abspath(__file__)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, script, None, 1)
        sys.exit()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.controllers.tor_controller import TorController

def main():
    run_as_admin()
    
    app = QApplication(sys.argv)
    window = TorController()
    window.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    main() 