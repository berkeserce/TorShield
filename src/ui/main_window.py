from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QMessageBox, QSystemTrayIcon,
                             QMenu, QApplication, QStyle)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QFont, QAction
import requests
import socks
import socket
import os
import psutil
import time
import json
import sys

from src.ui.settings_dialog import SettingsDialog
from src.utils.system_utils import set_system_proxy, get_tor_path
from src.utils.tor_utils import is_port_in_use, create_tor_config, launch_tor, create_controller
from src.models.connection_history import ConnectionHistory

class TorWorker(QThread):
    status = Signal(str)
    finished = Signal(bool, str, str)
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.is_connecting = True
        self.is_running = True
        
    def run(self):
        try:
            if self.is_connecting:
                self._connect_to_tor()
            else:
                self._disconnect_from_tor()
        except Exception as e:
            self.finished.emit(False, str(e), "")
        finally:
            self.is_running = False
            
    def stop(self):
        self.is_running = False
        self.wait()
        self.quit()
            
    def _connect_to_tor(self):
        original_socket = socket.socket
        try:
            # Terminate Tor processes
            self.status.emit('Stopping existing Tor processes...')
            for proc in psutil.process_iter(['pid', 'name']):
                if 'tor.exe' in proc.info['name'].lower():
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except:
                        try:
                            proc.kill()
                        except:
                            pass
            time.sleep(3)
            
            # Disable proxy settings
            self.status.emit('Disabling Windows proxy settings...')
            set_system_proxy(False)
            time.sleep(1)
            
            if is_port_in_use(9050) or is_port_in_use(9051):
                raise Exception("Port 9050/9051 is still in use!")
            
            self.status.emit('Starting Tor...')
            if not self.main_window.start_tor():
                self.finished.emit(False, "Failed to start Tor", "")
                return

            self.status.emit('Waiting for Tor service to start...')
            for _ in range(3):
                if is_port_in_use(9051):
                    break
            time.sleep(1)
            controller_retries = 3
            while controller_retries > 0:
                if self.main_window.controller and self.main_window.controller.is_authenticated():
                    break
                controller_retries -= 1
                if controller_retries > 0:
                    self.status.emit('Waiting for Tor controller...')
                    time.sleep(3)
            
            if not self.main_window.controller or not self.main_window.controller.is_authenticated():
                raise Exception("Tor controller is not ready!")

            self.status.emit('Setting up SOCKS proxy...')
            socket._original_socket = original_socket
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket

            self.status.emit('Setting up system proxy...')
            if not set_system_proxy(True):
                socket.socket = original_socket
                self.finished.emit(False, "System Proxy Error!", "")
                return

            max_retries = 3
            retry_count = 0
            retry_delay = 5
            while retry_count < max_retries:
                try:
                    self.status.emit('Testing Tor connection...')
                    session = requests.Session()
                    session.trust_env = False
                    
                    proxies = {
                        'http': 'socks5h://127.0.0.1:9050',
                        'https': 'socks5h://127.0.0.1:9050'
                    }
                    
                    if not self.main_window.controller.is_alive():
                        raise Exception("Tor service is not responding!")
                    
                    try:
                        response = session.get('https://check.torproject.org/api/ip', 
                                           timeout=15,
                                           verify=True,
                                           proxies=proxies)
                    except requests.exceptions.RequestException as e:
                        error_msg = "Connection timed out" if isinstance(e, requests.exceptions.Timeout) else \
                                    "Connection refused" if isinstance(e, requests.exceptions.ConnectionError) else \
                                    "SSL/TLS error" if isinstance(e, requests.exceptions.SSLError) else \
                                    f"Connection error: {str(e)}"
                        raise Exception(error_msg)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('IsTor', False):
                            current_ip = data.get('IP', 'Unknown')
                            self.finished.emit(True, "", current_ip)
                            return
                        else:
                            raise Exception("Tor connection could not be verified!")
                    else:
                        raise Exception(f'Could not get IP address! Status code: {response.status_code}')
                        
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if retry_count < max_retries:
                        self.status.emit(f'Connection attempt {retry_count + 1}/{max_retries}... ({error_msg})')
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 15)
                    else:
                        raise Exception(f"Connection error: {error_msg}")
                        
        except Exception as e:
            socket.socket = original_socket
            self.finished.emit(False, str(e), "")
            
    def _disconnect_from_tor(self):
        try:
            if self.main_window.controller:
                try:
                    self.main_window.controller.close()
                except:
                    pass
                self.main_window.controller = None
            
            set_system_proxy(False)
            
            if hasattr(socket, 'socket') and socket.socket == socks.socksocket:
                socket.socket = socket._original_socket if hasattr(socket, '_original_socket') else socket._socketobject
            
            self.main_window._cleanup_tor_processes()
            
            if is_port_in_use(9050) or is_port_in_use(9051):
                raise Exception("Ports are still in use!")
            
            self.finished.emit(True, "", "")
            
        except Exception as e:
            self.finished.emit(False, str(e), "")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loadSettings()
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.svg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.initUI()
        self.is_connected = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.connection_start_time = 0
        self.tor_path = get_tor_path()
        self.controller = None
        self.tor_process = None
        self.worker = None
        
        self.last_download = 0
        self.last_upload = 0
        self.last_time = time.time()
        
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_connection_status)
        self.speed_timer.setInterval(1000)
        
        self.ip_change_timer = QTimer()
        self.ip_change_timer.timeout.connect(self.auto_change_ip)
        
        self.connection_history = ConnectionHistory() if self.settings.get('save_history', True) else None
        
        self.create_tray_icon()
        
        if not self.tor_path:
            QMessageBox.critical(self, "Tor Not Found",
                               "Tor files not found. Please make sure the 'tor' folder is in the application directory.",
                               QMessageBox.StandardButton.Ok)
            sys.exit(1)
            
        if self.settings.get('auto_connect', False):
            QTimer.singleShot(1000, self.connect_to_tor)
            
    def loadSettings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                'auto_connect': False,
                'minimize_to_tray': True,
                'save_history': True,
                'show_speed': True,
                'proxy_host': '127.0.0.1',
                'proxy_port': '9050'
            }
            
    def initUI(self):
        self.setWindowTitle('TorShield')
        self.setFixedSize(350, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 25, 20, 20)
        
        status_frame = QWidget()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(12)
        status_layout.setContentsMargins(15, 15, 15, 15)
        status_frame.setStyleSheet("background-color: #222222; border-radius: 10px;")
        
        self.status_label = QLabel('Connection Status: Disconnected')
        self.status_label.setObjectName("status_label")
        self.ip_label = QLabel('IP Address: -')
        self.time_label = QLabel('Connection Time: -')
        self.speed_label = QLabel('Download: - KB/s | Upload: - KB/s')
        self.connection_status = QLabel('Connection: -')
        
        for label in [self.status_label, self.ip_label, self.time_label, 
                     self.speed_label, self.connection_status]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont('Segoe UI', 10))
            status_layout.addWidget(label)
        
        self.speed_label.setVisible(self.settings.get('show_speed', True))
        layout.addWidget(status_frame)
        
        layout.addStretch()
        
        buttons_frame = QWidget()
        buttons_layout = QVBoxLayout(buttons_frame)
        buttons_layout.setSpacing(15)
        buttons_layout.setContentsMargins(0, 10, 0, 10)
        
        self.connect_button = QPushButton('Connect')
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        self.connect_button.setFixedHeight(45)
        buttons_layout.addWidget(self.connect_button)
        
        self.change_ip_button = QPushButton('Change IP')
        self.change_ip_button.clicked.connect(self.change_ip)
        self.change_ip_button.setFont(QFont('Segoe UI', 10))
        self.change_ip_button.setFixedHeight(40)
        self.change_ip_button.setEnabled(False)
        buttons_layout.addWidget(self.change_ip_button)
        
        self.settings_button = QPushButton('Settings')
        self.settings_button.clicked.connect(self.showSettings)
        self.settings_button.setFont(QFont('Segoe UI', 10))
        self.settings_button.setFixedHeight(40)
        buttons_layout.addWidget(self.settings_button)
        
        layout.addWidget(buttons_frame)
        
        footer_layout = QHBoxLayout()
        
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #808080; font-size: 10px;")
        
        copyright_label = QLabel("© 2025 TorShield")
        copyright_label.setStyleSheet("color: #808080; font-size: 10px;")
        
        footer_layout.addWidget(copyright_label)
        footer_layout.addStretch()
        footer_layout.addWidget(version_label)
        
        layout.addLayout(footer_layout)
        
        self._apply_styles()
        
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1A1A1A; }
            QLabel { 
                color: #E0E0E0;
                margin: 5px;
                font-weight: normal;
                font-family: 'Segoe UI';
            }
            QLabel#status_label { font-weight: bold; }
            QLabel#status_label[text*="Disconnected"],
            QLabel#status_label[text*="disconnecting"],
            QLabel#status_label[text*="Error"] { color: #FF0000 !important; }
            QPushButton {
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border: none !important;
                padding: 10px;
                border-radius: 8px;
                min-width: 150px;
                font-weight: normal;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #404040; color: #FFFFFF; }
            QPushButton:pressed { background-color: #505050; }
            QPushButton:disabled { background-color: #1A1A1A; color: #808080; }
            QMessageBox { background-color: #1A1A1A; color: #E0E0E0; }
            QMessageBox QLabel { color: #E0E0E0; }
            QMessageBox QPushButton { min-width: 80px; }
            QMenu {
                background-color: #1A1A1A;
                color: #E0E0E0;
                border: 1px solid #404040;
            }
            QMenu::item:selected { background-color: #404040; }
            QMenu::item:pressed { background-color: #505050; }
        """)
        
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #006400;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #008000; }
            QPushButton:pressed { background-color: #004D00; }
            QPushButton[text="Disconnect"],
            QPushButton[text="Disconnecting..."] {
                background-color: #FF0000 !important;
                color: #FFFFFF !important;
                border: 1px solid #FF0000 !important;
            }
            QPushButton[text="Connect"] {
                background-color: #006400 !important;
                color: white !important;
            }
            QPushButton[text="Disconnect"]:hover,
            QPushButton[text="Disconnecting..."]:hover { background-color: #FF3333 !important; }
            QPushButton[text="Disconnect"]:pressed,
            QPushButton[text="Disconnecting..."]:pressed { background-color: #CC0000 !important; }
            QPushButton[text="Connecting..."] { background-color: #006400; }
        """)
        
        self.status_label.setStyleSheet('color: #FF0000; font-weight: bold;')
        self.connection_status.setStyleSheet('color: #E0E0E0;')
        
        self.change_ip_button.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #505050; }
            QPushButton:pressed { background-color: #303030; }
            QPushButton:disabled { background-color: #2D2D2D; color: #808080; }
        """)
        
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tor', 'tor.ico')
        
        self.tray_icon.setIcon(QIcon(icon_path) if os.path.exists(icon_path) 
                              else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        tray_menu = QMenu()
        actions = {
            "Show/Hide": self.toggleVisibility,
            "Connect": self.toggle_connection,
            "Connection History": self.show_connection_history,
            "Exit": self.quit_application
        }
        
        for text, slot in actions.items():
            action = QAction(text, self)
            action.triggered.connect(slot)
            tray_menu.addAction(action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.toggleVisibility)
            


    def update_connection_status(self):
        if not self.is_connected or not self.controller:
            return
        
        try:
            # Update speed information
            if self.settings.get('show_speed', True):
                current_time = time.time()
                time_diff = current_time - self.last_time
                
                if time_diff > 0:
                    bytes_read = self.controller.get_info('traffic/read')
                    bytes_written = self.controller.get_info('traffic/written')
                    
                    bytes_read = int(bytes_read) if bytes_read else 0
                    bytes_written = int(bytes_written) if bytes_written else 0
                    
                    download_speed = (bytes_read - self.last_download) / time_diff / 1024
                    upload_speed = (bytes_written - self.last_upload) / time_diff / 1024
                    
                    self.speed_label.setText(f'Download: {download_speed:.1f} KB/s | Upload: {upload_speed:.1f} KB/s')
                    
                    self.last_download = bytes_read
                    self.last_upload = bytes_written
                    self.last_time = current_time
                    
            if self.controller.is_alive():
                self.connection_status.setText('Connection: Good')
                self.connection_status.setStyleSheet('color: #00E676;')
            else:
                self.connection_status.setText('Connection: Weak')
                self.connection_status.setStyleSheet('color: #FFD740;')
                    
        except Exception as e:
            print(f"Error updating connection status: {str(e)}")
            self.speed_label.setText('Download: - KB/s | Upload: - KB/s')
            self.connection_status.setText('Connection: Error')
            self.connection_status.setStyleSheet('color: #FF5252;')
            
    def show_connection_history(self):
        if not self.connection_history:
            QMessageBox.information(self, "Information", "Connection history is disabled.")
            return
            
        connections = self.connection_history.get_last_connections()
        if not connections:
            QMessageBox.information(self, "Connection History", "No connection history yet.")
            return
            
        history_text = "Recent Connections:\n\n"
        for conn in reversed(connections):
            hours = conn['duration'] // 3600
            minutes = (conn['duration'] % 3600) // 60
            seconds = conn['duration'] % 60
            history_text += (f"IP: {conn['ip']}\n"
                           f"Date: {conn['timestamp']}\n"
                           f"Duration: {hours}:{minutes:02d}:{seconds:02d}\n"
                           f"{'-' * 30}\n")
            
        QMessageBox.information(self, "Bağlantı Geçmişi", history_text)
        
    def start_tor(self):
        try:
            self.status_label.setText('Starting Tor...')
            QApplication.processEvents()

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "tor_data")
            
            if os.path.exists(data_dir):
                try:
                    for file in os.listdir(data_dir):
                        file_path = os.path.join(data_dir, file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception as e:
                            print(f"Error deleting file: {str(e)}")
                except Exception as e:
                    print(f"Error cleaning directory: {str(e)}")
            else:
                try:
                    os.makedirs(data_dir)
                except Exception as e:
                    print(f"Error creating directory: {str(e)}")

            self._cleanup_tor_processes()

            if is_port_in_use(9050) or is_port_in_use(9051):
                try:
                    self.status_label.setText('Cleaning used ports...')
                    QApplication.processEvents()
                    os.system('taskkill /F /IM tor.exe')
                    time.sleep(3)
                except Exception as e:
                    print(f"Error terminating Tor process: {str(e)}")

            self.status_label.setText('Creating Tor configuration...')
            QApplication.processEvents()
            exit_country = self.settings.get('exit_country', '')
            if exit_country:
                self.status_label.setText(f'Creating Tor configuration (via {exit_country})...')
                QApplication.processEvents()
            tor_config = create_tor_config(self.tor_path, data_dir, exit_country)
            if not tor_config:
                self.status_label.setText('Failed to create Tor configuration!')
                return False

            self.status_label.setText('Starting Tor service...')
            QApplication.processEvents()
            self.tor_process = launch_tor(
                self.tor_path,
                tor_config,
                lambda msg: self._update_status_with_events(msg)
            )
            
            if not self.tor_process:
                self.status_label.setText('Failed to start Tor!')
                return False
            
            time.sleep(3)
            
            self.status_label.setText('Creating Tor controller...')
            QApplication.processEvents()
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    if self.controller:
                        try:
                            self.controller.close()
                        except:
                            pass
                        self.controller = None
                    
                    self.controller = create_controller()
                    
                    if not self.controller:
                        raise Exception("Failed to create controller!")
                        
                    if not self.controller.is_authenticated():
                        raise Exception("Controller authentication failed!")
                    
                    if not self.controller.is_alive():
                        raise Exception("Controller is not responding!")
                    
                    self.status_label.setText('Tor controller ready.')
                    QApplication.processEvents()
                    return True
                        
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if retry_count >= max_retries:
                        self.status_label.setText(f'Tor controller error: {error_msg}')
                        self._cleanup_tor_processes()
                        return False
                    
                    self.status_label.setText(f'Retrying Tor controller ({retry_count}/{max_retries})...')
                    QApplication.processEvents()
                    time.sleep(3)
            
            return False
            
        except Exception as e:
            error_msg = str(e)
            error_texts = {
                "Permission denied": 'Permission Error: Please run as administrator',
                "Address already in use": 'Port Error: 9050/9051 in use',
                "Connection refused": 'Connection Error: Failed to start Tor service'
            }
            self.status_label.setText(error_texts.get(error_msg, f'Tor Başlatma Hatası: {error_msg}'))
            return False

    def _cleanup_tor_processes(self):
        try:
            if self.controller:
                try:
                    self.controller.close()
                except:
                    pass
                self.controller = None
            
            if self.tor_process:
                try:
                    parent = psutil.Process(self.tor_process.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.terminate()
                            child.wait(timeout=5)
                        except:
                            try:
                                child.kill()
                            except:
                                pass
                    parent.terminate()
                    parent.wait(timeout=5)
                except:
                    pass
                self.tor_process = None
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'tor.exe' in proc.info['name'].lower():
                        proc.terminate()
                        proc.wait(timeout=5)
                except:
                    try:
                        proc.kill()
                    except:
                        pass
            
            time.sleep(3)
            
        except Exception as e:
            print(f"Tor cleanup error: {str(e)}")

    def toggle_connection(self):
        if not self.is_connected:
            self.connect_to_tor()
        else:
            self.disconnect_from_tor()
            
    def connect_to_tor(self):
        if self.is_connected or (self.worker is not None and self.worker.isRunning()):
            return

        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None

        self.connect_button.setEnabled(False)
        self.connect_button.setText('Connecting...')
        self.worker = TorWorker(self)
        self.worker.is_connecting = True
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_connection_finished)
        self.worker.start()
        
    def disconnect_from_tor(self):
        if not self.is_connected or (self.worker is not None and self.worker.isRunning()):
            return
            
        if self.is_connected and self.connection_history:
            ip_text = self.ip_label.text()
            ip = ip_text.replace('IP Address: ', '') if 'IP Address: ' in ip_text else 'Unknown'
            
            if hasattr(self, 'connection_start_time') and self.connection_start_time > 0:
                duration = int(time.time() - self.connection_start_time)
                self.connection_history.add_connection(ip, duration)
        
        for timer in [self.timer, self.speed_timer]:
            timer.stop()
        
        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
            
        self.connect_button.setEnabled(False)
        self.connect_button.setText('Disconnecting...')
        # Force style update to apply the red color
        self.connect_button.setStyleSheet(self.connect_button.styleSheet())
        self.connect_button.update()
        self.connect_button.repaint()
        self.status_label.setText('Disconnecting...')
        self.status_label.setStyleSheet('color: #FF0000; font-weight: bold;')
        
        self.worker = TorWorker(self)
        self.worker.is_connecting = False
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_disconnection_finished)
        self.worker.start()
        
    def _on_connection_finished(self, success, error_message, ip):
        self.connect_button.setEnabled(True)
        
        if success:
            self.is_connected = True
            self.change_ip_button.setEnabled(not self.settings.get('auto_ip_change', False))
            self.connection_start_time = time.time()
            self.status_label.setText('Connection Status: Connected')
            self.status_label.setStyleSheet('color: #00E676; font-weight: bold;')
            self.connect_button.setText('Disconnect')
            self.connect_button.update()
            self.ip_label.setText(f'IP Address: {ip}')
            self.time_label.setText('Connection Time: 00:00:00')
            self.connection_status.setText('Connection: Good')
            self.connection_status.setStyleSheet('color: #00E676;')
            
            self.last_download = 0
            self.last_upload = 0
            self.last_time = time.time()
            self.timer.start(1000)
            self.speed_timer.start()
            
            if self.settings.get('auto_ip_change', False):
                interval = self.settings.get('ip_change_interval', 15) * 60 * 1000
                self.ip_change_timer.setInterval(interval)
                self.ip_change_timer.start()
            
            self.tray_icon.setToolTip(f'Tor Connected\nIP: {ip}')
        else:
            self.is_connected = False
            self.change_ip_button.setEnabled(False)
            self.status_label.setText(f'Connection Error: {error_message}')
            self.status_label.setStyleSheet('color: #FF0000; font-weight: bold;')
            self.connect_button.setText('Connect')
            self.ip_label.setText('IP Address: -')
            self.time_label.setText('Connection Time: -')
            self.connection_status.setText('Connection: -')
            self.connection_status.setStyleSheet('color: #E0E0E0;')
            if self.settings.get('show_speed', True):
                self.speed_label.setText('Download: - KB/s | Upload: - KB/s')
            
            self.ip_change_timer.stop()

    def _on_disconnection_finished(self, success, error_message, _):
        self.connect_button.setEnabled(True)
        
        if success:
            self.is_connected = False
            self.change_ip_button.setEnabled(False)
            self.status_label.setText('Connection Status: Disconnected')
            self.status_label.setStyleSheet('color: #FF0000; font-weight: bold;')
            self.connect_button.setText('Connect')
            # Apply the original style from _apply_styles
            self._apply_styles()
            self.connect_button.update()
            self.ip_label.setText('IP Address: -')
            self.time_label.setText('Connection Time: -')
            self.speed_label.setText('Download: - KB/s | Upload: - KB/s')
            self.connection_status.setText('Connection: -')
            self.connection_status.setStyleSheet('color: #E0E0E0;')
            self.speed_label.setVisible(self.settings.get('show_speed', True))
            
            self.ip_change_timer.stop()

    def closeEvent(self, event):
        if self.settings.get('minimize_to_tray', True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "TorShield",
                "Program continues running in the background.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            if self.is_connected:
                self.disconnect_from_tor()
            
            if self.worker:
                self.worker.stop()
                self.worker.deleteLater()
                self.worker = None
            
            for timer in [self.timer, self.speed_timer]:
                timer.stop()
            
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            
            event.accept()
        
    def _update_status_with_events(self, message):
        """Helper method to update status label with UI processing"""
        self.status_label.setText(message)
        QApplication.processEvents()
        
    def update_time(self):
        if hasattr(self, 'connection_start_time'):
            elapsed_time = int(time.time() - self.connection_start_time)
            hours = elapsed_time // 3600
            minutes = (elapsed_time % 3600) // 60
            seconds = elapsed_time % 60
            self.time_label.setText(f'Connection Time: {hours:02d}:{minutes:02d}:{seconds:02d}')
        
    def showSettings(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        self.speed_label.setVisible(self.settings.get('show_speed', True))

    def toggleVisibility(self):
        self.setVisible(not self.isVisible())

    def quit_application(self):
        if self.is_connected:
            self.disconnect_from_tor()
            
        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
            
        for timer in [self.timer, self.speed_timer]:
            timer.stop()
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        QApplication.quit()

    def update_auto_ip_change(self):
        if self.settings.get('auto_ip_change', False) and self.is_connected:
            interval = self.settings.get('ip_change_interval', 15) * 60 * 1000
            self.ip_change_timer.setInterval(interval)
            self.ip_change_timer.start()
            self.change_ip_button.setEnabled(False)
        else:
            self.ip_change_timer.stop()
            self.change_ip_button.setEnabled(self.is_connected)

    def auto_change_ip(self):
        if self.is_connected and self.controller:
            self.change_ip(auto=True)

    def change_ip(self, auto=False):
        if not self.is_connected or not self.controller:
            return
            
        try:
            self.change_ip_button.setEnabled(False)
            self.status_label.setText('Changing IP...')
            self.controller.signal('NEWNYM')
            
            old_ip = self.ip_label.text().replace('IP Address: ', '')
            
            def check_ip_changed():
                try:
                    session = requests.Session()
                    session.trust_env = False
                    response = session.get('https://check.torproject.org/api/ip',
                                        timeout=10,
                                        verify=True,
                                        proxies={
                                            'http': 'socks5h://127.0.0.1:9050',
                                            'https': 'socks5h://127.0.0.1:9050'
                                        })
                    
                    if response.status_code == 200:
                        data = response.json()
                        new_ip = data.get('IP', 'Unknown')
                        if new_ip != old_ip:
                            self.ip_label.setText(f'IP Address: {new_ip}')
                            self.status_label.setText('Connection Status: Connected')
                            self.status_label.setStyleSheet('color: #00E676; font-weight: bold;')
                            self.tray_icon.setToolTip(f'Tor Connected\nIP: {new_ip}')
                            
                            if auto and self.settings.get('show_ip_notification', True):
                                self.tray_icon.showMessage(
                                    "IP Changed",
                                    f"New IP: {new_ip}",
                                    QSystemTrayIcon.MessageIcon.Information,
                                    3000
                                )
                        else:
                            self.controller.signal('NEWNYM')
                            QTimer.singleShot(5000, check_ip_changed)
                            return
                except:
                    pass
                
                if not self.settings.get('auto_ip_change', False):
                    self.change_ip_button.setEnabled(True)
            
            QTimer.singleShot(5000, check_ip_changed)
            
        except:
            self.status_label.setText('IP change failed!')
            if not self.settings.get('auto_ip_change', False):
                self.change_ip_button.setEnabled(True)
