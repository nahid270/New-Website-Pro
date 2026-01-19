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

# ========================================================
# ⚙️ কনফিগারেশন এবং ডাটাবেস সেটআপ
# ========================================================

# ১. সিকিউরিটি কি
app.config['SECRET_KEY'] = 'super_final_secret_key_2026_pro'

# ২. আপনার MongoDB লিংক (সরাসরি কোডে সেট করা)
MONGO_URI = "mongodb+srv://MoviaXBot3:MoviaXBot3@cluster0.ictlkq8.mongodb.net/shortener_db?retryWrites=true&w=majority&appName=Cluster0"

app.config["MONGO_URI"] = MONGO_URI
app.config["MONGO_TLS_CA_FILE"] = certifi.where()

# ৩. ডাটাবেস কানেকশন
try:
    mongo = PyMongo(app)
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")
    mongo = None

# ========================================================
# 🎨 সম্পূর্ণ HTML টেমপ্লেট (বিস্তারিত ডিজাইন)
# ========================================================

# ১. বেইজ টেমপ্লেট (হেডার, ফুটার, স্টাইল)
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.site_name }}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f2f5; font-family: 'Segoe UI', sans-serif; }
        .navbar { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .ad-box { 
            background-color: #e9ecef; 
            border: 2px dashed #adb5bd; 
            padding: 15px; 
            margin: 20px 0; 
            text-align: center; 
            border-radius: 8px;
            min-height: 80px;
            display: flex; align-items: center; justify-content: center;
        }
        .main-card { 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.08); 
            padding: 30px; 
            margin-top: 30px; 
        }
        .nav-link { cursor: pointer; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">🔗 {{ config.site_name }}</a>
            <div class="ms-auto">
                {% if session.get('admin_logged_in') %}
                    <a href="/admin/dashboard" class="btn btn-sm btn-outline-light me-2">Dashboard</a>
                    <a href="/admin/logout" class="btn btn-sm btn-danger">Logout</a>
                {% else %}
                    <a href="/admin/login" class="text-decoration-none text-secondary small">Admin Login</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Header Ad -->
        {% if config.ad_header %}
            <div class="ad-box">{{ config.ad_header | safe }}</div>
        {% endif %}

        <!-- Alerts -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show mt-3">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Content Block -->
        {% block content %}{% endblock %}

        <!-- Footer Ad -->
        {% if config.ad_footer %}
            <div class="ad-box">{{ config.ad_footer | safe }}</div>
        {% endif %}
        
        <footer class="text-center mt-5 mb-4 text-muted small">
            &copy; 2024 {{ config.site_name }}. All rights reserved.
        </footer>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ২. হোম পেজ
HOME_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="main-card text-center">
            <h2 class="mb-4 fw-bold text-dark">Shorten Your URL</h2>
            <form method="POST" action="/">
                <div class="input-group input-group-lg mb-3 shadow-sm">
                    <input type="url" name="url" class="form-control" placeholder="Paste your long link here..." required>
                    <button class="btn btn-primary px-4 fw-bold" type="submit">Shorten</button>
                </div>
            </form>

            {% if short_url %}
            <div class="mt-5 p-4 bg-light border rounded shadow-sm">
                <p class="mb-2 text-muted fw-bold">Your Shortened Link:</p>
                <div class="input-group">
                    <input type="text" value="{{ short_url }}" id="shortUrlInput" class="form-control text-center text-success fw-bold fs-5" readonly>
                    <button onclick="copyLink()" class="btn btn-outline-primary">Copy</button>
                    <a href="{{ short_url }}" target="_blank" class="btn btn-success">Open</a>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<script>
function copyLink() {
    var copyText = document.getElementById("shortUrlInput");
    copyText.select();
    navigator.clipboard.writeText(copyText.value);
    alert("Copied: " + copyText.value);
}
</script>
{% endblock %}
"""

# ৩. রিডাইরেক্ট পেজ (টাইমার ও স্টেপ)
REDIRECT_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <div class="main-card">
            <h3 class="fw-bold mb-3">Please Wait...</h3>
            <p class="text-muted">Step <span class="badge bg-dark">{{ current_page }}</span> of <span class="badge bg-secondary">{{ total_steps }}</span></p>

            <!-- Middle Ad -->
            {% if config.ad_middle %}
                <div class="ad-box my-4">{{ config.ad_middle | safe }}</div>
            {% endif %}

            <!-- Timer -->
            <div id="timer-area" class="my-5 p-4 bg-light rounded">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <h1 class="display-3 fw-bold text-danger" id="countdown">5</h1>
                <p class="text-muted fw-bold">Seconds Remaining</p>
            </div>

            <!-- Next Button -->
            <div id="link-area" style="display:none;" class="my-5">
                <a href="{{ url_for('redirect_logic', short_code=link.short_code, p=current_page+1) }}" 
                   class="btn btn-success btn-lg px-5 shadow fw-bold">
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

# ৪. লগইন পেজ
LOGIN_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="main-card">
            <h3 class="text-center mb-4 fw-bold">Admin Login</h3>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-dark w-100 fw-bold py-2">Login</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

# ৫. ড্যাশবোর্ড পেজ (সেটিংস, লিংক, এপিআই)
DASHBOARD_HTML = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Admin Dashboard</h2>
    <span class="badge bg-success">Active</span>
</div>

<!-- Stats -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card p-3 bg-primary text-white border-0 shadow-sm mb-2">
            <h3>{{ stats.links }}</h3>
            <span>Total Links</span>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card p-3 bg-success text-white border-0 shadow-sm mb-2">
            <h3>{{ stats.clicks }}</h3>
            <span>Total Clicks</span>
        </div>
    </div>
</div>

<!-- Tabs -->
<ul class="nav nav-tabs mb-3" id="adminTab" role="tablist">
    <li class="nav-item"><button class="nav-link active fw-bold" data-bs-toggle="tab" data-bs-target="#settings">⚙️ Settings</button></li>
    <li class="nav-item"><button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#links">🔗 Links</button></li>
    <li class="nav-item"><button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#api">🔑 API Keys</button></li>
</ul>

<div class="tab-content">
    
    <!-- Settings Tab -->
    <div class="tab-pane fade show active" id="settings">
        <div class="main-card pt-3">
            <form method="POST">
                <input type="hidden" name="update_settings" value="1">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="fw-bold">Website Name</label>
                        <input type="text" name="site_name" class="form-control" value="{{ config.site_name }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="fw-bold text-danger">Redirect Steps (Pages)</label>
                        <select name="total_pages" class="form-select">
                            <option value="0" {% if config.total_pages==0 %}selected{% endif %}>0 Page (Direct)</option>
                            <option value="1" {% if config.total_pages==1 %}selected{% endif %}>1 Page (Standard)</option>
                            <option value="2" {% if config.total_pages==2 %}selected{% endif %}>2 Pages (Max Ads)</option>
                        </select>
                    </div>
                </div>
                
                <h5 class="mt-3 mb-3 text-primary">Ads Configuration</h5>
                <div class="mb-3"><label>Header Ad</label><textarea name="ad_header" class="form-control" rows="2">{{ config.ad_header }}</textarea></div>
                <div class="mb-3"><label>Middle Ad</label><textarea name="ad_middle" class="form-control" rows="2">{{ config.ad_middle }}</textarea></div>
                <div class="mb-3"><label>Footer Ad</label><textarea name="ad_footer" class="form-control" rows="2">{{ config.ad_footer }}</textarea></div>
                
                <button type="submit" class="btn btn-primary px-4 fw-bold">Save Settings</button>
            </form>
        </div>
    </div>

    <!-- Links Tab -->
    <div class="tab-pane fade" id="links">
        <div class="main-card p-0 overflow-auto" style="max-height: 500px;">
            <table class="table table-striped mb-0">
                <thead class="table-dark sticky-top">
                    <tr><th>Original</th><th>Short</th><th>Clicks</th></tr>
                </thead>
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

    <!-- API Tab -->
    <div class="tab-pane fade" id="api">
        <div class="main-card mb-3">
            <h5>Generate New API Key</h5>
            <form method="POST" class="d-flex gap-2">
                <input type="hidden" name="create_api" value="1">
                <input type="text" name="label" class="form-control" placeholder="Label (e.g. My Bot)" required>
                <button class="btn btn-dark fw-bold">Generate</button>
            </form>
        </div>
        <div class="list-group">
            {% for api in api_keys %}
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span class="fw-bold">{{ api.label }}</span>
                <code class="text-primary fs-5 user-select-all">{{ api.key }}</code>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

# টেমপ্লেট লোড করা
TEMPLATES = {
    'base': BASE_HTML,
    'index': HOME_HTML,
    'redirect': REDIRECT_HTML,
    'login': LOGIN_HTML,
    'dashboard': DASHBOARD_HTML
}
app.jinja_loader = DictLoader(TEMPLATES)


# ========================================================
# 🛠️ ফাংশন এবং লজিক
# ========================================================

def get_settings():
    """ডাটাবেস থেকে সেটিংস লোড করে"""
    try:
        if not mongo: return {'site_name': 'Error', 'total_pages': 0}
        settings = mongo.db.settings.find_one({'_id': 'site_config'})
        if not settings:
            default_settings = {
                '_id': 'site_config',
                'site_name': 'SmartLink',
                'total_pages': 1,
                'ad_header': '', 'ad_middle': '', 'ad_footer': ''
            }
            mongo.db.settings.insert_one(default_settings)
            return default_settings
        return settings
    except:
        return {'site_name': 'Error', 'total_pages': 0}

def generate_code(length=5):
    """ইউনিক শর্ট কোড জেনারেট করে"""
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if mongo and not mongo.db.links.find_one({'short_code': code}):
            return code

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_conf():
    return dict(config=get_settings())

# ========================================================
# 🔥 API হ্যান্ডলিং লজিক (কমন ফাংশন)
# ========================================================

def handle_api_request(key, url):
    """এটিই সেই ফাংশন যা বটের রিকোয়েস্ট হ্যান্ডেল করে"""
    if not mongo: return jsonify({'status': 'error', 'message': 'DB Failed'}), 500
    
    # API Key যাচাই
    if not mongo.db.api_keys.find_one({'key': key}):
        return jsonify({'status': 'error', 'message': 'Invalid API Key'}), 401

    try:
        code = generate_code()
        mongo.db.links.insert_one({
            'original_url': url,
            'short_code': code,
            'clicks': 0,
            'created_at': datetime.utcnow()
        })
        
        # বট যে ফরম্যাটে চায়
        short_url = request.host_url + code
        return jsonify({
            'status': 'success',
            'shortenedUrl': short_url,
            'short_url': short_url,
            'url': short_url
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ========================================================
# 🌐 রাউটস (ওয়েবসাইট + API একসাথে)
# ========================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # ১. বটের রিকোয়েস্ট চেক করা (যদি ?api=... বা ?key=... থাকে)
    api_key = request.args.get('api') or request.args.get('key')
    long_url = request.args.get('url') or request.args.get('link')

    # যদি বটের প্যারামিটার থাকে, তবে HTML না দেখিয়ে JSON দেখাবে
    if api_key and long_url:
        return handle_api_request(api_key, long_url)

    # ২. সাধারণ ভিজিটরদের জন্য ওয়েবসাইট দেখানো
    short_url = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url and mongo:
            try:
                code = generate_code()
                mongo.db.links.insert_one({
                    'original_url': url,
                    'short_code': code,
                    'clicks': 0,
                    'created_at': datetime.utcnow()
                })
                short_url = request.host_url + code
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")
    return render_template_string(TEMPLATES['index'], short_url=short_url)

# আলাদা /api রাউট (বট যদি স্পেসিফিকভাবে এখানে হিট করে)
@app.route('/api', methods=['GET', 'POST'])
def api_endpoint():
    key = request.values.get('api') or request.values.get('key')
    url = request.values.get('url') or request.values.get('link')
    
    if not key or not url:
        return jsonify({'status': 'error', 'message': 'Missing API Key or URL'}), 400
        
    return handle_api_request(key, url)


@app.route('/<short_code>')
def redirect_logic(short_code):
    if not mongo: return "Database Error", 500
    link = mongo.db.links.find_one_or_404({'short_code': short_code})
    settings = get_settings()
    page = request.args.get('p', 1, type=int)
    
    # 0 পেজ হলে সরাসরি রিডাইরেক্ট
    if settings['total_pages'] == 0:
        mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
        return redirect(link['original_url'])

    # স্টেপ বাকি থাকলে টাইমার পেজ দেখাবে
    if page <= settings['total_pages']:
        return render_template_string(TEMPLATES['redirect'], link=link, current_page=page, total_steps=settings['total_pages'])
    
    # শেষ হলে রিডাইরেক্ট
    mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
    return redirect(link['original_url'])


# ========================================================
# 🔒 অ্যাডমিন প্যানেল
# ========================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if mongo and mongo.db.users.count_documents({'username': 'admin'}) == 0:
        mongo.db.users.insert_one({'username': 'admin', 'password': generate_password_hash('123456')})

    if request.method == 'POST':
        user = mongo.db.users.find_one({'username': request.form.get('username')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Wrong Credentials', 'danger')

    return render_template_string(TEMPLATES['login'])

@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        if 'update_settings' in request.form:
            mongo.db.settings.update_one({'_id': 'site_config'}, {'$set': {
                'site_name': request.form.get('site_name'),
                'total_pages': int(request.form.get('total_pages')),
                'ad_header': request.form.get('ad_header'),
                'ad_middle': request.form.get('ad_middle'),
                'ad_footer': request.form.get('ad_footer')
            }})
            flash('Settings Updated!', 'success')
        
        elif 'create_api' in request.form:
            key = "API-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            mongo.db.api_keys.insert_one({
                'key': key, 'label': request.form.get('label'), 'created_at': datetime.utcnow()
            })
            flash('New Key Created!', 'success')

    links = list(mongo.db.links.find().sort('created_at', -1).limit(50))
    api_keys = list(mongo.db.api_keys.find())
    
    total_links = mongo.db.links.count_documents({})
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$clicks"}}}]
    res = list(mongo.db.links.aggregate(pipeline))
    total_clicks = res[0]['total'] if res else 0

    return render_template_string(TEMPLATES['dashboard'], 
                                  links=links, api_keys=api_keys, 
                                  stats={'links': total_links, 'clicks': total_clicks})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
