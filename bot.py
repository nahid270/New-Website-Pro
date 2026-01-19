import os
import random
import string
import requests
import certifi
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
# নিরাপদ সেশন কি
app.secret_key = os.environ.get("SECRET_KEY", "ultimate_premium_key_2026")

# ========================================================
# ⚙️ ডাটাবেস এবং কনফিগারেশন
# ========================================================

# আপনার MongoDB লিংক
MONGO_URI = "mongodb+srv://MoviaXBot3:MoviaXBot3@cluster0.ictlkq8.mongodb.net/shortener_db?retryWrites=true&w=majority&appName=Cluster0"

# ডাটাবেস কানেকশন (SSL ফিক্স সহ)
try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['shortener_db']
    urls_col = db['urls']
    settings_col = db['settings']
    channels_col = db['channels']
    otp_col = db['otps']
    print("✅ MongoDB Connected Successfully (Premium Mode)")
except Exception as e:
    print(f"❌ Database Error: {e}")

# টেলিগ্রাম সেটিংস (পাসওয়ার্ড রিকভারির জন্য)
TELEGRAM_BOT_TOKEN = "8469682967:AAEWrNWBWjiYT3_L47Xe_byORfD6IIsFD34"

# --- থিম কালার ম্যাপ (ডিজাইন অপশন) ---
COLOR_MAP = {
    "red": {"text": "text-red-500", "bg": "bg-red-600", "border": "border-red-500", "hover": "hover:bg-red-700", "light_bg": "bg-red-50"},
    "blue": {"text": "text-blue-500", "bg": "bg-blue-600", "border": "border-blue-500", "hover": "hover:bg-blue-700", "light_bg": "bg-blue-50"},
    "green": {"text": "text-green-500", "bg": "bg-green-600", "border": "border-green-500", "hover": "hover:bg-green-700", "light_bg": "bg-green-50"},
    "purple": {"text": "text-purple-500", "bg": "bg-purple-600", "border": "border-purple-500", "hover": "hover:bg-purple-700", "light_bg": "bg-purple-50"},
    "sky": {"text": "text-sky-400", "bg": "bg-sky-500", "border": "border-sky-400", "hover": "hover:bg-sky-600", "light_bg": "bg-sky-50"}
}

# ========================================================
# 🛠️ হেল্পার ফাংশন
# ========================================================

def get_settings():
    """ডাটাবেস থেকে সেটিংস আনে, না থাকলে ডিফল্ট তৈরি করে"""
    settings = settings_col.find_one()
    if not settings:
        default_settings = {
            "site_name": "Premium URL Shortener",
            "admin_telegram_id": "", 
            "steps": 1,
            "timer_seconds": 10,
            "admin_password": generate_password_hash("admin123"),
            # ডিফল্ট API Key তৈরি
            "api_key": ''.join(random.choices(string.ascii_uppercase + string.digits, k=16)),
            "popunder": "", "banner": "", "social_bar": "", "native": "",
            "direct_link": "https://google.com", 
            "direct_click_limit": 1,
            "main_theme": "sky", "step_theme": "blue"
        }
        settings_col.insert_one(default_settings)
        return default_settings
    return settings

def is_logged_in():
    return session.get('logged_in')

def get_channels_html(theme_color="sky"):
    """হোমপেজে চ্যানেল লিস্ট দেখানোর ফাংশন"""
    channels = list(channels_col.find())
    if not channels: return ""
    c = COLOR_MAP.get(theme_color, COLOR_MAP['sky'])
    html = f'''<div class="w-full max-w-5xl mx-auto mt-12 mb-8 p-8 rounded-[40px] border-2 border-white/10 glass shadow-2xl">
        <h3 class="text-center {c['text']} font-black mb-10 uppercase tracking-[0.3em] text-lg">Partner Channels</h3>
        <div class="flex flex-col items-center gap-10">'''
    for ch in channels:
        html += f'''<a href="{ch['link']}" target="_blank" class="flex flex-col items-center gap-3 group transition-transform hover:scale-105">
            <div class="text-center"><p class="text-lg font-black text-gray-100 uppercase italic tracking-wider">{ch.get('name', 'Join Our Channel')}</p></div>
            <img src="{ch['logo']}" style="width: 320px; height: 180px;" class="object-cover border-2 border-white/10 rounded-lg group-hover:border-white/40 shadow-2xl transition">
        </a>'''
    return html + '</div></div>'

# ========================================================
# 🔥 UNIVERSAL API SYSTEM (বটের সমস্যার সমাধান)
# ========================================================

def handle_api_request():
    """বট থেকে আসা রিকোয়েস্ট হ্যান্ডেল করে এবং JSON রিটার্ন করে"""
    settings = get_settings()
    
    # ১. প্যারামিটার ধরা (GET/POST)
    # বট 'api' বা 'key' দিয়ে API Key পাঠায়
    api_token = request.values.get('api') or request.values.get('key') or request.values.get('api_key')
    # বট 'url' বা 'link' দিয়ে লিংক পাঠায়
    long_url = request.values.get('url') or request.values.get('link')

    # ২. এরর হ্যান্ডলিং
    if not api_token or not long_url:
        return jsonify({"status": "error", "message": "Missing API Key or URL"}), 400

    # ৩. API Key যাচাই
    stored_token = settings.get('api_key', '')
    if api_token.strip() != stored_token.strip():
        return jsonify({"status": "error", "message": "Invalid API Key"}), 401
    
    # ৪. লিংক তৈরি এবং ডাটাবেসে সেভ
    short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    urls_col.insert_one({
        "long_url": long_url, 
        "short_code": short_code, 
        "clicks": 0, 
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "type": "api"
    })
    
    shortened_url = request.host_url + short_code
    
    # ৫. সঠিক রেসপন্স (AdLinkFly Standard)
    # টেলিগ্রাম বট 'shortenedUrl' খোঁজে
    return jsonify({
        "status": "success", 
        "shortenedUrl": shortened_url, # বটের জন্য জরুরি
        "short_url": shortened_url
    })

# ========================================================
# 🌐 রাউটস (ROUTES)
# ========================================================

# ১. হোমপেজ (এখানে API চেক এবং ওয়েবসাইট দুটোই হ্যান্ডেল করা হয়)
@app.route('/', methods=['GET', 'POST'])
def index():
    # যদি URL এ ?api=... থাকে, তাহলে এটি API হিসেবে কাজ করবে
    if (request.values.get('api') or request.values.get('key')) and (request.values.get('url') or request.values.get('link')):
        return handle_api_request()

    # অন্যথায় সাধারণ ওয়েবসাইট দেখাবে
    settings = get_settings()
    c = COLOR_MAP.get(settings.get('main_theme', 'sky'), COLOR_MAP['sky'])
    
    return render_template_string(f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><script src="https://cdn.tailwindcss.com"></script><title>{settings['site_name']}</title><style>body {{ background: #0f172a; color: white; }} .glass {{ background: rgba(255,255,255,0.03); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); }}</style></head><body class="min-h-screen flex flex-col items-center justify-center p-6 text-center"><h1 class="text-7xl md:text-9xl font-black mb-6 {c['text']} italic tracking-tighter uppercase">{settings['site_name']}</h1><p class="text-gray-200 mb-14 text-2xl md:text-4xl font-black uppercase tracking-widest">Fast • Secure • Premium</p><div class="glass p-5 rounded-[50px] w-full max-w-4xl shadow-3xl"><form action="/shorten" method="POST" class="flex flex-col md:flex-row gap-4"><input type="url" name="long_url" placeholder="PASTE YOUR LONG LINK HERE..." required class="flex-1 bg-transparent p-6 outline-none text-white text-2xl font-black placeholder:text-gray-500"><button type="submit" class="{c['bg']} text-white px-14 py-6 rounded-[40px] font-black text-3xl hover:scale-105 transition uppercase tracking-tighter shadow-2xl">Shorten</button></form></div>{get_channels_html(settings.get('main_theme', 'sky'))}</body></html>''')

# ২. ডেডিকেটেড API রাউট
@app.route('/api', methods=['GET', 'POST'])
def api_system():
    return handle_api_request()

# ৩. ওয়েব থেকে লিংক শর্ট করা
@app.route('/shorten', methods=['POST'])
def web_shorten():
    settings = get_settings()
    c = COLOR_MAP.get(settings.get('main_theme', 'sky'), COLOR_MAP['sky'])
    long_url = request.form.get('long_url')
    sc = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    urls_col.insert_one({"long_url": long_url, "short_code": sc, "clicks": 0, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "web"})
    return render_template_string(f'''<html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-slate-900 flex flex-col items-center justify-center min-h-screen p-4 text-white"><div class="bg-slate-800 p-16 rounded-[60px] shadow-2xl text-center max-w-2xl w-full border border-slate-700"><h2 class="text-5xl font-black mb-10 {c['text']} uppercase italic">Link Created!</h2><input id="shortUrl" value="{request.host_url + sc}" readonly class="w-full bg-slate-900 p-8 rounded-3xl border border-slate-700 {c['text']} font-black text-center mb-10 text-3xl"><button onclick="copyLink()" id="copyBtn" class="w-full {c['bg']} text-white py-8 rounded-[40px] font-black text-4xl uppercase tracking-tighter transition shadow-2xl">COPY LINK</button><a href="/" class="block mt-10 text-slate-500 font-black uppercase text-sm hover:text-white transition">Shorten Another</a></div><script>function copyLink() {{ var copyText = document.getElementById("shortUrl"); copyText.select(); navigator.clipboard.writeText(copyText.value); document.getElementById("copyBtn").innerText = "COPIED!"; }}</script></body></html>''')

# ৪. রিডাইরেকশন লজিক (Multi-step + Ads)
@app.route('/<short_code>')
def handle_ad_steps(short_code):
    step = int(request.args.get('step', 1))
    settings = get_settings()
    url_data = urls_col.find_one({"short_code": short_code})
    
    if not url_data: return "404 - Link Not Found", 404
    
    # স্টেপ শেষ হলে রিডাইরেক্ট
    if step > settings['steps']:
        urls_col.update_one({"short_code": short_code}, {"$inc": {"clicks": 1}})
        return redirect(url_data['long_url'])
    
    tc = COLOR_MAP.get(settings.get('step_theme', 'blue'), COLOR_MAP['blue'])
    
    # রিডাইরেক্ট পেজ HTML
    return render_template_string(f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><script src="https://cdn.tailwindcss.com"></script>
    {settings['popunder']} {settings['social_bar']}
    </head>
    <body class="bg-slate-50 flex flex-col items-center p-6 min-h-screen">
        <div class="mb-6">{settings['banner']}</div>
        <div class="bg-white p-12 md:p-20 rounded-[70px] shadow-3xl text-center max-w-2xl w-full border-t-[16px] {tc['border']} my-4">
            <p class="text-xl md:text-2xl font-black {tc['text']} uppercase tracking-widest mb-4">Step {step} of {settings['steps']}</p>
            <h2 class="text-3xl md:text-5xl font-black text-slate-900 mb-8 tracking-tighter italic">Verifying Status...</h2>
            
            <div id="timer_box" class="text-7xl md:text-8xl font-black {tc['text']} mb-8 {tc['light_bg']} w-40 h-40 md:w-48 md:h-48 flex items-center justify-center rounded-full mx-auto border-8 {tc['border']} italic shadow-inner">{settings['timer_seconds']}</div>
            
            <button id="main_btn" onclick="handleClick()" class="hidden w-full {tc['bg']} text-white py-8 rounded-[40px] font-black text-3xl uppercase shadow-2xl transition hover:scale-105">Continue</button>
        </div>
        <div class="mt-4">{settings['native']}</div>
        {get_channels_html(settings.get('step_theme', 'blue'))}
        
        <script>
            let timeLeft = {settings['timer_seconds']};
            let totalAdClicks = 0;
            let adLimit = {settings.get('direct_click_limit', 1)};
            let adUrl = "{settings['direct_link']}";
            
            const timerBox = document.getElementById('timer_box');
            const mainBtn = document.getElementById('main_btn');

            const countdown = setInterval(() => {{
                timeLeft--;
                timerBox.innerText = timeLeft;
                if(timeLeft <= 0) {{
                    clearInterval(countdown);
                    timerBox.style.display = 'none';
                    mainBtn.classList.remove('hidden');
                    refreshBtnText();
                }}
            }}, 1000);

            function refreshBtnText() {{
                if (totalAdClicks < adLimit && adUrl !== "") {{
                    mainBtn.innerText = "VERIFY (" + (totalAdClicks + 1) + "/" + adLimit + ")";
                }} else {{
                    mainBtn.innerText = "CONTINUE TO NEXT";
                }}
            }}

            function handleClick() {{
                if (totalAdClicks < adLimit && adUrl !== "") {{
                    window.open(adUrl, '_blank');
                    totalAdClicks++;
                    refreshBtnText();
                }} else {{
                    window.location.href = "/{short_code}?step={step + 1}";
                }}
            }}
        </script>
    </body></html>''')

# ========================================================
# 🔒 অ্যাডমিন প্যানেল
# ========================================================

@app.route('/admin')
def admin_panel():
    if not is_logged_in(): return redirect(url_for('login'))
    settings = get_settings()
    all_urls = list(urls_col.find().sort("_id", -1))
    total_clicks = sum(u.get('clicks', 0) for u in all_urls)
    channels = list(channels_col.find())
    theme_options = sorted(COLOR_MAP.keys())

    return render_template_string(f'''
    <html><head><script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap" rel="stylesheet">
    <style> body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #f8fafc; }} .active-tab {{ background: #1e293b !important; color: white !important; }} .tab-content {{ display: none; }} .tab-content.active {{ display: block; }} </style>
    </head>
    <body class="flex flex-col lg:flex-row min-h-screen">
        <div class="lg:w-72 bg-white border-r p-8 flex flex-col shadow-sm">
            <h2 class="text-2xl font-black text-slate-900 mb-12 italic tracking-tighter">PREMIUM <span class="text-blue-600">ADMIN</span></h2>
            <nav class="space-y-3 flex-1">
                <button onclick="showTab('overview')" id="tab-overview-btn" class="w-full text-left p-4 rounded-2xl font-bold text-slate-500 hover:bg-slate-100 transition flex items-center gap-3 active-tab">📊 Analytics</button>
                <button onclick="showTab('config')" id="tab-config-btn" class="w-full text-left p-4 rounded-2xl font-bold text-slate-500 hover:bg-slate-100 transition flex items-center gap-3">⚙️ Settings</button>
                <button onclick="showTab('partners')" id="tab-partners-btn" class="w-full text-left p-4 rounded-2xl font-bold text-slate-500 hover:bg-slate-100 transition flex items-center gap-3">📢 Channels</button>
            </nav>
            <a href="/logout" class="mt-10 p-4 bg-red-50 text-red-600 rounded-2xl text-center font-black uppercase text-xs tracking-widest hover:bg-red-100 transition">Logout</a>
        </div>
        <div class="flex-1 p-6 lg:p-12 overflow-y-auto">
            
            <!-- ANALYTICS -->
            <div id="overview" class="tab-content active space-y-10">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-white p-8 rounded-[40px] shadow-sm border border-slate-100">
                        <p class="text-slate-400 text-xs font-bold uppercase mb-1">Total Links</p>
                        <h3 class="text-5xl font-black text-slate-900">{len(all_urls)}</h3>
                    </div>
                    <div class="bg-blue-600 p-8 rounded-[40px] shadow-lg text-white">
                        <p class="text-blue-200 text-xs font-bold uppercase mb-1">Total Clicks</p>
                        <h3 class="text-5xl font-black">{total_clicks}</h3>
                    </div>
                </div>
            </div>

            <!-- SETTINGS -->
            <div id="config" class="tab-content space-y-8">
                <form action="/admin/update" method="POST" class="grid grid-cols-1 xl:grid-cols-2 gap-8">
                    <div class="bg-white p-10 rounded-[50px] shadow-sm border border-slate-100 space-y-6">
                        <h4 class="font-black text-xl text-slate-900">🎨 Design</h4>
                        <select name="main_theme" class="w-full p-4 bg-slate-50 rounded-2xl font-bold">{"".join([f'<option value="{o}" {"selected" if settings.get("main_theme")==o else ""}>{o.upper()}</option>' for o in theme_options])}</select>
                        <input type="text" name="site_name" value="{settings['site_name']}" class="w-full p-4 bg-slate-50 rounded-2xl font-black text-lg" placeholder="Site Name">
                        <input type="number" name="steps" value="{settings['steps']}" class="w-full p-4 bg-slate-50 rounded-2xl" placeholder="Ad Steps">
                        <input type="number" name="timer_seconds" value="{settings['timer_seconds']}" class="w-full p-4 bg-slate-50 rounded-2xl" placeholder="Timer Seconds">
                        
                        <h4 class="font-black text-xl text-slate-900 pt-4">🔑 API Key</h4>
                        <div class="bg-orange-50 p-6 rounded-[30px] border border-orange-100">
                            <input type="text" id="api_key_field" name="api_key" value="{settings['api_key']}" class="w-full p-4 bg-white rounded-xl font-mono text-xs border border-orange-200 outline-none">
                            <button type="button" onclick="generateAPI()" class="w-full mt-2 bg-orange-600 text-white p-3 rounded-xl text-xs font-black">REGENERATE</button>
                        </div>
                    </div>
                    <div class="bg-white p-10 rounded-[50px] shadow-sm border border-slate-100 space-y-4">
                        <h4 class="font-black text-xl text-emerald-600">💰 Ads Scripts</h4>
                        <textarea name="popunder" placeholder="Popunder Script" class="w-full h-20 p-4 bg-slate-50 rounded-2xl text-xs font-mono">{settings['popunder']}</textarea>
                        <textarea name="banner" placeholder="Banner Ad Script" class="w-full h-20 p-4 bg-slate-50 rounded-2xl text-xs font-mono">{settings['banner']}</textarea>
                        <textarea name="social_bar" placeholder="Social Bar Script" class="w-full h-20 p-4 bg-slate-50 rounded-2xl text-xs font-mono">{settings['social_bar']}</textarea>
                        <textarea name="native" placeholder="Native Script" class="w-full h-20 p-4 bg-slate-50 rounded-2xl text-xs font-mono">{settings['native']}</textarea>
                        <button class="w-full bg-slate-900 text-white p-6 rounded-[30px] font-black text-xl shadow-2xl hover:scale-[1.02] transition mt-4">Save All</button>
                    </div>
                </form>
            </div>

            <!-- PARTNERS -->
            <div id="partners" class="tab-content space-y-8">
                <div class="bg-white p-10 rounded-[50px] shadow-sm border border-slate-100">
                    <h4 class="font-black text-xl text-slate-900 mb-6">📢 Add Channel</h4>
                    <form action="/admin/add_channel" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
                        <input type="text" name="name" placeholder="Name" required class="w-full p-4 bg-slate-50 rounded-2xl border-none">
                        <input type="url" name="logo" placeholder="Banner URL" required class="w-full p-4 bg-slate-50 rounded-2xl border-none">
                        <input type="url" name="link" placeholder="Link" required class="w-full p-4 bg-slate-50 rounded-2xl border-none">
                        <button class="bg-blue-600 text-white p-4 rounded-2xl font-black uppercase">Add</button>
                    </form>
                    <div class="mt-12 space-y-8">
                        {" ".join([f'<div class="flex items-center gap-6 bg-slate-50 p-6 rounded-[30px] border border-slate-100"><p class="font-black flex-1">{c.get("name")}</p><a href="/admin/delete_channel/{c["_id"]}" class="bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-bold">Delete</a></div>' for c in channels])}
                    </div>
                </div>
            </div>
        </div>
        <script>
            function showTab(tabId) {{
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('nav button').forEach(b => b.classList.remove('active-tab'));
                document.getElementById(tabId).classList.add('active');
                document.getElementById('tab-' + tabId + '-btn').classList.add('active-tab');
            }}
            function generateAPI() {{
                const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
                let newKey = "";
                for (let i = 0; i < 20; i++) {{ newKey += chars.charAt(Math.floor(Math.random() * chars.length)); }}
                document.getElementById("api_key_field").value = newKey;
            }}
        </script>
    </body></html>
    ''')

# --- এডমিন অ্যাকশন ---
@app.route('/admin/add_channel', methods=['POST'])
def add_channel():
    if not is_logged_in(): return redirect(url_for('login'))
    name, logo, link = request.form.get('name'), request.form.get('logo'), request.form.get('link')
    if logo and link: channels_col.insert_one({"name": name, "logo": logo, "link": link})
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_channel/<id>')
def delete_channel(id):
    if not is_logged_in(): return redirect(url_for('login'))
    channels_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin_panel'))

@app.post('/admin/update')
def update_settings():
    if not is_logged_in(): return redirect(url_for('login'))
    d = {
        "site_name": request.form.get('site_name'),
        "steps": int(request.form.get('steps', 1)),
        "timer_seconds": int(request.form.get('timer_seconds', 10)),
        "popunder": request.form.get('popunder'),
        "banner": request.form.get('banner'),
        "social_bar": request.form.get('social_bar'),
        "native": request.form.get('native'),
        "main_theme": request.form.get('main_theme'),
        "api_key": request.form.get('api_key').strip()
    }
    settings_col.update_one({}, {"$set": d})
    return redirect(url_for('admin_panel'))

# --- লগইন ও পাসওয়ার্ড রিকভারি ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_password_hash(get_settings()['admin_password'], request.form.get('password')):
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        return "Access Denied!"
    return render_template_string('''<body style="background:#0f172a; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif;"><form method="POST" style="background:white; padding:50px; border-radius:40px; text-align:center;"><h2 style="font-weight:900;">ADMIN LOGIN</h2><input type="password" name="password" placeholder="Password" style="padding:15px; border-radius:15px; border:1px solid #eee; width:250px; display:block; margin-bottom:15px;"><button style="width:100%; padding:15px; background:#1e293b; color:white; border:none; border-radius:15px; font-weight:900;">UNLOCK</button></form></body>''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
