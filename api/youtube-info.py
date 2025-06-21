from flask import Flask, request, jsonify
import yt_dlp
import os
import json
import requests
import re
from urllib.parse import urlparse, parse_qs
import time
import random

app = Flask(__name__)

# Multiple User Agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
]

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

def get_video_info_alternative(video_id):
    """Alternative method using direct API calls"""
    try:
        # Method 1: Try YouTube oEmbed API
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(oembed_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract duration from thumbnail URL pattern or other methods
            thumbnail_url = data.get('thumbnail_url', '')
            
            return {
                'title': data.get('title', 'Unknown Title'),
                'duration': 'Unknown',  # oEmbed doesn't provide duration
                'thumbnail': thumbnail_url,
                'uploader': data.get('author_name', 'Unknown'),
                'view_count': 0,
                'formats': generate_standard_formats(video_id)
            }
            
    except Exception as e:
        print(f"Alternative method failed: {e}")
        return None

def generate_standard_formats(video_id):
    """Generate standard YouTube format URLs"""
    base_url = f"https://www.youtube.com/watch?v={video_id}"
    
    formats = [
        {
            'quality': '1080p',
            'type': 'MP4 Video',
            'size': '~50-100 MB',
            'url': base_url,
            'ext': 'mp4'
        },
        {
            'quality': '720p',
            'type': 'MP4 Video',
            'size': '~30-60 MB',
            'url': base_url,
            'ext': 'mp4'
        },
        {
            'quality': '480p',
            'type': 'MP4 Video',
            'size': '~20-40 MB',
            'url': base_url,
            'ext': 'mp4'
        },
        {
            'quality': 'Audio Only',
            'type': 'MP3 Audio',
            'size': '~3-8 MB',
            'url': base_url,
            'ext': 'mp3'
        }
    ]
    
    return formats

def get_video_info_yt_dlp(url):
    """Get video information using yt-dlp with enhanced options"""
    try:
        # Random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': random.choice(USER_AGENTS),
            'referer': 'https://www.youtube.com/',
            'headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash'],
                    'player_skip': ['js'],
                    'player_client': ['android', 'web'],
                }
            },
            'format': 'best[height<=1080]',
            'socket_timeout': 60,
            'retries': 3,
            'fragment_retries': 3,
            'ignoreerrors': True,
            'no_check_certificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
                
            # Extract relevant information
            video_data = {
                'title': info.get('title', 'Unknown Title'),
                'duration': format_duration(info.get('duration', 0)),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'formats': []
            }
            
            # Process formats
            formats = info.get('formats', [])
            processed_formats = []
            
            # Get video formats
            video_formats = {}
            audio_formats = {}
            
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    # Video with audio
                    height = fmt.get('height')
                    if height and height >= 240:
                        quality = f"{height}p"
                        if quality not in video_formats or fmt.get('filesize', 0) > video_formats[quality].get('filesize', 0):
                            video_formats[quality] = {
                                'quality': quality,
                                'type': 'MP4 Video',
                                'url': fmt.get('url', ''),
                                'filesize': fmt.get('filesize', 0),
                                'ext': fmt.get('ext', 'mp4')
                            }
                
                elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    # Audio only
                    abr = fmt.get('abr', 0)
                    if abr > 0:
                        quality = f"{int(abr)}kbps"
                        if 'audio' not in audio_formats or abr > audio_formats['audio'].get('abr', 0):
                            audio_formats['audio'] = {
                                'quality': 'Audio Only',
                                'type': 'MP3 Audio',
                                'url': fmt.get('url', ''),
                                'filesize': fmt.get('filesize', 0),
                                'abr': abr,
                                'ext': fmt.get('ext', 'mp3')
                            }
            
            # Add processed formats
            for quality in ['1080p', '720p', '480p', '360p', '240p']:
                if quality in video_formats:
                    fmt = video_formats[quality]
                    processed_formats.append({
                        'quality': fmt['quality'],
                        'type': fmt['type'],
                        'size': format_filesize(fmt['filesize']),
                        'url': fmt['url'],
                        'ext': fmt['ext']
                    })
            
            # Add audio format
            if 'audio' in audio_formats:
                fmt = audio_formats['audio']
                processed_formats.append({
                    'quality': fmt['quality'],
                    'type': fmt['type'],
                    'size': format_filesize(fmt['filesize']),
                    'url': fmt['url'],
                    'ext': fmt['ext']
                })
            
            video_data['formats'] = processed_formats
            return video_data
            
    except Exception as e:
        print(f"yt-dlp extraction failed: {str(e)}")
        return None

def format_duration(seconds):
    """Format duration from seconds to MM:SS or HH:MM:SS"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_filesize(size):
    """Format file size to human readable format"""
    if not size or size == 0:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"~{size:.1f} {unit}"
        size /= 1024
    return f"~{size:.1f} TB"

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
        
        # Try multiple methods
        video_info = None
        
        # Method 1: Try yt-dlp
        try:
            video_info = get_video_info_yt_dlp(url)
        except Exception as e:
            print(f"yt-dlp failed: {e}")
            video_info = None
        
        # Method 2: Try alternative method if yt-dlp fails
        if not video_info:
            try:
                video_info = get_video_info_alternative(video_id)
            except Exception as e:
                print(f"Alternative method failed: {e}")
                video_info = None
        
        # Method 3: Return basic info if all methods fail
        if not video_info:
            video_info = {
                'title': 'Unable to fetch video details',
                'duration': 'Unknown',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                'uploader': 'Unknown',
                'view_count': 0,
                'formats': [
                    {
                        'quality': 'Download',
                        'type': 'Redirect to YouTube',
                        'size': 'Unknown',
                        'url': url,
                        'ext': 'redirect'
                    }
                ]
            }
        
        return jsonify(video_info)
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        download_url = data['url']
        quality = data.get('quality', 'best')
        
        # For Vercel deployment, return download URL
        return jsonify({
            'message': 'Download link ready',
            'download_url': download_url,
            'quality': quality,
            'instructions': 'Click the link to start download'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True, port=5000)
