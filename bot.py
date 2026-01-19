import os
import certifi
from flask import Flask, request, redirect, url_for, flash, session, jsonify, render_template_string
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import string
import random
from jinja2 import DictLoader

app = Flask(__name__)

# ===============================
# ⚙️ কনফিগারেশন (SETTINGS)
# ===============================

# সিক্রেট কি সরাসরি কোডে দেওয়া হলো
app.config['SECRET_KEY'] = 'my_super_hardcoded_secret_key_12345'

# ⚠️ আপনার MongoDB কানেকশন লিংক (সরাসরি কোডে বসানো হয়েছে)
# আমি লিংকের শেষে '/shortener_db' যুক্ত করেছি যাতে ডাটা সঠিক জায়গায় সেভ হয়
app.config["MONGO_URI"] = "mongodb+srv://MoviaXBot3:MoviaXBot3@cluster0.ictlkq8.mongodb.net/shortener_db?retryWrites=true&w=majority&appName=Cluster0"

# SSL সার্টিফিকেটের সমস্যা সমাধানের জন্য এটি জরুরি
app.config["MONGO_TLS_CA_FILE"] = certifi.where()

# ডাটাবেস ইনিশিয়ালাইজেশন
try:
    mongo = PyMongo(app)
    # কানেকশন টেস্ট
    # mongo.db.command('ping') 
    print("✅ MongoDB Configured Successfully inside Code!")
except Exception as e:
    print(f"❌ Database Configuration Error: {e}")
    mongo = None

# ===============================
# 🎨 HTML টেমপ্লেট (HTML Templates)
# ===============================

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.site_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f7f6; font-family: 'Segoe UI', sans-serif; }
        .ad-box { background: #e2e8f0; padding: 15px; margin: 20px 0; text-align: center; border: 1px dashed #94a3b8; border-radius: 8px; }
        .main-card { background: white; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); padding: 40px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark mb-4 shadow">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">🔗 {{ config.site_name }}</a>
            <div class="d-flex">
                {% if session.get('admin_logged_in') %}
                    <a href="/admin/dashboard" class="btn btn-sm btn-outline-light me-2">Dashboard</a>
                    <a href="/admin/logout" class="btn btn-sm btn-danger">Logout</a>
                {% else %}
                    <a href="/admin/login" class="text-decoration-none text-secondary small">Admin</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container">
        {% if config.ad_header %}<div class="ad-box">{{ config.ad_header | safe }}</div>{% endif %}

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}

        {% if config.ad_footer %}<div class="ad-box">{{ config.ad_footer | safe }}</div>{% endif %}
        
        <footer class="text-center mt-5 text-muted small">
            &copy; 2024 {{ config.site_name }}. All rights reserved.
        </footer>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

HOME_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="main-card text-center">
            <h2 class="mb-4 fw-bold text-primary">Shorten Your Link</h2>
            <form method="POST" action="/">
                <div class="input-group input-group-lg mb-3 shadow-sm">
                    <input type="url" name="url" class="form-control" placeholder="Paste long URL here..." required>
                    <button class="btn btn-primary px-4" type="submit">Shorten</button>
                </div>
            </form>
            {% if short_url %}
            <div class="mt-5 p-4 bg-light border rounded">
                <p class="mb-2 text-muted">Here is your short link:</p>
                <h3 class="text-success fw-bold text-break">{{ short_url }}</h3>
                <div class="mt-3">
                    <a href="{{ short_url }}" target="_blank" class="btn btn-success">Open Link</a>
                    <button onclick="navigator.clipboard.writeText('{{ short_url }}')" class="btn btn-outline-secondary">Copy</button>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
"""

REDIRECT_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <div class="main-card">
            <h3 class="fw-bold">Please Wait...</h3>
            <p class="text-muted">Step <span class="badge bg-secondary">{{ current_page }}</span> of <span class="badge bg-secondary">{{ total_steps }}</span></p>

            {% if config.ad_middle %}<div class="ad-box my-4">{{ config.ad_middle | safe }}</div>{% endif %}

            <div id="timer-area" class="my-5">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <h1 class="display-3 fw-bold text-dark" id="countdown">5</h1>
                <p class="text-muted">Seconds remaining</p>
            </div>

            <div id="link-area" style="display:none;">
                <a href="{{ url_for('redirect_logic', short_code=link.short_code, p=current_page+1) }}" 
                   class="btn btn-success btn-lg px-5 shadow">
                   {% if current_page == total_steps %} Get Link &rarr; {% else %} Next Step &rarr; {% endif %}
                </a>
            </div>
        </div>
    </div>
</div>
<script>
    let seconds = 5;
    const countEl = document.getElementById('countdown');
    const timerArea = document.getElementById('timer-area');
    const linkArea = document.getElementById('link-area');
    const interval = setInterval(() => {
        seconds--;
        countEl.innerText = seconds;
        if (seconds <= 0) {
            clearInterval(interval);
            timerArea.style.display = 'none';
            linkArea.style.display = 'block';
        }
    }, 1000);
</script>
{% endblock %}
"""

LOGIN_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="main-card">
            <h3 class="text-center mb-4">Admin Login</h3>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-dark w-100">Login</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

DASHBOARD_HTML = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Admin Dashboard</h2>
</div>
<div class="row mb-4">
    <div class="col-md-6"><div class="card p-4 bg-primary text-white border-0 shadow-sm"><h3>{{ stats.links }}</h3><span>Total Links</span></div></div>
    <div class="col-md-6"><div class="card p-4 bg-success text-white border-0 shadow-sm"><h3>{{ stats.clicks }}</h3><span>Total Clicks</span></div></div>
</div>

<ul class="nav nav-tabs mb-3" id="adminTab" role="tablist">
    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#settings">⚙️ Settings</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#links">🔗 Links</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#api">🔑 API Keys</button></li>
</ul>

<div class="tab-content">
    <div class="tab-pane fade show active" id="settings">
        <div class="main-card">
            <form method="POST">
                <input type="hidden" name="update_settings" value="1">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Website Name</label>
                        <input type="text" name="site_name" class="form-control" value="{{ config.site_name }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label fw-bold text-danger">Redirect Steps</label>
                        <select name="total_pages" class="form-select">
                            <option value="0" {% if config.total_pages==0 %}selected{% endif %}>0 (Direct)</option>
                            <option value="1" {% if config.total_pages==1 %}selected{% endif %}>1 Page (Standard)</option>
                            <option value="2" {% if config.total_pages==2 %}selected{% endif %}>2 Pages (More Ads)</option>
                            <option value="3" {% if config.total_pages==3 %}selected{% endif %}>3 Pages (Max Revenue)</option>
                        </select>
                    </div>
                </div>
                <h5 class="mt-3 mb-3 text-muted">Ads Config</h5>
                <div class="mb-3"><label>Header Ad</label><textarea name="ad_header" class="form-control" rows="2">{{ config.ad_header }}</textarea></div>
                <div class="mb-3"><label>Middle Ad</label><textarea name="ad_middle" class="form-control" rows="2">{{ config.ad_middle }}</textarea></div>
                <div class="mb-3"><label>Footer Ad</label><textarea name="ad_footer" class="form-control" rows="2">{{ config.ad_footer }}</textarea></div>
                <button type="submit" class="btn btn-primary px-4">Save Config</button>
            </form>
        </div>
    </div>
    <div class="tab-pane fade" id="links">
        <div class="main-card p-0 overflow-hidden">
            <table class="table table-striped mb-0">
                <thead class="table-dark"><tr><th>Original URL</th><th>Short Code</th><th>Clicks</th></tr></thead>
                <tbody>
                    {% for link in links %}
                    <tr>
                        <td class="text-truncate" style="max-width:250px;">{{ link.original_url }}</td>
                        <td><a href="/{{ link.short_code }}" target="_blank" class="fw-bold">{{ link.short_code }}</a></td>
                        <td>{{ link.clicks }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="tab-pane fade" id="api">
        <div class="main-card mb-4">
            <form method="POST" class="d-flex gap-2">
                <input type="hidden" name="create_api" value="1">
                <input type="text" name="label" class="form-control" placeholder="Label" required>
                <button class="btn btn-dark">Generate Key</button>
            </form>
        </div>
        <div class="list-group">
            {% for api in api_keys %}
            <div class="list-group-item"><strong>{{ api.label }}</strong>: <code class="text-primary">{{ api.key }}</code></div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

# ===============================
# 🛠️ HELPER & LOGIC
# ===============================

TEMPLATES = {
    'base': BASE_HTML,
    'index': HOME_HTML,
    'redirect': REDIRECT_HTML,
    'login': LOGIN_HTML,
    'dashboard': DASHBOARD_HTML
}

app.jinja_loader = DictLoader(TEMPLATES)

def get_settings():
    """ডাটাবেস চেক করে, না পেলে এরর হ্যান্ডেল করে"""
    try:
        if not mongo:
            return {'site_name': 'DB Error', 'total_pages': 0}
            
        settings = mongo.db.settings.find_one({'_id': 'site_config'})
        if not settings:
            default_settings = {
                '_id': 'site_config',
                'site_name': 'BotShortener',
                'total_pages': 1,
                'ad_header': '',
                'ad_middle': '',
                'ad_footer': ''
            }
            mongo.db.settings.insert_one(default_settings)
            return default_settings
        return settings
    except Exception as e:
        print(f"Error fetching settings: {e}")
        # যদি ডাটাবেস এরর দেয়, তবুও যেন সাইট ক্র্যাশ না করে
        return {'site_name': 'Site', 'total_pages': 0}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    if not mongo:
        raise Exception("Database not connected!")
        
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not mongo.db.links.find_one({'short_code': code}):
            return code

@app.context_processor
def inject_conf():
    return dict(config=get_settings())

# ===============================
# 🌐 ROUTING
# ===============================

@app.route('/', methods=['GET', 'POST'])
def index():
    short_url = None
    if request.method == 'POST':
        original_url = request.form.get('url')
        if original_url and mongo:
            try:
                code = generate_code()
                mongo.db.links.insert_one({
                    'original_url': original_url,
                    'short_code': code,
                    'clicks': 0,
                    'created_at': datetime.utcnow()
                })
                short_url = request.host_url + code
            except Exception as e:
                flash(f"Database Error: {str(e)}", "danger")
        elif not mongo:
            flash("Database connection failed. Please check your connection string.", "danger")
            
    return render_template_string(TEMPLATES['index'], short_url=short_url)

@app.route('/<short_code>')
def redirect_logic(short_code):
    if not mongo:
        return "Database not connected. Please contact admin.", 500

    link = mongo.db.links.find_one_or_404({'short_code': short_code})
    settings = get_settings()
    current_page = request.args.get('p', 1, type=int)
    total_steps = settings.get('total_pages', 1)

    if total_steps == 0:
        mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
        return redirect(link['original_url'])

    if current_page <= total_steps:
        return render_template_string(TEMPLATES['redirect'], 
                                      link=link, 
                                      current_page=current_page, 
                                      total_steps=total_steps)
    
    mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
    return redirect(link['original_url'])

# ===============================
# 🔒 ADMIN PANEL
# ===============================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if not mongo:
        flash("Database not connected!", "danger")
        return render_template_string(TEMPLATES['login'])

    try:
        if mongo.db.users.count_documents({'username': 'admin'}) == 0:
            mongo.db.users.insert_one({
                'username': 'admin',
                'password': generate_password_hash('123456')
            })
    except Exception as e:
        print(f"DB Error on login check: {e}")

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid Username or Password', 'danger')
        
    return render_template_string(TEMPLATES['login'])

@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if not mongo:
        return "Database Error", 500
        
    if request.method == 'POST':
        if 'update_settings' in request.form:
            new_settings = {
                'site_name': request.form.get('site_name'),
                'total_pages': int(request.form.get('total_pages')),
                'ad_header': request.form.get('ad_header'),
                'ad_middle': request.form.get('ad_middle'),
                'ad_footer': request.form.get('ad_footer')
            }
            mongo.db.settings.update_one({'_id': 'site_config'}, {'$set': new_settings})
            flash('Settings Updated Successfully!', 'success')
        
        elif 'create_api' in request.form:
            chars = string.ascii_letters + string.digits
            key = "API-" + ''.join(random.choices(chars, k=12)).upper()
            mongo.db.api_keys.insert_one({
                'key': key,
                'label': request.form.get('label'),
                'created_at': datetime.utcnow()
            })
            flash('API Key Created!', 'success')

    links = list(mongo.db.links.find().sort('created_at', -1).limit(50))
    api_keys = list(mongo.db.api_keys.find())
    
    total_links = mongo.db.links.count_documents({})
    clicks_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$clicks"}}}]
    click_res = list(mongo.db.links.aggregate(clicks_pipeline))
    total_clicks = click_res[0]['total'] if click_res else 0

    return render_template_string(TEMPLATES['dashboard'], 
                                  links=links, 
                                  api_keys=api_keys, 
                                  stats={'links': total_links, 'clicks': total_clicks})

@app.route('/api/shorten', methods=['POST'])
def api_shorten():
    if not mongo: return jsonify({'error': 'DB Error'}), 500
    
    key = request.headers.get('x-api-key')
    if not mongo.db.api_keys.find_one({'key': key}):
        return jsonify({'error': 'Invalid API Key'}), 401

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL missing'}), 400

    chars = string.ascii_letters + string.digits
    code = ''.join(random.choices(chars, k=6))
    
    mongo.db.links.insert_one({
        'original_url': data['url'],
        'short_code': code,
        'clicks': 0,
        'created_at': datetime.utcnow()
    })

    return jsonify({
        'status': 'success',
        'short_url': request.host_url + code,
        'short_code': code
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
