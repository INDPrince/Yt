from flask import Flask, request, jsonify import yt_dlp import random

app = Flask(name)

HEADERS_LIST = [ "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/90.0.4430.210 Mobile Safari/537.36", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/14.1.1 Safari/605.1.15" ]

def extract_video_info(url): headers = { 'User-Agent': random.choice(HEADERS_LIST), 'Accept-Language': 'en-US,en;q=0.9' } ydl_opts = { 'quiet': True, 'nocheckcertificate': True, 'source_address': '0.0.0.0', 'force_generic_extractor': False, 'proxy': None, 'noplaylist': True, 'ratelimit': 500000, 'simulate': True, 'geo_bypass': True, 'headers': headers, 'extract_flat': False, } try: with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=False) formats = [] for f in info.get("formats", []): if not f.get("url") or not f.get("ext"): continue size = f.get("filesize") or f.get("filesize_approx") size_mb = f"{round(size/1048576, 2)} MB" if size else "Unknown" formats.append({ "url": f["url"], "ext": f["ext"], "quality": f.get("format_note") or f.get("height", "Unknown"), "type": f.get("vcodec", "audio") if f.get("vcodec") != "none" else "Audio", "size": size_mb }) return { "title": info.get("title"), "duration": info.get("duration_string", ""), "uploader": info.get("uploader"), "thumbnail": info.get("thumbnail"), "formats": formats } except Exception as e: return {"error": str(e)}

@app.route("/api/youtube-info", methods=["POST"]) def youtube_info(): data = request.get_json() url = data.get("url") if not url: return jsonify({"error": "Missing URL"}), 400 result = extract_video_info(url) if "error" in result: return jsonify(result), 500 return jsonify(result)

@app.route("/") def index(): return open("index.html").read()

if name == 'main': app.run(debug=True)

