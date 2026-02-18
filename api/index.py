from flask import Flask, jsonify, request, render_template_string
import json
import os
import datetime
import uuid
from functools import wraps

app = Flask(__name__)

# ==========================================
# ตั้งค่าระบบ
# ==========================================
# ไฟล์ Database จะถูกสร้างที่โฟลเดอร์หลัก (ถอยออกมา 1 ชั้นจากโฟลเดอร์ api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'database.json')

# !!! รหัสผ่านเข้าหน้า Admin (เปลี่ยนได้) !!!
ADMIN_SECRET = "brx_admin_password" 

# ==========================================
# ระบบจัดการ Database (JSON)
# ==========================================
def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {"keys": {}}
        with open(DB_FILE, 'w') as f:
            json.dump(default_db, f)
        return default_db
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"keys": {}}

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except:
        return False

# ==========================================
# หน้าเว็บ ADMIN DASHBOARD (HTML)
# ==========================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BRX Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <style>body{background-color:#0f172a;color:#e2e8f0;font-family:sans-serif}.glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1)}</style>
</head>
<body class="p-6">
    <div id="loginModal" class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center">
        <div class="bg-slate-800 p-8 rounded-xl w-96 text-center border border-slate-700">
            <h2 class="text-2xl font-bold mb-4 text-red-500">ADMIN LOGIN</h2>
            <input type="password" id="secretInput" class="w-full p-3 bg-slate-900 border border-slate-700 rounded text-white mb-4" placeholder="Enter Secret Key">
            <button onclick="checkLogin()" class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 rounded">LOGIN</button>
        </div>
    </div>

    <div class="max-w-7xl mx-auto hidden" id="mainContent">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold text-red-500"><i class="fas fa-shield-alt"></i> BRX MANAGER</h1>
            <div>
                <button onclick="refreshData()" class="bg-slate-700 px-4 py-2 rounded mr-2"><i class="fas fa-sync"></i></button>
                <button onclick="logout()" class="bg-red-900 px-4 py-2 rounded text-red-200"><i class="fas fa-sign-out-alt"></i></button>
            </div>
        </div>

        <div class="glass p-6 rounded-xl mb-8 flex flex-col md:flex-row gap-4 justify-between items-center">
            <div class="flex gap-2 w-full md:w-1/2">
                <input type="text" id="genNote" placeholder="Note (User Name)" class="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2">
                <input type="number" id="genAmount" value="1" min="1" max="50" class="w-20 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-center">
                <button onclick="generateKeys()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded font-bold">GENERATE</button>
            </div>
            <div class="w-full md:w-1/3">
                 <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Search..." class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2">
            </div>
        </div>

        <div class="glass rounded-xl overflow-hidden overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead><tr class="bg-slate-800 text-slate-400 uppercase text-sm"><th class="p-4">Key</th><th class="p-4">Note</th><th class="p-4">HWID</th><th class="p-4">Status</th><th class="p-4 text-center">Actions</th></tr></thead>
                <tbody id="tableBody" class="text-sm divide-y divide-slate-800"></tbody>
            </table>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin + '/api';
        let AUTH_SECRET = localStorage.getItem('brx_secret');
        if(AUTH_SECRET) verifyToken();

        async function verifyToken() {
            const res = await fetch(`${API_URL}/admin/list`, { headers: { 'X-Admin-Secret': AUTH_SECRET } });
            if(res.ok) { document.getElementById('loginModal').classList.add('hidden'); document.getElementById('mainContent').classList.remove('hidden'); refreshData(); }
            else { document.getElementById('loginModal').classList.remove('hidden'); }
        }
        function checkLogin() { AUTH_SECRET = document.getElementById('secretInput').value; localStorage.setItem('brx_secret', AUTH_SECRET); verifyToken(); }
        function logout() { localStorage.removeItem('brx_secret'); location.reload(); }

        async function refreshData() {
            const res = await fetch(`${API_URL}/admin/list`, { headers: { 'X-Admin-Secret': AUTH_SECRET } });
            const data = await res.json();
            const tbody = document.getElementById('tableBody'); tbody.innerHTML = '';
            Object.entries(data.keys).reverse().forEach(([key, info]) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-4 font-mono text-yellow-500 select-all">${key}</td>
                    <td class="p-4 text-slate-300">${info.note || '-'}</td>
                    <td class="p-4 font-mono text-xs text-blue-300">${info.hwid ? info.hwid.substring(0,10)+'...' : 'Not Bound'}</td>
                    <td class="p-4"><span class="px-2 py-1 rounded text-xs font-bold ${info.is_banned ? 'bg-red-900 text-red-300':'bg-green-900 text-green-300'}">${info.is_banned ? 'BANNED':'ACTIVE'}</span></td>
                    <td class="p-4 flex gap-2 justify-center">
                        <button onclick="doAction('reset_hwid','${key}')" class="p-2 bg-slate-700 text-blue-400 rounded" title="Reset HWID"><i class="fas fa-laptop"></i></button>
                        <button onclick="doAction('${info.is_banned?'unban':'ban'}','${key}')" class="p-2 bg-slate-700 ${info.is_banned?'text-green-400':'text-orange-400'} rounded"><i class="fas ${info.is_banned?'fa-check':'fa-ban'}"></i></button>
                        <button onclick="doAction('delete','${key}')" class="p-2 bg-slate-700 text-red-400 rounded"><i class="fas fa-trash"></i></button>
                    </td>`;
                tbody.appendChild(tr);
            });
        }

        async function generateKeys() {
            const amount = document.getElementById('genAmount').value;
            const note = document.getElementById('genNote').value;
            await fetch(`${API_URL}/admin/create`, { method: 'POST', headers: {'Content-Type':'application/json','X-Admin-Secret':AUTH_SECRET}, body: JSON.stringify({amount, note}) });
            refreshData();
        }

        async function doAction(action, key) {
            if(!confirm('Are you sure?')) return;
            await fetch(`${API_URL}/admin/action`, { method: 'POST', headers: {'Content-Type':'application/json','X-Admin-Secret':AUTH_SECRET}, body: JSON.stringify({action, key}) });
            refreshData();
        }
        
        function filterTable() {
            const input = document.getElementById("searchInput").value.toUpperCase();
            const tr = document.getElementById("tableBody").getElementsByTagName("tr");
            for (let i = 0; i < tr.length; i++) {
                const text = tr[i].innerText;
                tr[i].style.display = text.toUpperCase().indexOf(input) > -1 ? "" : "none";
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# API ROUTES
# ==========================================
@app.route('/')
def home(): return jsonify({"status": "online", "admin": "/admin"})

@app.route('/admin')
def admin_page(): return render_template_string(ADMIN_HTML)

@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.json
    key, hwid = data.get('key'), data.get('hwid')
    db = load_db()
    
    if key not in db['keys']: return jsonify({"success": False, "message": "Invalid Key"}), 403
    info = db['keys'][key]
    
    if info['is_banned']: return jsonify({"success": False, "message": "Key Banned"}), 403
    
    if info['hwid'] is None:
        db['keys'][key]['hwid'] = hwid
        save_db(db)
        return jsonify({"success": True, "message": "Activated"})
    
    if info['hwid'] != hwid: return jsonify({"success": False, "message": "HWID Mismatch"}), 403
    
    return jsonify({"success": True, "message": "Valid"})

# --- ADMIN API ---
def auth_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-Admin-Secret') != ADMIN_SECRET: return jsonify({"success":False}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/admin/list', methods=['GET'])
@auth_admin
def list_keys(): return jsonify({"keys": load_db()['keys']})

@app.route('/api/admin/create', methods=['POST'])
@auth_admin
def create_key():
    data = request.json
    db = load_db()
    for _ in range(int(data.get('amount',1))):
        k = f"BRX-{str(uuid.uuid4()).upper()[:12]}"
        db['keys'][k] = {"hwid":None, "is_banned":False, "note":data.get('note',''), "created_at":str(datetime.datetime.now())}
    save_db(db)
    return jsonify({"success":True})

@app.route('/api/admin/action', methods=['POST'])
@auth_admin
def action_key():
    data = request.json
    act, key = data.get('action'), data.get('key')
    db = load_db()
    if key in db['keys']:
        if act == 'delete': del db['keys'][key]
        elif act == 'ban': db['keys'][key]['is_banned'] = True
        elif act == 'unban': db['keys'][key]['is_banned'] = False
        elif act == 'reset_hwid': db['keys'][key]['hwid'] = None
        save_db(db)
    return jsonify({"success":True})

if __name__ == '__main__':
    # รัน Server ที่ Port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
