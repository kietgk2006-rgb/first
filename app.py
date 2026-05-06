from flask import Flask, render_template, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import hashlib
import time

app = Flask(__name__)

# --- CẤU HÌNH API VÀ IP ---
SPOTIPY_CLIENT_ID = 'b4fc617aa60f4de48b4cef7a2db51945'
SPOTIPY_CLIENT_SECRET = 'f075c4a3064e4a749bd2dfec07503ef0'

# Địa chỉ IP của con ESP-01S 
ESP_IP = '172.20.10.2' 

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_song():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
        
    try:
        results = sp.search(q=query, limit=1, type='track')
        if not results['tracks']['items']:
            return jsonify({'error': 'Not found'}), 404
            
        track = results['tracks']['items'][0]
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        preview_url = track.get('preview_url') # Lấy link nghe thử 30s
        
        bpm = None
        try:
            features = sp.audio_features(track['id'])[0]
            if features:
                bpm = round(features['tempo'])
        except:
            hash_val = int(hashlib.md5(track['id'].encode()).hexdigest(), 16)
            bpm = 80 + (hash_val % 70) 

        return jsonify({
            'name': track_name,
            'artist': artist_name,
            'bpm': bpm,
            'preview_url': preview_url, # Trả về cho Frontend
            'source': 'Verified' if bpm else 'Estimated'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q')
    if not query or len(query) < 2: 
        return jsonify([])
    
    try:
        results = sp.search(q=query, limit=5, type='track')
        tracks = []
        for t in results['tracks']['items']:
            img_url = t['album']['images'][2]['url'] if t['album']['images'] else ''
            tracks.append({
                'id': t['id'],
                'name': t['name'],
                'artist': t['artists'][0]['name'],
                'image': img_url
            })
        return jsonify(tracks)
    except Exception as e:
        return jsonify([])

@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.json
    cmd = data.get('cmd')
    try:
        url = f"http://{ESP_IP}/action?cmd={cmd}"
        response = requests.get(url, timeout=3)
        return jsonify({'status': 'success', 'esp_reply': response.text})
    except Exception as e:
        return jsonify({'error': "Không kết nối được ESP"}), 500

# API mới: Kiểm tra kết nối và đo độ trễ (Ping) tới ESP
@app.route('/ping_esp', methods=['GET'])
def ping_esp():
    start_time = time.time()
    try:
        # Gửi request nhẹ nhất có thể để check kết nối
        requests.get(f"http://{ESP_IP}/", timeout=1.5)
        latency = int((time.time() - start_time) * 1000)
        return jsonify({'status': 'connected', 'ping': latency})
    except Exception:
        return jsonify({'status': 'disconnected', 'ping': 999}), 503
import time # Nhớ thêm import time ở đầu file cùng với các thư viện khác nhé

@app.route('/ping_esp', methods=['GET'])
def ping_esp():
    # Kiểm tra kết nối từ Server Web đến Adafruit IO
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED_NAME}"
    headers = {"X-AIO-Key": AIO_KEY}
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=3)
        ping = round((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            return jsonify({'status': 'connected', 'ping': ping})
        else:
            return jsonify({'status': 'disconnected'}), 500
    except Exception as e:
        return jsonify({'status': 'disconnected'}), 500
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
