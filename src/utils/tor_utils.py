import socket
import subprocess
import os
import time
from stem.control import Controller
import psutil

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except:
            return True
            
def create_tor_config(tor_path, data_dir, exit_country=None):
    config_path = os.path.join(data_dir, 'torrc')
    
    config = f"""DataDirectory {data_dir}
SocksPort 9050
ControlPort 9051
CookieAuthentication 1
"""    
    # Ülke bazlı çıkış noktası ayarı
    if exit_country and exit_country.strip():
        config += f"\nExitNodes {{{exit_country}}}"
        config += "\nStrictNodes 0"
        config += "\nGeoIPFile " + os.path.join(os.path.dirname(os.path.dirname(tor_path)), 'data', 'geoip')
        config += "\nGeoIPv6File " + os.path.join(os.path.dirname(os.path.dirname(tor_path)), 'data', 'geoip6')
        
    # Add connection optimization settings
    config += "\nCircuitBuildTimeout 60"
    config += "\nLearnCircuitBuildTimeout 1"
    config += "\nNewCircuitPeriod 15"
    config += "\nMaxCircuitDirtiness 600"
    
    try:
        with open(config_path, 'w') as f:
            f.write(config)
        return config_path
    except Exception as e:
        print(f"Tor yapılandırma dosyası oluşturulurken hata oluştu: {e}")
        return None
        
def launch_tor(tor_path, config_path, status_callback=None):
    try:
        if status_callback:
            status_callback("Tor başlatılıyor...")
            
        process = subprocess.Popen(
            [tor_path, '-f', config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        time.sleep(3)
        
        if process.poll() is not None:
            if status_callback:
                status_callback("Tor başlatılamadı!")
            return None
            
        if status_callback:
            status_callback("Tor başlatıldı!")
            
        return process
    except Exception as e:
        if status_callback:
            status_callback(f"Tor başlatılırken hata oluştu: {e}")
        return None
        
def create_controller():
    controller = Controller.from_port(port=9051, timeout=5)
    controller.authenticate()
    return controller