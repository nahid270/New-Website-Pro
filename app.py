import os
import requests
import tempfile
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# --- কনফিগারেশন ---
# .env ফাইল না থাকলে ডিফল্ট ভ্যালু কাজ করবে
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

# --- ডিজাইন (CSS) - সম্পূর্ণ মোবাইল ফ্রেন্ডলি ---
CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    :root { --main: #e50914; --bg: #0b0b0b; --card: #181818; --text: #fff; --gray: #333; }
    * { box-sizing: border-box; margin: 0; padding: 0; outline: none; -webkit-tap-highlight-color: transparent; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: var(--bg); color: var(--text); padding-bottom: 20px; }
    
    /* Navbar */
    .navbar { background: rgba(0,0,0,0.9); padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; border-bottom: 1px solid var(--gray); backdrop-filter: blur(10px); }
    .logo { color: var(--main); font-size: 20px; font-weight: 800; text-decoration: none; letter-spacing: 1px; }
    
    /* Buttons */
    .btn { background: var(--main); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; text-decoration: none; font-weight: 600; font-size: 13px; display: inline-block; transition: 0.2s; }
    .btn:active { transform: scale(0.95); }
    .btn-danger { background: #e74c3c; width: 100%; margin-top: 8px; padding: 10px; }

    /* Layout */
    .container { max-width: 100%; padding: 15px; margin: auto; }
    
    /* Search Bar */
    .search-box { margin: 15px 0; display: flex; justify-content: center; }
    .search-input { width: 100%; max-width: 500px; padding: 12px 20px; border-radius: 50px; border: 1px solid var(--gray); background: #1a1a1a; color: white; font-size: 16px; transition: 0.3s; }
    .search-input:focus { border-color: var(--main); background: #222; }

    /* Movie Grid (Mobile Optimized) */
    .movie-grid { 
        display: grid; 
        grid-template-columns: repeat(2, 1fr); /* মোবাইলে ২ কলাম */
        gap: 10px; 
        margin-top: 15px; 
    }
    
    /* বড় স্ক্রিনে কলাম বাড়বে */
    @media (min-width: 768px) {
        .movie-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    }

    .card { background: var(--card); border-radius: 6px; overflow: hidden; position: relative; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
    .card-info { padding: 8px; }
    .card-title { font-size: 13px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 3px; }
    .card-meta { font-size: 11px; color: #aaa; }
    
    /* Player Section */
    .player-section { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 2000; display: none; flex-direction: column; justify-content: center; }
    .player-header { padding: 15px; position: absolute; top: 0; left: 0; width: 100%; z-index: 2001; display: flex; justify-content: space-between; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent); }
    
    /* Admin Styles */
    .admin-box { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--gray); }
    .admin-header { font-size: 18px; color: var(--main); margin-bottom: 15px; border-bottom: 1px solid var(--gray); padding-bottom: 10px; }
    
    /* Form Elements */
    input[type="text"], select, input[type="file"] { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid var(--gray); background: #252525; color: white; font-size: 16px; /* Font 16px prevents iOS zoom */ }
    input:focus { border-color: var(--main); }
    
    /* Search Results in Admin */
    .search-results { display: flex; overflow-x: auto; gap: 10px; padding-bottom: 10px; -webkit-overflow-scrolling: touch; }
    .search-item { flex: 0 0 100px; background: #222; padding: 5px; border-radius: 5px; text-align: center; font-size: 10px; }
    .search-item img { width: 100%; border-radius: 4px; height: 140px; object-fit: cover; }
    
    /* Progress Bar */
    .progress-container { width: 100%; background: #333; height: 10px; border-radius: 5px; margin: 15px 0; overflow: hidden; display: none; }
    .progress-bar { height: 100%; background: var(--main); width: 0%; transition: width 0.3s; }

    /* Plyr Customization */
    .plyr { width: 100%; height: 100%; }
</style>
<!-- Plyr Player -->
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
<script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
"""

# --- পাবলিক হোমপেজ (Mobile Friendly) ---
HOME_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">M-BOX</a>
    <a href="/admin" class="btn">ADMIN</a>
</nav>

<div class="container">
    <div class="search-box">
        <form action="/" method="GET" style="width:100%;">
            <input type="text" name="q" class="search-input" placeholder="Search movies..." value="{{ request.args.get('q', '') }}">
        </form>
    </div>

    <!-- Full Screen Player -->
    <div id="playerBox" class="player-section">
        <div class="player-header">
            <h3 id="pTitle" style="color:white; font-size:16px; margin:0;">Playing...</h3>
            <button onclick="closePlayer()" class="btn" style="background:rgba(255,255,255,0.2); padding:5px 12px;">✕ Close</button>
        </div>
        <video id="player" playsinline controls>
            <source src="" type="video/mp4" />
        </video>
    </div>

    <!-- Movie Grid -->
    <div class="movie-grid">
        {% if movies|length == 0 %}
            <p style="grid-column: 1/-1; text-align:center; color:#777; margin-top:20px;">No results found.</p>
        {% endif %}

        {% for m in movies %}
        <div class="card" onclick="playMovie('{{ m.video_url }}', '{{ m.title }}')">
            <img src="{{ m.poster }}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
            <div class="card-info">
                <div class="card-title">{{ m.title }}</div>
                <div class="card-meta">{{ m.year }} • {{ m.type|upper }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<script>
    let player;
    document.addEventListener('DOMContentLoaded', () => {
        player = new Plyr('#player', {
            controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'fullscreen'],
            hideControls: true
        });
    });

    function playMovie(url, title) {
        const box = document.getElementById('playerBox');
        box.style.display = 'flex';
        document.getElementById('pTitle').innerText = title;
        
        player.source = { type: 'video', sources: [{ src: url, type: 'video/mp4' }] };
        player.play();
        
        // Fullscreen request for mobile
        if (box.requestFullscreen) box.requestFullscreen();
    }

    function closePlayer() {
        player.stop();
        document.getElementById('playerBox').style.display = 'none';
        if (document.exitFullscreen) document.exitFullscreen();
    }
</script>
"""

# --- এডমিন ড্যাশবোর্ড (Mobile Optimized) ---
ADMIN_HTML = CSS + """
<nav class="navbar">
    <a href="/" class="logo">ADMIN</a>
    <a href="/logout" class="btn" style="background:#333;">LOGOUT</a>
</nav>
<div class="container">
    
    <!-- TMDB Search -->
    <div class="admin-box">
        <div class="admin-header">Auto Fill (TMDB)</div>
        <div style="display:flex; gap:8px;">
            <input type="text" id="tmdbQuery" placeholder="Movie Name..." style="margin:0;">
            <button onclick="searchTMDB()" class="btn" style="height:46px;">GO</button>
        </div>
        <div id="searchResults" class="search-results" style="margin-top:15px;"></div>
    </div>

    <!-- Upload Form -->
    <div class="admin-box">
        <div class="admin-header">Upload Video</div>
        <form id="uploadForm">
            <input type="text" id="fTitle" name="title" placeholder="Title" required>
            <div style="display:flex; gap:10px;">
                <input type="text" id="fYear" name="year" placeholder="Year" style="flex:1;">
                <select name="type" id="fType" onchange="checkType()" style="flex:1; margin:8px 0;">
                    <option value="movie">Movie</option>
                    <option value="tv">TV Show</option>
                </select>
            </div>
            
            <input type="text" id="fPoster" name="poster" placeholder="Poster Link" required>
            <input type="text" id="fBack" name="backdrop" placeholder="Backdrop Link">
            <input type="text" id="fTrailer" name="trailer" placeholder="Trailer Link">
            
            <div id="tvFields" style="display:none; gap:10px;">
                <input type="text" name="season" placeholder="Season (e.g. 1)">
                <input type="text" name="episode" placeholder="Episode (e.g. 5)">
            </div>
            
            <label style="display:block; margin-top:10px; color:#aaa; font-size:12px;">Select Video File:</label>
            <input type="file" id="fVideo" name="video_file" accept="video/mp4" required style="padding:8px;">
            
            <div class="progress-container" id="pCont">
                <div class="progress-bar" id="pBar"></div>
            </div>
            <p id="statusMsg" style="text-align:center; font-size:12px; color:var(--main); display:none; margin-bottom:10px;">Uploading... Don't close window.</p>
            
            <button type="button" onclick="startUpload()" class="btn" style="width:100%; padding:14px;">UPLOAD CONTENT</button>
        </form>
    </div>

    <!-- Manage Content -->
    <div class="admin-box">
        <div class="admin-header">Delete Content</div>
        <div class="movie-grid">
            {% for m in movies %}
            <div class="card" style="cursor:default;">
                <img src="{{ m.poster }}" style="height:120px;">
                <div class="card-info">
                    <div class="card-title">{{ m.title }}</div>
                    <a href="/delete/{{ m._id }}" onclick="return confirm('Delete {{ m.title }}?')" class="btn btn-danger">DELETE</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<script>
    function checkType() { document.getElementById('tvFields').style.display = (document.getElementById('fType').value === 'tv') ? 'flex' : 'none'; }
    
    async function searchTMDB() {
        const q = document.getElementById('tmdbQuery').value;
        if(!q) return alert("Please type a name!");
        const btn = document.querySelector('button[onclick="searchTMDB()"]');
        btn.innerText = "...";
        
        try {
            const res = await fetch(`/api/tmdb?q=${q}`);
            const data = await res.json();
            const div = document.getElementById('searchResults');
            div.innerHTML = '';
            
            if(!data.results || data.results.length === 0) {
                div.innerHTML = '<p style="color:#777; width:100%; text-align:center;">No match found.</p>';
            }

            data.results.slice(0, 10).forEach(item => {
                const d = document.createElement('div');
                d.className = 'search-item';
                d.innerHTML = `<img src="https://image.tmdb.org/t/p/w200${item.poster_path || ''}"><p>${item.title || item.name}</p>`;
                d.onclick = () => {
                    document.getElementById('fTitle').value = item.title || item.name;
                    document.getElementById('fYear').value = (item.release_date || item.first_air_date || '').split('-')[0];
                    document.getElementById('fPoster').value = `https://image.tmdb.org/t/p/w500${item.poster_path}`;
                    document.getElementById('fBack').value = `https://image.tmdb.org/t/p/original${item.backdrop_path}`;
                    document.getElementById('fType').value = item.title ? 'movie' : 'tv';
                    checkType();
                    div.innerHTML = ''; // Clear after selection
                };
                div.appendChild(d);
            });
        } catch(e) { alert("Error connecting to TMDB"); }
        btn.innerText = "GO";
    }

    function startUpload() {
        const form = document.getElementById('uploadForm');
        if(!form.checkValidity()) { form.reportValidity(); return; }
        
        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();
        
        document.getElementById('pCont').style.display = 'block';
        document.getElementById('statusMsg').style.display = 'block';
        
        xhr.upload.onprogress = (e) => {
            const p = Math.round((e.loaded / e.total) * 100);
            document.getElementById('pBar').style.width = p + '%';
        };
        
        xhr.onload = () => { 
            if(xhr.status === 200) { 
                alert("Success!"); 
                window.location.reload(); 
            } else { 
                alert("Failed: " + xhr.responseText);
                document.getElementById('statusMsg').innerText = "Upload Failed!";
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

@app.route('/api/tmdb')
def tmdb_api():
    q = request.args.get('q')
    if not TMDB_API_KEY: return jsonify({"results": []})
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={q}"
    try:
        return jsonify(requests.get(url).json())
    except:
        return jsonify({"results": []})

@app.route('/admin')
def admin():
    if session.get('auth'): 
        movies = list(movies_collection.find().sort('_id', -1))
        return render_template_string(ADMIN_HTML, movies=movies)
    
    return render_template_string(CSS + """
    <div style="height:100vh; display:flex; align-items:center; justify-content:center; padding:20px;">
        <div style="background:#1a1a1a; padding:30px; border-radius:10px; width:100%; max-width:400px; text-align:center;">
            <h2 style="color:var(--main); margin-bottom:20px;">ADMIN LOGIN</h2>
            <form action="/login" method="POST">
                <input type="text" name="u" placeholder="User" required style="text-align:center;">
                <input type="password" name="p" placeholder="Pass" required style="text-align:center;">
                <button class="btn" style="width:100%; margin-top:15px; padding:12px;">LOGIN</button>
            </form>
            <a href="/" style="display:block; margin-top:15px; color:#777; text-decoration:none; font-size:12px;">Back to Home</a>
        </div>
    </div>
    """)

@app.route('/login', methods=['POST'])
def login():
    if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
        session['auth'] = True
        return redirect('/admin')
    return "Wrong Password! <a href='/admin'>Back</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add_content', methods=['POST'])
def add_content():
    if not session.get('auth'): return "Unauthorized", 401
    try:
        file = request.files.get('video_file')
        if file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tf:
                file.save(tf.name)
                temp_path = tf.name
            
            upload = cloudinary.uploader.upload_large(temp_path, resource_type="video", chunk_size=6000000)
            os.remove(temp_path)
            
            movies_collection.insert_one({
                "title": request.form.get('title'),
                "year": request.form.get('year'),
                "poster": request.form.get('poster'),
                "backdrop": request.form.get('backdrop'),
                "trailer": request.form.get('trailer'),
                "type": request.form.get('type'),
                "season": request.form.get('season'),
                "episode": request.form.get('episode'),
                "video_url": upload['secure_url']
            })
            return "OK", 200
    except Exception as e:
        return str(e), 500
    return "No file provided", 400

@app.route('/delete/<movie_id>')
def delete_movie(movie_id):
    if not session.get('auth'): return redirect('/')
    try:
        movies_collection.delete_one({'_id': ObjectId(movie_id)})
    except:
        pass
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
