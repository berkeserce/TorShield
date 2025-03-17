import os
import ctypes
import winreg
import sys
import subprocess

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_tor_path():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tor_dir = os.path.join(base_dir, 'tor')
        
        if not os.path.exists(tor_dir):
            return None
            
        tor_exe = os.path.join(tor_dir, 'tor.exe')
        if os.path.exists(tor_exe):
            return tor_exe
            
        return None
    except:
        return None

def set_system_proxy(enable, host='127.0.0.1', port='9050'):
    try:
        INTERNET_SETTINGS = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
            0, winreg.KEY_ALL_ACCESS)

        def set_key(name, value):
            try:
                winreg.SetValueEx(INTERNET_SETTINGS, name, 0, winreg.REG_DWORD, value)
            except Exception as e:
                print(f"Registry değeri ayarlanırken hata: {name} - {e}")

        def set_key_string(name, value):
            try:
                winreg.SetValueEx(INTERNET_SETTINGS, name, 0, winreg.REG_SZ, value)
            except Exception as e:
                print(f"Registry değeri ayarlanırken hata: {name} - {e}")

        if enable:
            set_key('ProxyEnable', 1)
            set_key_string('ProxyServer', f'socks={host}:{port}')
        else:
            set_key('ProxyEnable', 0)
            set_key_string('ProxyServer', '')

        try:
            subprocess.run(['ipconfig', '/flushdns'], capture_output=True)
            subprocess.run(['ipconfig', '/registerdns'], capture_output=True)
            subprocess.run(['ipconfig', '/release'], capture_output=True)
            subprocess.run(['ipconfig', '/renew'], capture_output=True)
        except Exception as e:
            print(f"IP yapılandırması yenilenirken hata: {e}")

        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        try:
            ctypes.windll.Wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        except Exception as e:
            print(f"Internet seçenekleri yenilenirken hata: {e}")

        return True
    except Exception as e:
        print(f"Sistem proxy ayarları değiştirilirken hata oluştu: {e}")
        return False 