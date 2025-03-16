from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QGroupBox, QCheckBox, QSpinBox, QLabel, QPushButton,
                             QLineEdit, QScrollArea, QMessageBox, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import json

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        self.loadSettings()
        self._apply_styles()
        
    def initUI(self):
        self.setWindowTitle('TorShield Ayarları')
        self.setFixedSize(500, 500)
        
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #404040;
                background: #1A1A1A;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #2D2D2D;
                color: #E0E0E0;
                padding: 10px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #404040;
            }
        """)
        
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        general_group = QGroupBox("Genel Ayarlar")
        general_box_layout = QVBoxLayout()
        
        self.auto_connect = QCheckBox("Başlangıçta otomatik bağlan")
        self.minimize_to_tray = QCheckBox("Kapatınca sistem tepsisine küçült")
        self.save_history = QCheckBox("Bağlantı geçmişini kaydet")
        self.show_speed = QCheckBox("Bağlantı hızını göster")
        
        for checkbox in [self.auto_connect, self.minimize_to_tray, 
                        self.save_history, self.show_speed]:
            general_box_layout.addWidget(checkbox)
            
        general_group.setLayout(general_box_layout)
        general_layout.addWidget(general_group)
        
        # Güvenlik Ayarları
        security_group = QGroupBox("Güvenlik Ayarları")
        security_layout = QVBoxLayout()
        
        auto_reconnect_layout = QHBoxLayout()
        auto_reconnect_label = QLabel("Otomatik yeniden bağlan (dakika):")
        self.auto_reconnect = QSpinBox()
        self.auto_reconnect.setRange(0, 60)
        self.auto_reconnect.setSpecialValueText("Kapalı")
        auto_reconnect_layout.addWidget(auto_reconnect_label)
        auto_reconnect_layout.addWidget(self.auto_reconnect)
        
        security_layout.addLayout(auto_reconnect_layout)
        security_group.setLayout(security_layout)
        general_layout.addWidget(security_group)
        
        general_layout.addStretch()
        general_tab.setLayout(general_layout)
        
        # Bağlantı Geçmişi Sekmesi
        history_tab = QWidget()
        history_layout = QVBoxLayout()
        
        # Geçmiş görüntüleme alanı
        history_group = QGroupBox("Son Bağlantılar")
        history_box_layout = QVBoxLayout()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2D2D2D;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        history_content = QWidget()
        history_content_layout = QVBoxLayout()
        
        self.history_text = QLabel()
        self.history_text.setWordWrap(True)
        self.history_text.setStyleSheet("color: #E0E0E0;")
        history_content_layout.addWidget(self.history_text)
        history_content_layout.addStretch()
        
        history_content.setLayout(history_content_layout)
        scroll_area.setWidget(history_content)
        history_box_layout.addWidget(scroll_area)
        
        # Geçmiş yönetim butonları
        history_buttons_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.update_history_text)
        clear_button = QPushButton("Geçmişi Temizle")
        clear_button.clicked.connect(self.clear_history)
        
        history_buttons_layout.addWidget(refresh_button)
        history_buttons_layout.addWidget(clear_button)
        
        history_box_layout.addLayout(history_buttons_layout)
        history_group.setLayout(history_box_layout)
        history_layout.addWidget(history_group)
        history_tab.setLayout(history_layout)
        
        # Sekmeleri ekle
        tab_widget.addTab(general_tab, "Genel")
        tab_widget.addTab(history_tab, "Geçmiş")
        layout.addWidget(tab_widget)
        
        # Alt butonlar
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Kaydet")
        save_button.clicked.connect(self.saveSettings)
        cancel_button = QPushButton("İptal")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A1A;
                color: #E0E0E0;
            }
            QGroupBox {
                color: #E0E0E0;
                border: 1px solid #404040;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: normal;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #E0E0E0;
            }
            QCheckBox {
                color: #E0E0E0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #404040;
                background: #2D2D2D;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #00E676;
                border: 2px solid #00E676;
            }
            QCheckBox::indicator:hover {
                border-color: #00E676;
            }
            QSpinBox {
                background: #2D2D2D;
                color: #E0E0E0;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
            QScrollArea {
                border: 1px solid #404040;
                border-radius: 5px;
            }
        """)
        
    def loadSettings(self):
        settings = self.parent.settings
        
        self.auto_connect.setChecked(settings.get('auto_connect', False))
        self.minimize_to_tray.setChecked(settings.get('minimize_to_tray', True))
        self.save_history.setChecked(settings.get('save_history', True))
        self.show_speed.setChecked(settings.get('show_speed', True))
        self.auto_reconnect.setValue(settings.get('auto_reconnect', 0))
        
        self.update_history_text()
        
    def saveSettings(self):
        settings = {
            'auto_connect': self.auto_connect.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked(),
            'save_history': self.save_history.isChecked(),
            'show_speed': self.show_speed.isChecked(),
            'auto_reconnect': self.auto_reconnect.value()
        }
        
        self.parent.settings = settings
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilirken hata oluştu: {str(e)}")
            
    def update_history_text(self):
        if not self.parent.connection_history:
            self.history_text.setText("Bağlantı geçmişi devre dışı.")
            return
            
        connections = self.parent.connection_history.get_last_connections()
        if not connections:
            self.history_text.setText("Henüz bağlantı geçmişi yok.")
            return
            
        history_text = ""
        for conn in reversed(connections):
            hours = conn['duration'] // 3600
            minutes = (conn['duration'] % 3600) // 60
            seconds = conn['duration'] % 60
            history_text += (f"<p style='margin: 10px 0;'>"
                           f"<b>IP:</b> {conn['ip']}<br>"
                           f"<b>Tarih:</b> {conn['timestamp']}<br>"
                           f"<b>Süre:</b> {hours}:{minutes:02d}:{seconds:02d}"
                           f"</p><hr>")
            
        self.history_text.setText(history_text)
        
    def clear_history(self):
        reply = QMessageBox.question(
            self, 'Geçmişi Temizle',
            "Tüm bağlantı geçmişini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.parent.connection_history:
                    self.parent.connection_history.clear_history()
                    self.update_history_text()
                    QMessageBox.information(self, "Başarılı", "Bağlantı geçmişi temizlendi!")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Geçmiş temizlenirken hata oluştu: {str(e)}")

    def show_connection_history(self):
        self.parent.show_connection_history()
        
    def save_settings(self):
        self.parent.settings.update({
            'auto_connect': self.auto_connect.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked(),
            'save_history': self.save_history.isChecked(),
            'show_speed': self.show_speed.isChecked(),
            'auto_reconnect': self.auto_reconnect.value()
        })
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.parent.settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilirken hata oluştu: {str(e)}")
            return
            
        self.accept() 