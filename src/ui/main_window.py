from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
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
            self.status.emit('Tor başlatılıyor...')
            if not self.main_window.start_tor():
                self.finished.emit(False, "Tor başlatılamadı", "")
                return

            self.status.emit('Tor servisi başlaması bekleniyor...')
            time.sleep(5)

            if not self.main_window.controller or not self.main_window.controller.is_authenticated():
                raise Exception("Tor kontrolcüsü hazır değil!")

            self.status.emit('SOCKS proxy ayarlanıyor...')
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket

            self.status.emit('Sistem proxy ayarlanıyor...')
            if not set_system_proxy(True):
                socket.socket = original_socket
                self.finished.emit(False, "Sistem Proxy Hatası!", "")
                return

            max_retries = 2
            retry_count = 0
            while retry_count < max_retries:
                try:
                    self.status.emit('Tor bağlantısı test ediliyor...')
                    session = requests.Session()
                    session.trust_env = False
                    
                    proxies = {
                        'http': 'socks5h://127.0.0.1:9050',
                        'https': 'socks5h://127.0.0.1:9050'
                    }
                    
                    response = session.get('https://check.torproject.org/api/ip', 
                                       timeout=10,
                                       verify=True,
                                       proxies=proxies)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('IsTor', False):
                            current_ip = data.get('IP', 'Bilinmiyor')
                            self.finished.emit(True, "", current_ip)
                            return
                        else:
                            raise Exception("Tor bağlantısı doğrulanamadı!")
                    else:
                        raise Exception(f'IP adresi alınamadı! Durum kodu: {response.status_code}')
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.status.emit(f'Bağlantı denemesi {retry_count}/{max_retries}...')
                        time.sleep(2)
                    else:
                        raise Exception(f"Bağlantı hatası: {str(e)}")
                        
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
            
            if hasattr(self, '_original_socket'):
                socket.socket = self._original_socket
            
            self.main_window._cleanup_tor_processes()
            
            if is_port_in_use(9050) or is_port_in_use(9051):
                raise Exception("Portlar hala kullanımda!")
            
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
        self.connection_time = 0
        self.tor_path = get_tor_path()
        self.controller = None
        self.tor_process = None
        self.worker = None
        
        self.last_download = 0
        self.last_upload = 0
        self.last_time = time.time()
        
        self.auto_reconnect_timer = QTimer()
        self.auto_reconnect_timer.timeout.connect(self.auto_reconnect)
        
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_connection_status)
        self.speed_timer.setInterval(1000)
        
        self.connection_history = ConnectionHistory() if self.settings.get('save_history', True) else None
        
        self.create_tray_icon()
        
        if not self.tor_path:
            QMessageBox.critical(self, "Tor Bulunamadı",
                               "Tor dosyaları bulunamadı. Lütfen 'tor' klasörünün uygulama dizininde olduğundan emin olun.",
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
                'proxy_port': '9050',
                'auto_reconnect': 0
            }
            
    def initUI(self):
        self.setWindowTitle('TorShield')
        self.setFixedSize(350, 350)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        self.status_label = QLabel('Bağlantı Durumu: Kapalı')
        self.ip_label = QLabel('IP Adresi: -')
        self.time_label = QLabel('Bağlantı Süresi: -')
        self.speed_label = QLabel('İndirme: - KB/s | Yükleme: - KB/s')
        self.connection_status = QLabel('Bağlantı: -')
        
        for label in [self.status_label, self.ip_label, self.time_label, 
                     self.speed_label, self.connection_status]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont('Segoe UI', 10))
            layout.addWidget(label)
        
        self.speed_label.setVisible(self.settings.get('show_speed', True))
        
        self.connect_button = QPushButton('Bağlan')
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setFont(QFont('Segoe UI', 10))
        layout.addWidget(self.connect_button)
        
        self.settings_button = QPushButton('Ayarlar')
        self.settings_button.clicked.connect(self.showSettings)
        self.settings_button.setFont(QFont('Segoe UI', 10))
        layout.addWidget(self.settings_button)
        
        self._apply_styles()
        
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #1A1A1A; 
            }
            QLabel { 
                color: #E0E0E0;
                margin: 5px;
                font-weight: normal;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: none;
                padding: 10px;
                border-radius: 5px;
                min-width: 150px;
                font-weight: normal;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { 
                background-color: #404040;
                color: #FFFFFF;
            }
            QPushButton:pressed { 
                background-color: #505050; 
            }
            QPushButton:disabled {
                background-color: #1A1A1A;
                color: #808080;
            }
            QMessageBox {
                background-color: #1A1A1A;
                color: #E0E0E0;
            }
            QMessageBox QLabel {
                color: #E0E0E0;
            }
            QMessageBox QPushButton {
                min-width: 80px;
            }
            QMenu {
                background-color: #1A1A1A;
                color: #E0E0E0;
                border: 1px solid #404040;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
            QMenu::item:pressed {
                background-color: #505050;
            }
        """)
        
        self.status_label.setStyleSheet('color: #E0E0E0;')
        self.connection_status.setStyleSheet("""
            QLabel[text="Bağlantı: İyi"] { color: #00E676; }
            QLabel[text="Bağlantı: Zayıf"] { color: #FFD740; }
            QLabel[text="Bağlantı: -"] { color: #E0E0E0; }
            QLabel[text="Bağlantı: Hata"] { color: #FF5252; }
        """)
        
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tor', 'tor.ico')
        
        self.tray_icon.setIcon(QIcon(icon_path) if os.path.exists(icon_path) 
                              else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        tray_menu = QMenu()
        actions = {
            "Göster/Gizle": self.toggleVisibility,
            "Bağlan": self.toggle_connection,
            "Bağlantı Geçmişi": self.show_connection_history,
            "Çıkış": self.quit_application
        }
        
        for text, slot in actions.items():
            action = QAction(text, self)
            action.triggered.connect(slot)
            tray_menu.addAction(action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggleVisibility()
            
    def auto_reconnect(self):
        if self.is_connected:
            self.status_label.setText('Otomatik yeniden bağlantı başlatılıyor...')
            self.connect_button.setText('Bağlanılıyor...')
            self.connect_button.setEnabled(False)
            
            self.disconnect_from_tor()
            
            self.status_label.setText('Yeniden bağlanmak için bekleniyor (5 saniye)...')
            QTimer.singleShot(5000, lambda: self._delayed_reconnect())

    def _delayed_reconnect(self):
        self.status_label.setText('Yeniden bağlantı başlatılıyor...')
        self.connect_to_tor()

    def update_connection_status(self):
        if not self.is_connected or not self.controller:
            return
            
        try:
            current_time = time.time()
            time_diff = current_time - self.last_time
            
            current_download = int(self.controller.get_info('traffic/read'))
            current_upload = int(self.controller.get_info('traffic/written'))
            
            download_speed = (current_download - self.last_download) / time_diff / 1024
            upload_speed = (current_upload - self.last_upload) / time_diff / 1024
            
            self.last_download = current_download
            self.last_upload = current_upload
            self.last_time = current_time
            
            if self.settings.get('show_speed', True):
                self.speed_label.setText(f'İndirme: {download_speed:.1f} KB/s | Yükleme: {upload_speed:.1f} KB/s')
                self.speed_label.setVisible(True)
            else:
                self.speed_label.setVisible(False)
            
            self.connection_status.setText('Bağlantı: İyi' if self.controller.is_alive() else 'Bağlantı: Zayıf')
            self.connection_status.setStyleSheet('color: lime;' if self.controller.is_alive() else 'color: yellow;')
        except:
            if self.settings.get('show_speed', True):
                self.speed_label.setText('İndirme: - KB/s | Yükleme: - KB/s')
            self.connection_status.setText('Bağlantı: Hata')
            self.connection_status.setStyleSheet('color: red;')
            
    def show_connection_history(self):
        if not self.connection_history:
            QMessageBox.information(self, "Bilgi", "Bağlantı geçmişi devre dışı.")
            return
            
        connections = self.connection_history.get_last_connections()
        if not connections:
            QMessageBox.information(self, "Bağlantı Geçmişi", "Henüz bağlantı geçmişi yok.")
            return
            
        history_text = "Son Bağlantılar:\n\n"
        for conn in reversed(connections):
            hours = conn['duration'] // 3600
            minutes = (conn['duration'] % 3600) // 60
            seconds = conn['duration'] % 60
            history_text += (f"IP: {conn['ip']}\n"
                           f"Tarih: {conn['timestamp']}\n"
                           f"Süre: {hours}:{minutes:02d}:{seconds:02d}\n"
                           f"{'-' * 30}\n")
            
        QMessageBox.information(self, "Bağlantı Geçmişi", history_text)
        
    def start_tor(self):
        try:
            self.status_label.setText('Tor başlatılıyor...')
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
                        except:
                            pass
                except:
                    pass
            else:
                os.makedirs(data_dir)

            self._cleanup_tor_processes()

            if is_port_in_use(9050) or is_port_in_use(9051):
                try:
                    os.system('taskkill /F /IM tor.exe')
                except:
                    pass

            self.status_label.setText('Tor yapılandırması oluşturuluyor...')
            tor_config = create_tor_config(self.tor_path, data_dir)
            if not tor_config:
                self.status_label.setText('Tor yapılandırması oluşturulamadı!')
                return False

            self.status_label.setText('Tor servisi başlatılıyor...')
            self.tor_process = launch_tor(
                self.tor_path,
                tor_config,
                lambda msg: self.status_label.setText(msg)
            )
            
            if not self.tor_process:
                self.status_label.setText('Tor başlatılamadı!')
                return False
            
            time.sleep(3)
            
            self.status_label.setText('Tor kontrolcüsü oluşturuluyor...')
            max_retries = 2
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
                        raise Exception("Kontrolcü oluşturulamadı!")
                        
                    if not self.controller.is_authenticated():
                        raise Exception("Kontrolcü kimlik doğrulaması başarısız!")
                    
                    self.status_label.setText('Tor kontrolcüsü hazır.')
                    return True
                        
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if retry_count >= max_retries:
                        self.status_label.setText(f'Tor kontrolcüsü hatası: {error_msg}')
                        self._cleanup_tor_processes()
                        return False
                    
                    self.status_label.setText(f'Tor kontrolcüsü yeniden deneniyor ({retry_count}/{max_retries})...')
                    time.sleep(1)
            
            return False
            
        except Exception as e:
            error_msg = str(e)
            error_texts = {
                "Permission denied": 'Yetki Hatası: Lütfen yönetici olarak çalıştırın',
                "Address already in use": 'Port Hatası: 9050/9051 kullanımda',
                "Connection refused": 'Bağlantı Hatası: Tor servisi başlatılamadı'
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
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Tor temizleme hatası: {str(e)}")

    def _disconnect_from_tor(self):
        try:
            if self.main_window.controller:
                try:
                    self.main_window.controller.close()
                except:
                    pass
                self.main_window.controller = None
            
            set_system_proxy(False)
            
            if hasattr(self, '_original_socket'):
                socket.socket = self._original_socket
            
            self.main_window._cleanup_tor_processes()
            
            if is_port_in_use(9050) or is_port_in_use(9051):
                raise Exception("Portlar hala kullanımda!")
            
            self.finished.emit(True, "", "")
            
        except Exception as e:
            self.finished.emit(False, str(e), "")
            
    def toggle_connection(self):
        if not self.is_connected:
            self.connect_to_tor()
        else:
            self.disconnect_from_tor()
            
    def connect_to_tor(self):
        if self.is_connected or (self.worker is not None and self.worker.isRunning()):
            return
            
        if is_port_in_use(9050) or is_port_in_use(9051):
            self.status_label.setText('Portlar kontrol ediliyor...')
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    if 'tor.exe' in proc.info['name'].lower():
                        proc.terminate()
                        proc.wait(timeout=5)
                time.sleep(2)
            except:
                pass
            
            if is_port_in_use(9050) or is_port_in_use(9051):
                QMessageBox.warning(self, "Hata", 
                    "Port 9050/9051 hala kullanımda!\nLütfen diğer Tor uygulamalarını kapatın.")
                self.connect_button.setEnabled(True)
                return
        
        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
            
        self.connect_button.setEnabled(False)
        self.connect_button.setText('Bağlanılıyor...')
        self.worker = TorWorker(self)
        self.worker.is_connecting = True
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_connection_finished)
        self.worker.start()
        
    def disconnect_from_tor(self):
        if not self.is_connected or (self.worker is not None and self.worker.isRunning()):
            return
            
        if self.is_connected and hasattr(self, 'current_ip') and self.connection_history:
            self.connection_history.add_connection(self.current_ip, self.connection_time)
        
        for timer in [self.timer, self.speed_timer, self.auto_reconnect_timer]:
            timer.stop()
        
        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
            
        self.connect_button.setEnabled(False)
        self.connect_button.setText('Bağlantı Kesiliyor...')
        self.status_label.setText('Bağlantı kesiliyor...')
        
        self.worker = TorWorker(self)
        self.worker.is_connecting = False
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_disconnection_finished)
        self.worker.start()
        
    def _on_connection_finished(self, success, error_message, ip):
        self.connect_button.setEnabled(True)
        
        if success:
            self.is_connected = True
            self.current_ip = ip
            self.status_label.setText('Bağlantı Durumu: Bağlı')
            self.status_label.setStyleSheet('color: lime;')
            self.connect_button.setText('Bağlantıyı Kes')
            self._update_button_style(True)
            self.ip_label.setText(f'IP Adresi: {ip}')
            
            self.connection_time = 0
            self.last_download = 0
            self.last_upload = 0
            self.last_time = time.time()
            self.timer.start(1000)
            self.speed_timer.start()
            
            reconnect_minutes = self.settings.get('auto_reconnect', 0)
            if reconnect_minutes > 0:
                self.status_label.setText(f'Bağlantı Durumu: Bağlı ({reconnect_minutes} dakika sonra yenilenecek)')
                self.auto_reconnect_timer.setInterval(reconnect_minutes * 60 * 1000)
                self.auto_reconnect_timer.start()
            
            self.tray_icon.setToolTip(f'Tor Bağlı\nIP: {ip}')
        else:
            self.is_connected = False
            self.status_label.setText(f'Bağlantı Hatası: {error_message}')
            self.connect_button.setText('Bağlan')
            self._update_button_style(False)
            self.ip_label.setText('IP Adresi: -')
            self.time_label.setText('Bağlantı Süresi: -')
            self.connection_status.setText('Bağlantı: -')
            self.connection_status.setStyleSheet('color: white;')
            if self.settings.get('show_speed', True):
                self.speed_label.setText('İndirme: - KB/s | Yükleme: - KB/s')
            
    def _on_disconnection_finished(self, success, error_message, _):
        self.connect_button.setEnabled(True)
        
        if success:
            self.is_connected = False
            self.status_label.setText('Bağlantı Durumu: Kapalı')
            self.status_label.setStyleSheet('color: white;')
            self.connect_button.setText('Bağlan')
            self._update_button_style(False)
            self.ip_label.setText('IP Adresi: -')
            self.time_label.setText('Bağlantı Süresi: -')
            self.connection_status.setText('Bağlantı: -')
            self.connection_status.setStyleSheet('color: white;')
            if self.settings.get('show_speed', True):
                self.speed_label.setText('İndirme: - KB/s | Yükleme: - KB/s')
            
            for timer in [self.timer, self.speed_timer, self.auto_reconnect_timer]:
                timer.stop()
            
            self.tray_icon.setToolTip('Tor Bağlantısı Kapalı')
            
            if self.worker:
                self.worker.deleteLater()
                self.worker = None
        else:
            self.status_label.setText(f'Bağlantıyı Kesme Hatası: {error_message}')
            
    def _update_button_style(self, is_connected):
        style = """
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                padding: 10px;
                border-radius: 5px;
                min-width: 150px;
                font-weight: normal;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{ 
                background-color: {hover_color}; 
                color: #FFFFFF;
            }}
            QPushButton:pressed {{ 
                background-color: {press_color}; 
            }}
            QPushButton:disabled {{
                background-color: #1A1A1A;
                color: #808080;
            }}
        """
        
        colors = {
            True: {
                'bg_color': '#2D2D2D',
                'text_color': '#FF5252',
                'hover_color': '#404040',
                'press_color': '#505050'
            },
            False: {
                'bg_color': '#2D2D2D',
                'text_color': '#00E676',
                'hover_color': '#404040',
                'press_color': '#505050'
            }
        }
        
        self.connect_button.setStyleSheet(style.format(**colors[is_connected]))
            
    def closeEvent(self, event):
        if self.settings.get('minimize_to_tray', True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "TorShield",
                "Program arka planda çalışmaya devam ediyor.",
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
            
            for timer in [self.timer, self.speed_timer, self.auto_reconnect_timer]:
                timer.stop()
            
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            
            event.accept()
        
    def update_time(self):
        self.connection_time += 1
        hours = self.connection_time // 3600
        minutes = (self.connection_time % 3600) // 60
        seconds = self.connection_time % 60
        self.time_label.setText(f'Bağlantı Süresi: {hours}:{minutes:02d}:{seconds:02d}')
        
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
            
        for timer in [self.timer, self.speed_timer, self.auto_reconnect_timer]:
            timer.stop()
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        QApplication.quit() 