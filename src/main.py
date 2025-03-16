import sys
import os
import ctypes
import subprocess

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
from PySide6.QtGui import QIcon
from src.controllers.tor_controller import TorController

def main():
    run_as_admin()
    
    app = QApplication(sys.argv)
    
    # Uygulama simgesini ayarla
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'logo.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = TorController()
    window.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    main() 