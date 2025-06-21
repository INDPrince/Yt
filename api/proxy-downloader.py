from flask import Flask, request, jsonify
import requests
import json
import re
import time
from urllib.parse import urlparse, parse_qs
import random

app = Flask(__name__)

# Free proxy servers (update regularly)
PROXY_SERVERS = [
    'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
    # Add more proxy sources as needed
]

# YouTube API alternatives
YOUTUBE_APIS = [
    'https://youtube-dl-web.herokuapp.com/api/info',
    'https://ytdl-org.github.io/youtube-dl/supportedsites.html',
    # Add more alternative APIs
]

def get_working_proxies():
    """Get list of working proxies"""
    proxies = []
    try:
        # This is a simplified example - in production, use a proper proxy service
        proxies = [
            {'http': 'http://proxy1.com:8080'},
            {'http': 'http://proxy2.com:8080'},
            # Add actual working proxies
        ]
    except:
        pass
    return proxies

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    parsed_url = urlparse(url)
    
    if parsed_url.hostname in ['youtu.be']:
        return parsed_url.path[1:]
    elif parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        elif parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    
    return None

def get_video_info_with_proxy(video_id, max_retries=3):
    """Get video info using proxy servers"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Method 1: Direct YouTube oEmbed (often works)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', 'Unknown Title'),
                'duration': 'Unknown',
                'thumbnail': data.get('thumbnail_url', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'),
                'uploader': data.get('author_name', 'Unknown'),
                'view_count': 0,
                'formats': generate_download_formats(video_id)
            }
    except:
        pass
    
    # Method 2: Try with different proxy servers
    proxies = get_working_proxies()
    
    for proxy in proxies:
        try:
            response = requests.get(
                oembed_url, 
                headers=headers, 
                proxies=proxy, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', 'Unknown Title'),
                    'duration': 'Unknown',
                    'thumbnail': data.get('thumbnail_url', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'),
                    'uploader': data.get('author_name', 'Unknown'),
                    'view_count': 0,
                    'formats': generate_download_formats(video_id)
                }
        except:
            continue
    
    # Method 3: Fallback with basic info
    return {
        'title': 'Video Information Available',
        'duration': 'Unknown',
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
        'uploader': 'YouTube',
        'view_count': 0,
        'formats': generate_download_formats(video_id)
    }

def generate_download_formats(video_id):
    """Generate download options using external services"""
    
    # Popular YouTube downloader services
    download_services = [
        {
            'name': 'Y2mate',
            'url': f'https://www.y2mate.com/youtube/{video_id}',
            'quality': '1080p',
            'type': 'External Service'
        },
        {
            'name': 'SaveFrom',
            'url': f'https://en.savefrom.net/1-youtube-video-downloader-{video_id}',
            'quality': '720p', 
            'type': 'External Service'
        },
        {
            'name': 'KeepVid',
            'url': f'https://keepvid.ch/?url=https://www.youtube.com/watch?v={video_id}',
            'quality': '480p',
            'type': 'External Service'
        },
        {
            'name': 'YouTube Direct',
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'quality': 'Watch Online',
            'type': 'YouTube Direct'
        }
    ]
    
    formats = []
    for service in download_services:
        formats.append({
            'quality': service['quality'],
            'type': service['type'],
            'size': 'Click to check',
            'url': service['url'],
            'ext': 'redirect',
            'service': service['name']
        })
    
    return formats

@app.route('/api/youtube-info', methods=['POST'])
def youtube_info():
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url'].strip()
        
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Validate YouTube URL
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Get video information
        video_info = get_video_info_with_proxy(video_id)
        
        return jsonify(video_info)
        
    except Exception as e:
        return jsonify({
            'error': 'Unable to fetch video info at the moment',
            'message': 'Please try again later or use direct YouTube link',
            'youtube_url': data.get('url', '') if 'data' in locals() else ''
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'YouTube Info API is running',
        'timestamp': time.time()
    })

# For local development
if __name__ == '__main__':
    app.run(debug=True, port=5000)
