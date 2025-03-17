from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QGroupBox, QCheckBox, QSpinBox, QLabel, QPushButton,
                             QLineEdit, QScrollArea, QMessageBox, QWidget, QComboBox,
                             QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QIcon
import json
import os
from src.utils.country_codes import get_all_countries, get_popular_countries

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        self.loadSettings()
        self._apply_styles()
        
    def initUI(self):
        self.setWindowTitle('TorShield Settings')
        self.setFixedSize(600, 600)
        
        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header section
        header = self._create_header()
        main_layout.addLayout(header)
        
        # Tab widget
        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_general_tab(), "General")
        tab_widget.addTab(self._create_country_tab(), "Country Selection")
        tab_widget.addTab(self._create_history_tab(), "History")
        main_layout.addWidget(tab_widget)
        
        # Bottom buttons
        buttons = self._create_buttons()
        main_layout.addLayout(buttons)
        
        self.setLayout(main_layout)

    def _create_header(self):
        header = QHBoxLayout()
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets/logo.png')
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
            logo_label.setPixmap(logo_pixmap)
        
        # Title
        title = QLabel("TorShield Settings")
        title.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        
        header.addWidget(logo_label)
        header.addWidget(title)
        header.addStretch()
        
        return header

    def _create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Startup Settings
        startup_group = QGroupBox("Startup Settings")
        startup_layout = QVBoxLayout()
        
        self.auto_start = QCheckBox("Start with Windows")
        self.auto_connect = QCheckBox("Connect automatically at startup")
        self.minimize_to_tray = QCheckBox("Minimize to system tray when closed")
        
        startup_layout.addWidget(self.auto_start)
        startup_layout.addWidget(self.auto_connect)
        startup_layout.addWidget(self.minimize_to_tray)
        startup_group.setLayout(startup_layout)
        
        # IP Change Settings
        ip_group = QGroupBox("IP Change Settings")
        ip_layout = QVBoxLayout()
        
        self.auto_ip_change = QCheckBox("Change IP automatically")
        self.auto_ip_change.stateChanged.connect(self._toggle_ip_interval)
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("IP change interval:"))
        self.ip_interval = QSpinBox()
        self.ip_interval.setMinimum(1)
        self.ip_interval.setMaximum(60)
        self.ip_interval.setValue(15)
        interval_layout.addWidget(self.ip_interval)
        interval_layout.addWidget(QLabel("minutes"))
        interval_layout.addStretch()
        
        self.show_ip_notification = QCheckBox("Show notification when IP changes")
        
        ip_layout.addWidget(self.auto_ip_change)
        ip_layout.addLayout(interval_layout)
        ip_layout.addWidget(self.show_ip_notification)
        ip_group.setLayout(ip_layout)
        
        # Appearance Settings
        appearance_group = QGroupBox("Appearance Settings")
        appearance_layout = QVBoxLayout()
        
        self.show_speed = QCheckBox("Show connection speed")
        
        appearance_layout.addWidget(self.show_speed)
        appearance_group.setLayout(appearance_layout)
        
        layout.addWidget(startup_group)
        layout.addWidget(ip_group)
        layout.addWidget(appearance_group)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _create_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # History View
        history_group = QGroupBox("Connection History")
        history_layout = QVBoxLayout()
        
        self.history_area = QScrollArea()
        self.history_area.setWidgetResizable(True)
        self.history_content = QWidget()
        self.history_content_layout = QVBoxLayout()
        self.history_text = QLabel()
        self.history_text.setWordWrap(True)
        
        self.history_content_layout.addWidget(self.history_text)
        self.history_content_layout.addStretch()
        self.history_content.setLayout(self.history_content_layout)
        self.history_area.setWidget(self.history_content)
        
        # Geçmiş Yönetimi
        history_buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_history_text)
        self.clear_button = QPushButton("Clear History")
        self.clear_button.clicked.connect(self._clear_history)
        
        history_buttons.addWidget(self.refresh_button)
        history_buttons.addWidget(self.clear_button)
        
        history_layout.addWidget(self.history_area)
        history_layout.addLayout(history_buttons)
        history_group.setLayout(history_layout)
        
        layout.addWidget(history_group)
        tab.setLayout(layout)
        return tab

    def _create_buttons(self):
        buttons = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.saveSettings)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        
        return buttons

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3C3C3C;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00E676;
            }
            QLabel {
                color: #FFFFFF;
            }
            QCheckBox {
                color: #FFFFFF;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #3C3C3C;
                border-radius: 4px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #00E676;
                background-color: #00E676;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 14 14'%3E%3Cpath fill='%23ffffff' d='M11.4,3.6l-5.8,5.8L2.6,6.4c-0.4-0.4-1-0.4-1.4,0s-0.4,1,0,1.4l3.8,3.8c0.2,0.2,0.4,0.3,0.7,0.3s0.5-0.1,0.7-0.3 l6.4-6.4c0.4-0.4,0.4-1,0-1.4S11.8,3.2,11.4,3.6z'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: center;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
            }
            QPushButton:pressed {
                background-color: #4C4C4C;
            }
            QScrollArea {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2D2D2D;
                color: #FFFFFF;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3C3C3C;
                color: #00E676;
            }
        """)

    def _toggle_ip_interval(self, state):
        self.ip_interval.setEnabled(state == Qt.CheckState.Checked.value)
        self.show_ip_notification.setEnabled(state == Qt.CheckState.Checked.value)

    def loadSettings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
        except:
            settings = {}
        
        # Genel ayarlar
        self.auto_start.setChecked(settings.get('auto_start', False))
        self.auto_connect.setChecked(settings.get('auto_connect', False))
        self.minimize_to_tray.setChecked(settings.get('minimize_to_tray', True))
        self.show_speed.setChecked(settings.get('show_speed', True))
        
        # IP değiştirme ayarları
        self.auto_ip_change.setChecked(settings.get('auto_ip_change', False))
        self.ip_interval.setValue(settings.get('ip_change_interval', 15))
        self.show_ip_notification.setChecked(settings.get('show_ip_notification', True))
        self._toggle_ip_interval(self.auto_ip_change.checkState())
        
        # Ülke seçimi ayarları
        exit_country = settings.get('exit_country', '')
        if exit_country:
            for i in range(self.country_combo.count()):
                if self.country_combo.itemData(i) == exit_country:
                    self.country_combo.setCurrentIndex(i)
                    break
        

        
        self.update_history_text()

    def saveSettings(self):

        
        settings = {
            'auto_start': self.auto_start.isChecked(),
            'auto_connect': self.auto_connect.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked(),
            'show_speed': self.show_speed.isChecked(),
            'auto_ip_change': self.auto_ip_change.isChecked(),
            'ip_change_interval': self.ip_interval.value(),
            'show_ip_notification': self.show_ip_notification.isChecked(),
            'exit_country': self.country_combo.currentData()
        }
        
        try:
            # Ayarları dosyaya kaydet
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Ana pencere ayarlarını güncelle
            if self.parent:
                self.parent.settings = settings
                self.parent.speed_label.setVisible(settings['show_speed'])
                self.parent.update_auto_ip_change()
                
                # Eğer bağlıysa ve ülke değiştiyse, yeniden bağlanma öner
                if self.parent.is_connected and 'exit_country' in settings:
                    QMessageBox.information(self, "Information", "Country selection has changed. You need to reconnect for the changes to take effect.")
                
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {str(e)}")

    def _create_country_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Country Selection Settings
        country_group = QGroupBox("Country-Based Exit Node")
        country_layout = QVBoxLayout()
        
        # Description
        description = QLabel("You can choose which country your Tor connection will exit from. "
                           "This allows websites you visit to see you as a user "
                           "coming from your selected country.")
        description.setWordWrap(True)
        country_layout.addWidget(description)
        
        # Country selection
        country_select_layout = QHBoxLayout()
        country_select_layout.addWidget(QLabel("Exit Country:"))
        
        self.country_combo = QComboBox()
        self.country_combo.addItem("Automatic (No Country Selection)", "")
        
        # Tüm ülkeler
        all_countries = get_all_countries()
        for code, name in sorted(all_countries.items(), key=lambda x: x[1]):
            self.country_combo.addItem(f"{name} ({code})", code)
        
        country_select_layout.addWidget(self.country_combo)
        country_layout.addLayout(country_select_layout)
        
        country_group.setLayout(country_layout)
        layout.addWidget(country_group)


        layout.addStretch()
        tab.setLayout(layout)
        return tab
        

    
    def _clear_history(self):
        if hasattr(self.parent, 'connection_history') and self.parent.connection_history:
            self.parent.connection_history.clear_history()
            self.update_history_text()
            QMessageBox.information(self, "Success", "Connection history cleared.")
    
    def update_history_text(self):
        if not hasattr(self.parent, 'connection_history') or not self.parent.connection_history:
            self.history_text.setText("Connection history is disabled or empty.")
            return
            
        connections = self.parent.connection_history.get_last_connections()
        if not connections:
            self.history_text.setText("No connection history yet.")
            return
            
        history_text = ""
        for conn in reversed(connections):
            hours = conn['duration'] // 3600
            minutes = (conn['duration'] % 3600) // 60
            seconds = conn['duration'] % 60
            
            history_text += (f"<div style='margin: 10px 0; padding: 10px; background: #2D2D2D; border-radius: 4px;'>"
                           f"<b style='color: #00E676;'>IP:</b> {conn['ip']}<br>"
                           f"<b style='color: #00E676;'>Date:</b> {conn['timestamp']}<br>"
                           f"<b style='color: #00E676;'>Duration:</b> {hours}:{minutes:02d}:{seconds:02d}"
                           f"</div>")
            
        self.history_text.setText(history_text)