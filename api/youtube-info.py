from flask import Flask, request, jsonify
import yt_dlp
import os
import json
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

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

def get_video_info(url):
    """Get video information using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
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
        raise Exception(f"Error extracting video info: {str(e)}")

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
        
        # Get video information
        video_info = get_video_info(url)
        
        return jsonify(video_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        download_url = data['url']
        quality = data.get('quality', 'best')
        
        # In a real implementation, you would handle the download here
        # For Vercel, direct file downloads are limited due to serverless constraints
        # You might want to return the direct URL or use a different approach
        
        return jsonify({
            'message': 'Download initiated',
            'download_url': download_url,
            'quality': quality
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True)
