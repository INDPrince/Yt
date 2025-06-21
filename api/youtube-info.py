from flask import Flask, request, jsonify
import yt_dlp
import time
import random
import requests
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# User agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['youtu.be']:
        return parsed_url.path[1:]
    elif parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    return None

def format_duration(seconds):
    if not seconds:
        return "Unknown"
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

def format_filesize(size):
    if not size:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"~{size:.1f} {unit}"
        size /= 1024
    return f"~{size:.1f} TB"

def get_video_info_yt_dlp(url):
    try:
        time.sleep(random.uniform(1, 2))
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': random.choice(USER_AGENTS),
            'referer': 'https://www.youtube.com/',
            'format': 'best[height<=1080]',
            'socket_timeout': 30,
            'retries': 2,
            'ignoreerrors': True,
            'no_check_certificate': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None

            video_data = {
                'title': info.get('title', 'Unknown Title'),
                'duration': format_duration(info.get('duration', 0)),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'formats': []
            }

            formats = info.get('formats', [])
            processed = []

            for f in formats:
                if f.get('url') and f.get('filesize') and f.get('vcodec') != 'none':
                    height = f.get('height')
                    if height:
                        processed.append({
                            'quality': f"{height}p",
                            'type': 'MP4 Video',
                            'size': format_filesize(f.get('filesize')),
                            'url': f.get('url'),
                            'ext': f.get('ext', 'mp4')
                        })
                elif f.get('url') and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    processed.append({
                        'quality': 'Audio Only',
                        'type': 'MP3 Audio',
                        'size': format_filesize(f.get('filesize')),
                        'url': f.get('url'),
                        'ext': f.get('ext', 'mp3')
                    })

            video_data['formats'] = processed
            return video_data

    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None

@app.route('/api/youtube-info', methods=['POST'])
def youtube_info():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400

        url = data['url'].strip()
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        info = get_video_info_yt_dlp(url)
        if info and info['formats']:
            return jsonify(info)

        return jsonify({'error': 'Could not fetch valid download links.'}), 500

    except Exception as e:
        return jsonify({'error': f'Server error: {e}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': time.time()})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
