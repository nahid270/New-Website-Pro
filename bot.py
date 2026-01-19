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
# ⚙️ কনফিগারেশন এবং ডাটাবেস কানেকশন
# ========================================================

# ১. সিকিউরিটি কি
app.config['SECRET_KEY'] = 'final_full_code_secret_key_2026'

# ২. আপনার MongoDB লিংক (ডাটাবেস নাম সহ)
MONGO_URI = "mongodb+srv://MoviaXBot3:MoviaXBot3@cluster0.ictlkq8.mongodb.net/shortener_db?retryWrites=true&w=majority&appName=Cluster0"

app.config["MONGO_URI"] = MONGO_URI
app.config["MONGO_TLS_CA_FILE"] = certifi.where()

# ৩. ডাটাবেস কানেক্ট করা
try:
    mongo = PyMongo(app)
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")
    mongo = None

# ========================================================
# 🎨 সম্পূর্ণ HTML টেমপ্লেট (বিস্তারিত কোড)
# ========================================================

# ১. বেইজ ডিজাইন (Header, Footer, CSS)
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.site_name }}</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f2f5; font-family: 'Segoe UI', sans-serif; }
        .navbar { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .container { max-width: 900px; }
        
        /* বিজ্ঞাপনের বক্স ডিজাইন */
        .ad-box { 
            background-color: #e9ecef; 
            border: 2px dashed #cbd5e1; 
            padding: 15px; 
            margin: 20px 0; 
            text-align: center; 
            border-radius: 8px;
            min-height: 90px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #64748b;
        }

        /* কার্ড ডিজাইন */
        .main-card { 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.08); 
            padding: 40px; 
            margin-top: 30px; 
        }

        .btn-primary { background-color: #2563eb; border: none; }
        .btn-primary:hover { background-color: #1d4ed8; }
    </style>
</head>
<body>
    <!-- নেভিগেশন বার -->
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
        <!-- হেডার বিজ্ঞাপন -->
        {% if config.ad_header %}
            <div class="ad-box">
                {{ config.ad_header | safe }}
            </div>
        {% endif %}

        <!-- অ্যালার্ট মেসেজ -->
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

        <!-- মূল কন্টেন্ট -->
        {% block content %}{% endblock %}

        <!-- ফুটার বিজ্ঞাপন -->
        {% if config.ad_footer %}
            <div class="ad-box">
                {{ config.ad_footer | safe }}
            </div>
        {% endif %}
        
        <footer class="text-center mt-5 mb-4 text-muted small">
            &copy; 2024 {{ config.site_name }}. All rights reserved.
        </footer>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ২. হোম পেজ (লিংক পেস্ট করার জায়গা)
HOME_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-10">
        <div class="main-card text-center">
            <h2 class="mb-4 fw-bold text-dark">Shorten Your Long URL</h2>
            <p class="text-muted mb-4">Paste your long link below to create a short, shareable link.</p>
            
            <form method="POST" action="/">
                <div class="input-group input-group-lg mb-3 shadow-sm">
                    <input type="url" name="url" class="form-control" placeholder="https://example.com/very-long-url..." required>
                    <button class="btn btn-primary px-5 fw-bold" type="submit">SHORTEN</button>
                </div>
            </form>

            {% if short_url %}
            <div class="mt-5 p-4 bg-light border rounded">
                <p class="mb-2 text-muted fw-bold">Your Shortened Link:</p>
                
                <div class="d-flex justify-content-center align-items-center gap-2 flex-wrap">
                    <input type="text" value="{{ short_url }}" id="shortUrlInput" class="form-control text-center text-success fw-bold fs-5" readonly>
                    
                    <button onclick="copyLink()" class="btn btn-outline-primary">
                        Copy Link
                    </button>
                    
                    <a href="{{ short_url }}" target="_blank" class="btn btn-success">
                        Open Link
                    </a>
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
    copyText.setSelectionRange(0, 99999); 
    navigator.clipboard.writeText(copyText.value);
    alert("Copied to clipboard: " + copyText.value);
}
</script>
{% endblock %}
"""

# ৩. রিডাইরেক্ট পেজ (টাইমার এবং অ্যাড শো করার পেজ)
REDIRECT_HTML = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <div class="main-card">
            <h3 class="fw-bold mb-3">Please Wait...</h3>
            <p class="text-muted mb-4">
                You are on step <span class="badge bg-secondary fs-6">{{ current_page }}</span> of 
                <span class="badge bg-dark fs-6">{{ total_steps }}</span>
            </p>

            <!-- মাঝখানের বিজ্ঞাপন (টাইমারের কাছে) -->
            {% if config.ad_middle %}
                <div class="ad-box my-4">
                    {{ config.ad_middle | safe }}
                </div>
            {% endif %}

            <!-- টাইমার সেকশন -->
            <div id="timer-area" class="my-5 p-4 bg-light rounded">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <h1 class="display-3 fw-bold text-danger" id="countdown">5</h1>
                <p class="text-muted fw-bold">Seconds Remaining</p>
            </div>

            <!-- পরবর্তী বাটন (লুকানো থাকবে) -->
            <div id="link-area" style="display:none;" class="my-5">
                <a href="{{ url_for('redirect_logic', short_code=link.short_code, p=current_page+1) }}" 
                   class="btn btn-success btn-lg px-5 shadow fw-bold animate-btn">
                   {% if current_page == total_steps %} 
                       Get Destination Link &rarr; 
                   {% else %} 
                       Next Step &rarr; 
                   {% endif %}
                </a>
            </div>
        </div>
    </div>
</div>

<script>
    let seconds = 5; // ৫ সেকেন্ড সময়
    const countEl = document.getElementById('countdown');
    const timerArea = document.getElementById('timer-area');
    const linkArea = document.getElementById('link-area');

    const interval = setInterval(() => {
        seconds--;
        countEl.innerText = seconds;
        
        if (seconds <= 0) {
            clearInterval(interval);
            // টাইমার লুকিয়ে বাটন দেখানো
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
                <button type="submit" class="btn btn-dark w-100 py-2">Login to Dashboard</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

# ৫. ড্যাশবোর্ড (সেটিংস, লিংক লিস্ট, API কী)
DASHBOARD_HTML = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Admin Dashboard</h2>
    <span class="badge bg-primary fs-6">Status: Active</span>
</div>

<!-- পরিসংখ্যান (Stats) -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card p-4 bg-primary text-white border-0 shadow-sm mb-3">
            <h3>{{ stats.links }}</h3>
            <span>Total Links Created</span>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card p-4 bg-success text-white border-0 shadow-sm mb-3">
            <h3>{{ stats.clicks }}</h3>
            <span>Total Clicks / Views</span>
        </div>
    </div>
</div>

<!-- ট্যাবস -->
<ul class="nav nav-tabs mb-3" id="adminTab" role="tablist">
    <li class="nav-item">
        <button class="nav-link active fw-bold" data-bs-toggle="tab" data-bs-target="#settings">⚙️ Settings</button>
    </li>
    <li class="nav-item">
        <button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#links">🔗 All Links</button>
    </li>
    <li class="nav-item">
        <button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#api">🔑 API Keys</button>
    </li>
</ul>

<div class="tab-content">
    
    <!-- সেটিংস ট্যাব -->
    <div class="tab-pane fade show active" id="settings">
        <div class="main-card pt-4">
            <h4 class="mb-4">Website Configuration</h4>
            <form method="POST">
                <input type="hidden" name="update_settings" value="1">
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label fw-bold">Website Name</label>
                        <input type="text" name="site_name" class="form-control" value="{{ config.site_name }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label fw-bold text-danger">Redirect Pages (Steps)</label>
                        <select name="total_pages" class="form-select">
                            <option value="0" {% if config.total_pages==0 %}selected{% endif %}>0 Page (Direct Redirect)</option>
                            <option value="1" {% if config.total_pages==1 %}selected{% endif %}>1 Page (Standard - 5s)</option>
                            <option value="2" {% if config.total_pages==2 %}selected{% endif %}>2 Pages (Double Ads)</option>
                            <option value="3" {% if config.total_pages==3 %}selected{% endif %}>3 Pages (Max Revenue)</option>
                        </select>
                        <small class="text-muted">User will see this many pages before reaching the final link.</small>
                    </div>
                </div>
                
                <hr class="my-4">
                <h5 class="mb-3 text-primary">Advertisement Codes (HTML/JS)</h5>
                
                <div class="mb-3">
                    <label class="fw-bold">Header Ad (Top)</label>
                    <textarea name="ad_header" class="form-control" rows="3" placeholder="Paste ad code here...">{{ config.ad_header }}</textarea>
                </div>
                <div class="mb-3">
                    <label class="fw-bold">Middle Ad (Near Timer)</label>
                    <textarea name="ad_middle" class="form-control" rows="3" placeholder="Paste ad code here...">{{ config.ad_middle }}</textarea>
                </div>
                <div class="mb-3">
                    <label class="fw-bold">Footer Ad (Bottom)</label>
                    <textarea name="ad_footer" class="form-control" rows="3" placeholder="Paste ad code here...">{{ config.ad_footer }}</textarea>
                </div>
                
                <button type="submit" class="btn btn-primary px-5 fw-bold">Save All Settings</button>
            </form>
        </div>
    </div>

    <!-- লিংক ট্যাব -->
    <div class="tab-pane fade" id="links">
        <div class="main-card p-0 overflow-auto" style="max-height: 600px;">
            <table class="table table-hover table-striped mb-0">
                <thead class="table-dark sticky-top">
                    <tr>
                        <th>Original URL</th>
                        <th>Short Code</th>
                        <th>Clicks</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {% for link in links %}
                    <tr>
                        <td class="text-truncate" style="max-width:300px;">
                            <a href="{{ link.original_url }}" target="_blank" class="text-decoration-none">{{ link.original_url }}</a>
                        </td>
                        <td>
                            <a href="/{{ link.short_code }}" target="_blank" class="fw-bold text-success">{{ link.short_code }}</a>
                        </td>
                        <td><span class="badge bg-secondary">{{ link.clicks }}</span></td>
                        <td><small>{{ link.created_at.strftime('%Y-%m-%d') }}</small></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- API কী ট্যাব -->
    <div class="tab-pane fade" id="api">
        <div class="main-card mb-4">
            <h5>Generate New API Key</h5>
            <p class="text-muted">Use this key in your Telegram Bot or external apps.</p>
            <form method="POST" class="d-flex gap-2">
                <input type="hidden" name="create_api" value="1">
                <input type="text" name="label" class="form-control" placeholder="Key Label (e.g. My Bot)" required>
                <button class="btn btn-dark fw-bold">Generate Key</button>
            </form>
        </div>
        
        <div class="list-group">
            {% for api in api_keys %}
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-0 fw-bold">{{ api.label }}</h6>
                    <code class="text-primary fs-5 user-select-all">{{ api.key }}</code>
                </div>
                <span class="badge bg-success">Active</span>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

# HTML টেমপ্লেট লোড করা
TEMPLATES = {
    'base': BASE_HTML,
    'index': HOME_HTML,
    'redirect': REDIRECT_HTML,
    'login': LOGIN_HTML,
    'dashboard': DASHBOARD_HTML
}

app.jinja_loader = DictLoader(TEMPLATES)


# ========================================================
# 🛠️ লজিক এবং ফাংশনস
# ========================================================

def get_settings():
    """ডাটাবেস থেকে সেটিংস লোড করে"""
    try:
        if not mongo: return {'site_name': 'Error', 'total_pages': 0}
        settings = mongo.db.settings.find_one({'_id': 'site_config'})
        
        # যদি সেটিংস না থাকে, ডিফল্ট তৈরি করো
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
    """লগইন চেক করার ডেকোরেটর"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# সব টেমপ্লেটে কনফিগারেশন পাঠানো
@app.context_processor
def inject_conf():
    return dict(config=get_settings())

# ========================================================
# 🌐 রাউটস (ওয়েবসাইট কন্ট্রোল)
# ========================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """হোমপেজ এবং লিংক শর্ট করার লজিক"""
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
        elif not mongo:
            flash("Database Connection Failed!", "danger")
            
    return render_template_string(TEMPLATES['index'], short_url=short_url)

@app.route('/<short_code>')
def redirect_logic(short_code):
    """মাল্টি-পেজ রিডাইরেকশন লজিক"""
    if not mongo: return "Database Error", 500
    
    link = mongo.db.links.find_one_or_404({'short_code': short_code})
    settings = get_settings()
    current_page = request.args.get('p', 1, type=int)
    total_steps = settings.get('total_pages', 1)

    # যদি 0 পেজ সেট করা থাকে, সরাসরি রিডাইরেক্ট
    if total_steps == 0:
        mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
        return redirect(link['original_url'])

    # যদি পেজ স্টেপ বাকি থাকে, টাইমার পেজ দেখাও
    if current_page <= total_steps:
        return render_template_string(TEMPLATES['redirect'], 
                                      link=link, 
                                      current_page=current_page, 
                                      total_steps=total_steps)
    
    # সব ধাপ শেষ, আসল লিংকে পাঠাও
    mongo.db.links.update_one({'_id': link['_id']}, {'$inc': {'clicks': 1}})
    return redirect(link['original_url'])

# ========================================================
# 🔥 স্মার্ট API (বটের জন্য)
# ========================================================

@app.route('/api/quick', methods=['GET'])
def api_quick():
    """
    বট বা স্ক্রিপ্টের জন্য সহজ API
    ব্যবহার: /api/quick?key=API_KEY&url=LONG_LINK
    """
    key = request.args.get('key')
    url = request.args.get('url')

    if not mongo: return jsonify({'error': 'DB Connection Failed'}), 500
    if not key or not url: return jsonify({'error': 'Missing key or url parameter'}), 400

    # API Key ভেরিফাই
    if not mongo.db.api_keys.find_one({'key': key}):
        return jsonify({'error': 'Invalid API Key'}), 401

    # লিংক সেভ করা
    try:
        code = generate_code()
        mongo.db.links.insert_one({
            'original_url': url,
            'short_code': code,
            'clicks': 0,
            'created_at': datetime.utcnow()
        })
        
        return jsonify({
            'status': 'success',
            'short_url': request.host_url + code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================================
# 🔒 অ্যাডমিন প্যানেল
# ========================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if not mongo: return "Database Error"

    # প্রথমবার অটোমেটিক অ্যাডমিন তৈরি (User: admin, Pass: 123456)
    if mongo.db.users.count_documents({'username': 'admin'}) == 0:
        mongo.db.users.insert_one({
            'username': 'admin', 
            'password': generate_password_hash('123456')
        })

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
    if request.method == 'POST':
        # সেটিংস আপডেট লজিক
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
        
        # নতুন API Key তৈরি লজিক
        elif 'create_api' in request.form:
            key = "API-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            mongo.db.api_keys.insert_one({
                'key': key, 
                'label': request.form.get('label'), 
                'created_at': datetime.utcnow()
            })
            flash('New API Key Generated!', 'success')

    # ড্যাশবোর্ডের জন্য ডাটা লোড
    links = list(mongo.db.links.find().sort('created_at', -1).limit(50))
    api_keys = list(mongo.db.api_keys.find())
    
    # পরিসংখ্যান
    total_links = mongo.db.links.count_documents({})
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$clicks"}}}]
    res = list(mongo.db.links.aggregate(pipeline))
    total_clicks = res[0]['total'] if res else 0

    return render_template_string(TEMPLATES['dashboard'], 
                                  links=links, 
                                  api_keys=api_keys, 
                                  stats={'links': total_links, 'clicks': total_clicks})

if __name__ == '__main__':
    # সার্ভার রান করা
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
