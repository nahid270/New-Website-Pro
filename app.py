import os
import requests
import tempfile
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

# Cloudinary কনফিগারেশন
cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_NAME"), 
  api_key = "885392694246946", 
  api_secret = "a7y3o299JJqLfxmj9rLMK3hNbcg" 
)

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['moviebox_db']
movies_collection = db['movies']

# এডমিন ক্রেডেনশিয়াল
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "12345")

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
    .card:active { transform: scale(0.98); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
    .card-info { padding: 10px; }
    .card-title { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
    .card-meta { font-size: 12px; color: var(--gray); }

    /* Watch Page */
    .watch-video-container { width: 100%; position: sticky; top: 0; z-index: 900; background: #000; }
    .video-info { padding: 15px; border-bottom: 1px solid #333; }
    .video-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; line-height: 1.3; }
    .video-meta { font-size: 13px; color: var(--gray); display: flex; justify-content: space-between; align-items: center; }
    
    .action-bar { display: flex; gap: 15px; margin-top: 15px; }
    .action-btn { background: #222; color: white; border: none; padding: 8px 15px; border-radius: 18px; display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; }
    .action-btn.liked { color: var(--main); background: rgba(229, 9, 20, 0.1); }
    
    .comments-section { padding: 15px; }
    .comment-form { display: flex; gap: 10px; margin-bottom: 20px; }
    .comment-input { flex: 1; background: transparent; border: none; border-bottom: 1px solid #444; color: white; padding: 8px; }
    .comment-list { display: flex; flex-direction: column; gap: 15px; }
    .comment-item { display: flex; gap: 10px; }
    .avatar { width: 35px; height: 35px; background: #333; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #888; font-size: 12px; }
    .comment-content b { font-size: 13px; display: block; color: #ddd; }
    .comment-content p { font-size: 13px; color: var(--gray); margin-top: 2px; }

    /* Admin Styles */
    .admin-box { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #333; }
    input[type="text"], select, input[type="file"] { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid #444; background: #222; color: white; }
    
    .or-divider { text-align: center; margin: 15px 0; position: relative; }
    .or-divider span { background: #1a1a1a; padding: 0 10px; color: #777; font-size: 12px; position: relative; z-index: 1; }
    .or-divider::before { content: ''; position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background: #333; z-index: 0; }

    /* Plyr */
    .plyr { width: 100%; aspect-ratio: 16/9; }
</style>
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
<script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
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

# --- ওয়াচ পেজ ---
WATCH_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">PLAYBOX</a>
    <a href="/" class="btn" style="background:#333;">BACK</a>
</nav>

<div class="watch-video-container">
    <video id="player" playsinline controls autoplay>
        <source src="{{ movie.video_url }}" type="video/mp4" />
    </video>
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
            <button class="action-btn" onclick="alert('Share URL copied!'); navigator.clipboard.writeText(window.location.href);">
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
        const player = new Plyr('#player', {
            controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'fullscreen'],
        });
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

# --- এডমিন প্যানেল (আপডেটেড) ---
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
        <h3 style="margin-bottom:10px; color:var(--main);">2. Upload Content</h3>
        <form id="uploadForm">
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

            <!-- OPTION 1: LINK PASTE -->
            <label style="color:var(--main); font-weight:bold; margin-top:10px; display:block;">Option A: Paste Link (Google Drive / Direct URL)</label>
            <input type="text" id="fLink" name="video_link" placeholder="Paste link here...">

            <div class="or-divider"><span>OR</span></div>

            <!-- OPTION 2: UPLOAD FILE -->
            <label style="color:var(--main); font-weight:bold; display:block;">Option B: Upload File</label>
            <input type="file" id="fVideo" name="video_file" accept="video/mp4" style="padding:8px;">
            
            <div style="background:#333; height:5px; margin:15px 0; border-radius:5px; overflow:hidden;">
                <div id="pBar" style="background:var(--main); width:0%; height:100%;"></div>
            </div>
            <p id="statusMsg" style="text-align:center; color:var(--main); display:none; margin-bottom:10px;">Processing... Please wait.</p>
            
            <button type="button" onclick="startUpload()" class="btn" style="width:100%;">PUBLISH CONTENT</button>
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

    function startUpload() {
        const form = document.getElementById('uploadForm');
        
        // ভ্যালিডেশন: হয় লিঙ্ক থাকতে হবে, না হয় ফাইল থাকতে হবে
        const file = document.getElementById('fVideo').files[0];
        const link = document.getElementById('fLink').value;
        if(!file && !link) {
            alert("Please Select a File OR Paste a Link!");
            return;
        }

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();
        document.getElementById('statusMsg').style.display = 'block';
        
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const p = Math.round((e.loaded / e.total) * 100);
                document.getElementById('pBar').style.width = p + '%';
            }
        };
        xhr.onload = () => { 
            if(xhr.status === 200) { 
                alert("Done!"); window.location.reload(); 
            } else { 
                alert("Fail: " + xhr.responseText); 
            } 
        };
        xhr.open("POST", "/add_content", true);
        xhr.send(formData);
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
        return render_template_string(ADMIN_HTML, movies=movies)
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

# --- মেইন আপলোড লজিক (File + Link Support) ---
@app.route('/add_content', methods=['POST'])
def add_content():
    if not session.get('auth'): return "Unauthorized", 401
    
    video_url = None
    
    # ১. যদি ইউজার লিঙ্ক দিয়ে থাকে
    link = request.form.get('video_link')
    if link and link.strip():
        video_url = link.strip()
        
        # গুগল ড্রাইভ লিঙ্ক প্রসেসিং
        if "drive.google.com" in video_url:
            try:
                # ফাইল আইডি বের করা
                file_id = None
                if "/d/" in video_url:
                    file_id = video_url.split("/d/")[1].split("/")[0]
                elif "id=" in video_url:
                    file_id = video_url.split("id=")[1].split("&")[0]
                
                # ডাইরেক্ট ডাউনলোড লিঙ্কে কনভার্ট করা
                if file_id:
                    video_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            except:
                pass # কনভার্ট না হলে অরিজিনাল লিঙ্ক থাকবে

    # ২. যদি ইউজার ফাইল আপলোড করে (লিঙ্ক না দিলে)
    elif request.files.get('video_file'):
        try:
            file = request.files.get('video_file')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tf:
                file.save(tf.name)
                temp_path = tf.name
            
            upload = cloudinary.uploader.upload_large(temp_path, resource_type="video", chunk_size=6000000)
            os.remove(temp_path)
            video_url = upload['secure_url']
        except Exception as e:
            return f"Upload Error: {str(e)}", 500
            
    # ফাইনাল সেভ
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
        return "OK", 200
        
    return "Please provide a file or a link", 400

@app.route('/delete/<movie_id>')
def delete_movie(movie_id):
    if not session.get('auth'): return redirect('/')
    try: movies_collection.delete_one({'_id': ObjectId(movie_id)})
    except: pass
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
