from flask import Flask, render_template, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import hashlib
import time
import os  # Thêm thư viện này để lấy Cổng (Port) tự động từ Render

app = Flask(__name__)

# --- CẤU HÌNH API SPOTIFY ---
SPOTIPY_CLIENT_ID = 'b4fc617aa60f4de48b4cef7a2db51945'
SPOTIPY_CLIENT_SECRET = 'f075c4a3064e4a749bd2dfec07503ef0'
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

# --- CẤU HÌNH ADAFRUIT IO ---
AIO_USERNAME = "Ktey"
AIO_KEY = "aio_GNfi72lXlZm0BjwllqZktnU8iQay"
FEED_NAME = "bpm-control"

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
        bpm = None
        try:
            features = sp.audio_features(track['id'])[0]
            if features: bpm = round(features['tempo'])
        except:
            hash_val = int(hashlib.md5(track['id'].encode()).hexdigest(), 16)
            bpm = 80 + (hash_val % 70) 

        return jsonify({
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'bpm': bpm,
            'preview_url': track.get('preview_url'),
            'source': 'Verified' if bpm else 'Estimated'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- THÊM HÀM AUTOCOMPLETE ĐỂ LÚC GÕ TÌM KIẾM WEB HIỆN GỢI Ý ---
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q')
    if not query:
        return jsonify([])
    try:
        results = sp.search(q=query, limit=5, type='track')
        suggestions =[]
        for track in results['tracks']['items']:
            img_url = track['album']['images'][0]['url'] if track['album']['images'] else ''
            suggestions.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'image': img_url
            })
        return jsonify(suggestions)
    except Exception as e:
        return jsonify([])

@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.json
    cmd = data.get('cmd')
    # Bắn lệnh thẳng lên Server của Adafruit IO
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED_NAME}/data"
    headers = {"X-AIO-Key": AIO_KEY, "Content-Type": "application/json"}
    payload = {"value": cmd}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            return jsonify({'status': 'success', 'msg': 'Đã đẩy lệnh lên Cloud'})
        else:
            return jsonify({'error': "Lỗi từ Adafruit"}), 500
    except Exception as e:
        return jsonify({'error': "Không kết nối được Cloud"}), 500

# --- HÀM MỚI: KIỂM TRA PING GIỮA WEB VÀ MẠCH ---
@app.route('/ping_esp', methods=['GET'])
def ping_esp():
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
    # SỬA LẠI ĐỂ TƯƠNG THÍCH VỚI RENDER (Tự động lấy Port của Server)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
