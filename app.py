import os
import requests
import datetime
import re
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# --- কনফিগারেশন ---
app.secret_key = os.environ.get("SECRET_KEY", "moviebox_2026_super_secret")
MONGO_URI = os.environ.get("MONGO_URI")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_NAME")

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['moviebox_db']
movies_collection = db['movies']

# এডমিন ক্রেডেনশিয়াল
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "12345")

# --- হেল্পার ফাংশন: ইউটিউব আইডি বের করা ---
def get_yt_id(url):
    if not url: return ""
    if "v=" in url: # m.youtube.com/watch?v=ID
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be" in url: # youtu.be/ID
        return url.split("/")[-1].split("?")[0]
    elif "embed" in url: # youtube.com/embed/ID
        return url.split("/")[-1]
    return ""

app.jinja_env.globals.update(get_yt_id=get_yt_id)

# --- ডিজাইন (CSS) ---
CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    :root { --main: #e50914; --bg: #0f0f0f; --card: #181818; --text: #fff; --gray: #aaa; }
    * { box-sizing: border-box; margin: 0; padding: 0; outline: none; -webkit-tap-highlight-color: transparent; }
    body { font-family: Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); padding-bottom: 30px; }
    a { text-decoration: none; color: inherit; }

    /* Navbar */
    .navbar { background: rgba(15, 15, 15, 0.95); padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; border-bottom: 1px solid #333; }
    .logo { color: var(--main); font-size: 20px; font-weight: 800; letter-spacing: -1px; }
    .btn { background: var(--main); color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-weight: 600; font-size: 13px; display: inline-block; }
    
    /* Layout */
    .container { max-width: 1000px; margin: auto; padding: 15px; }
    .search-box { margin: 10px 0 20px; display: flex; justify-content: center; }
    .search-input { width: 100%; max-width: 500px; padding: 10px 20px; border-radius: 50px; border: 1px solid #333; background: #121212; color: white; font-size: 16px; }

    /* Movie Grid */
    .movie-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    @media (min-width: 768px) { .movie-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; } }

    .card { background: var(--card); border-radius: 8px; overflow: hidden; position: relative; transition: 0.2s; }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
    .card-info { padding: 10px; }
    .card-title { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
    .card-meta { font-size: 12px; color: var(--gray); }

    /* Watch Page */
    .watch-video-container { width: 100%; position: sticky; top: 0; z-index: 900; background: #000; aspect-ratio: 16/9; }
    .iframe-container { position: relative; width: 100%; height: 100%; }
    .iframe-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
    
    .video-info { padding: 15px; border-bottom: 1px solid #333; }
    .video-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; line-height: 1.3; }
    .video-meta { font-size: 13px; color: var(--gray); display: flex; justify-content: space-between; align-items: center; }
    .action-bar { display: flex; gap: 15px; margin-top: 15px; }
    .action-btn { background: #222; color: white; border: none; padding: 8px 15px; border-radius: 18px; display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; }
    .action-btn.liked { color: var(--main); background: rgba(229, 9, 20, 0.1); }

    /* Admin Styles */
    .admin-box { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #333; }
    input[type="text"], select { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid #444; background: #222; color: white; }
    .upload-btn-widget { background: #222; border: 2px dashed #444; color: white; width: 100%; padding: 20px; text-align: center; cursor: pointer; border-radius: 5px; margin: 10px 0; }
    
    /* Plyr */
    .plyr { width: 100%; height: 100%; }
</style>
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
<script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
<script src="https://upload-widget.cloudinary.com/global/all.js" type="text/javascript"></script>
"""

# --- হোমপেজ ---
HOME_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">PLAYBOX</a>
    <a href="/admin" class="btn">ADMIN</a>
</nav>

<div class="container">
    <div class="search-box">
        <form action="/" method="GET" style="width:100%;">
            <input type="text" name="q" class="search-input" placeholder="Search movies..." value="{{ request.args.get('q', '') }}">
        </form>
    </div>

    <div class="movie-grid">
        {% if movies|length == 0 %}
            <p style="grid-column: 1/-1; text-align:center; color:#777; margin-top:20px;">No content found.</p>
        {% endif %}

        {% for m in movies %}
        <a href="/watch/{{ m._id }}" class="card">
            <img src="{{ m.poster }}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
            <div class="card-info">
                <div class="card-title">{{ m.title }}</div>
                <div class="card-meta">{{ m.year }} • {{ m.type|upper }}</div>
            </div>
        </a>
        {% endfor %}
    </div>
</div>
"""

# --- ওয়াচ পেজ (Final Smart Player) ---
WATCH_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">PLAYBOX</a>
    <a href="/" class="btn" style="background:#333;">BACK</a>
</nav>

<div class="watch-video-container">
    <!-- ১. যদি ইউটিউব ভিডিও হয় -->
    {% if 'youtu' in movie.video_url %}
        <div class="plyr__video-embed" id="player">
            <iframe
                src="https://www.youtube.com/embed/{{ get_yt_id(movie.video_url) }}?origin=https://plyr.io&amp;iv_load_policy=3&amp;modestbranding=1&amp;playsinline=1&amp;showinfo=0&amp;rel=0&amp;enablejsapi=1"
                allowfullscreen allowtransparency allow="autoplay">
            </iframe>
        </div>
    
    <!-- ২. যদি গুগল ড্রাইভ হয় -->
    {% elif 'drive.google.com' in movie.video_url %}
        <div class="iframe-container">
            <iframe src="{{ movie.video_url }}" allow="autoplay"></iframe>
        </div>

    <!-- ৩. যদি ক্লাউডিনারি বা ডাইরেক্ট ভিডিও হয় -->
    {% else %}
        <video id="player" playsinline controls autoplay>
            <source src="{{ movie.video_url }}" type="video/mp4" />
        </video>
    {% endif %}
</div>

<div class="container" style="padding-top:0;">
    <div class="video-info">
        <div class="video-title">{{ movie.title }}</div>
        <div class="video-meta">
            <span>{{ movie.year }} • {{ movie.type|upper }}</span>
            <span id="likeCount">{{ movie.likes|default(0) }} Likes</span>
        </div>
        
        <div class="action-bar">
            <button class="action-btn" onclick="toggleLike('{{ movie._id }}')">
                <span>👍</span> Like
            </button>
            <button class="action-btn" onclick="navigator.clipboard.writeText(window.location.href); alert('Link Copied!');">
                <span>↗️</span> Share
            </button>
        </div>
    </div>

    <div class="comments-section">
        <h4 style="margin-bottom:15px;">Comments</h4>
        <form action="/add_comment/{{ movie._id }}" method="POST" class="comment-form">
            <input type="text" name="text" class="comment-input" placeholder="Add a comment..." required autocomplete="off">
            <button class="btn" style="border-radius:50%; width:35px; height:35px; padding:0;">➤</button>
        </form>

        <div class="comment-list">
            {% for c in movie.comments|reverse %}
            <div class="comment-item">
                <div class="avatar">{{ c.user[0]|upper }}</div>
                <div class="comment-content">
                    <b>{{ c.user }}</b>
                    <p>{{ c.text }}</p>
                </div>
            </div>
            {% else %}
            <p style="color:#555; font-size:12px;">No comments yet.</p>
            {% endfor %}
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', () => {
        // Plyr শুধু ইউটিউব আর MP4 এর জন্য কাজ করবে
        if(document.getElementById('player')) {
            const player = new Plyr('#player', {
                controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'fullscreen'],
                youtube: { noCookie: true, rel: 0, showinfo: 0, iv_load_policy: 3, modestbranding: 1 }
            });
        }
    });

    function toggleLike(id) {
        fetch(`/like/${id}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                document.getElementById('likeCount').innerText = data.likes + ' Likes';
                document.querySelector('.action-btn').classList.add('liked');
            });
    }
</script>
"""

# --- এডমিন প্যানেল (Final Upload) ---
ADMIN_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">ADMIN</a>
    <a href="/logout" class="btn" style="background:#333;">LOGOUT</a>
</nav>
<div class="container">
    
    <div class="admin-box">
        <h3 style="margin-bottom:10px; color:var(--main);">1. Auto Fill (TMDB)</h3>
        <div style="display:flex; gap:8px;">
            <input type="text" id="tmdbQuery" placeholder="Movie Name...">
            <button onclick="searchTMDB()" class="btn">GO</button>
        </div>
        <div id="searchResults" style="display:flex; overflow-x:auto; gap:10px; margin-top:15px;"></div>
    </div>

    <div class="admin-box">
        <h3 style="margin-bottom:10px; color:var(--main);">2. Add Content</h3>
        <form id="uploadForm" action="/add_content" method="POST">
            <input type="text" id="fTitle" name="title" placeholder="Title" required>
            <div style="display:flex; gap:10px;">
                <input type="text" id="fYear" name="year" placeholder="Year" style="flex:1;">
                <select name="type" id="fType" style="flex:1; margin:8px 0;">
                    <option value="movie">Movie</option>
                    <option value="tv">TV Show</option>
                </select>
            </div>
            <input type="text" id="fPoster" name="poster" placeholder="Poster Link" required>
            <input type="text" id="fBack" name="backdrop" placeholder="Backdrop Link">

            <!-- Link Option -->
            <label style="color:var(--main); font-weight:bold; margin-top:10px; display:block;">Option A: Paste Link (YouTube Unlisted / Drive / URL)</label>
            <input type="text" id="fVideoUrl" name="video_url" placeholder="https://youtu.be/..." oninput="checkInput()">

            <div style="text-align:center; margin:15px 0; color:#777;">--- OR ---</div>

            <!-- Upload Option -->
            <div class="upload-btn-widget" id="uploadWidgetBtn" onclick="openWidget()">
                📤 Option B: Upload Video (Cloudinary)
            </div>
            <p id="uploadStatus" style="text-align:center; font-size:12px; color:var(--main); display:none;">Video Uploaded! Link Auto-filled.</p>
            
            <button type="submit" id="saveBtn" class="btn" style="width:100%; margin-top:10px;">SAVE CONTENT</button>
        </form>
    </div>

    <div class="admin-box">
        <h3 style="margin-bottom:10px;">Manage Content</h3>
        <div class="movie-grid">
            {% for m in movies %}
            <div class="card" style="cursor:default;">
                <img src="{{ m.poster }}" style="height:100px;">
                <div class="card-info">
                    <div class="card-title">{{ m.title }}</div>
                    <a href="/delete/{{ m._id }}" onclick="return confirm('Delete?')" class="btn" style="background:#d32f2f; font-size:10px; padding:5px 10px;">DELETE</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<script>
    async function searchTMDB() {
        const q = document.getElementById('tmdbQuery').value;
        const res = await fetch(`/api/tmdb?q=${q}`);
        const data = await res.json();
        const div = document.getElementById('searchResults');
        div.innerHTML = '';
        data.results.slice(0, 10).forEach(item => {
            const d = document.createElement('div');
            d.innerHTML = `<img src="https://image.tmdb.org/t/p/w200${item.poster_path}" style="width:80px; border-radius:4px;">`;
            d.onclick = () => {
                document.getElementById('fTitle').value = item.title || item.name;
                document.getElementById('fYear').value = (item.release_date || item.first_air_date || '').split('-')[0];
                document.getElementById('fPoster').value = `https://image.tmdb.org/t/p/w500${item.poster_path}`;
                document.getElementById('fBack').value = `https://image.tmdb.org/t/p/original${item.backdrop_path}`;
                div.innerHTML = '';
            };
            div.appendChild(d);
        });
    }

    // --- CLOUDINARY WIDGET ---
    var myWidget = cloudinary.createUploadWidget({
        cloudName: '{{ cloud_name }}', 
        uploadPreset: 'YOUR_PRESET_NAME', // <--- আপনার প্রিসেট নাম এখানে বসাবেন
        sources: ['local', 'url'],
        resourceType: 'video',
        clientAllowedFormats: ['mp4', 'mkv', 'mov'],
        maxFileSize: 2000000000 // 2GB
    }, (error, result) => { 
        if (!error && result && result.event === "success") { 
            document.getElementById('fVideoUrl').value = result.info.secure_url;
            document.getElementById('uploadWidgetBtn').style.display = 'none';
            document.getElementById('uploadStatus').style.display = 'block';
        }
    });

    function openWidget() { myWidget.open(); }
    function checkInput() { 
        if(document.getElementById('fVideoUrl').value.length > 0) {
            document.getElementById('uploadWidgetBtn').style.opacity = '0.5';
            document.getElementById('uploadWidgetBtn').style.pointerEvents = 'none';
        } else {
            document.getElementById('uploadWidgetBtn').style.opacity = '1';
            document.getElementById('uploadWidgetBtn').style.pointerEvents = 'all';
        }
    }
</script>
"""

# --- রাউটস ---

@app.route('/')
def index():
    query = request.args.get('q')
    if query:
        movies = list(movies_collection.find({"title": {"$regex": query, "$options": "i"}}))
    else:
        movies = list(movies_collection.find().sort('_id', -1))
    return render_template_string(HOME_HTML, movies=movies)

@app.route('/watch/<movie_id>')
def watch(movie_id):
    try:
        movie = movies_collection.find_one({'_id': ObjectId(movie_id)})
        if not movie: return redirect('/')
        return render_template_string(WATCH_HTML, movie=movie)
    except:
        return redirect('/')

@app.route('/like/<movie_id>', methods=['POST'])
def add_like(movie_id):
    movies_collection.update_one({'_id': ObjectId(movie_id)}, {'$inc': {'likes': 1}})
    movie = movies_collection.find_one({'_id': ObjectId(movie_id)})
    return jsonify({'likes': movie.get('likes', 0)})

@app.route('/add_comment/<movie_id>', methods=['POST'])
def add_comment(movie_id):
    text = request.form.get('text')
    if text:
        comment = {'user': 'Guest', 'text': text, 'time': datetime.datetime.now()}
        movies_collection.update_one({'_id': ObjectId(movie_id)}, {'$push': {'comments': comment}})
    return redirect(url_for('watch', movie_id=movie_id))

@app.route('/api/tmdb')
def tmdb_api():
    q = request.args.get('q')
    if not TMDB_API_KEY: return jsonify({"results": []})
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={q}"
    return jsonify(requests.get(url).json())

@app.route('/admin')
def admin():
    if session.get('auth'): 
        movies = list(movies_collection.find().sort('_id', -1))
        # এখানে cloud_name পাঠানো হচ্ছে যাতে JS এ ব্যবহার করা যায়
        return render_template_string(ADMIN_HTML, movies=movies, cloud_name=os.environ.get("CLOUDINARY_NAME"))
    return render_template_string(CSS + """<div style="padding:50px; text-align:center;"><h2 style="color:var(--main);">LOGIN</h2><form action="/login" method="POST"><input type="text" name="u" placeholder="User"><input type="password" name="p" placeholder="Pass"><button class="btn" style="width:100%; margin-top:10px;">LOGIN</button></form></div>""")

@app.route('/login', methods=['POST'])
def login():
    if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
        session['auth'] = True
        return redirect('/admin')
    return "Fail"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add_content', methods=['POST'])
def add_content():
    if not session.get('auth'): return "Unauthorized", 401
    
    video_url = request.form.get('video_url')
    
    # গুগল ড্রাইভ লিংক ফিক্সার
    if video_url and "drive.google.com" in video_url:
        try:
            if "/d/" in video_url:
                file_id = video_url.split("/d/")[1].split("/")[0]
            elif "id=" in video_url:
                file_id = video_url.split("id=")[1].split("&")[0]
            if file_id:
                video_url = f"https://drive.google.com/file/d/{file_id}/preview"
        except:
            pass

    if video_url:
        movies_collection.insert_one({
            "title": request.form.get('title'),
            "year": request.form.get('year'),
            "poster": request.form.get('poster'),
            "backdrop": request.form.get('backdrop'),
            "type": request.form.get('type'),
            "video_url": video_url, 
            "likes": 0,
            "comments": []
        })
        return redirect('/admin')
    return "Error: No content", 400

@app.route('/delete/<movie_id>')
def delete_movie(movie_id):
    if not session.get('auth'): return redirect('/')
    try: movies_collection.delete_one({'_id': ObjectId(movie_id)})
    except: pass
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
