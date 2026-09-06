"""RASDAD website and persistent API. Run: python server.py"""
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('RASDAD_DB', str(ROOT / 'data' / 'rasdad.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get('RASDAD_ADMIN_TOKEN') or secrets.token_urlsafe(32)

@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

with connect() as db:
    db.executescript('''
    CREATE TABLE IF NOT EXISTS visitors (id TEXT PRIMARY KEY, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, visitor TEXT UNIQUE NOT NULL, name TEXT NOT NULL, rating INTEGER NOT NULL, comment TEXT NOT NULL, created TEXT NOT NULL);
    ''')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def reply(self, status, data, cookie=None):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(raw)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN)

    def static_allowed(self):
        path = unquote(urlsplit(self.path).path)
        return path in ['/', '/index.html', '/packages.html', '/services.html', '/header.html', '/footer.html', '/admin.html'] or bool(re.fullmatch(r'/media/[\w-]+\.(png|css|js)', path))

    def do_HEAD(self):
        if not self.static_allowed():
            return self.send_error(404)
        super().do_HEAD()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/community':
            with connect() as db:
                count = db.execute('SELECT COUNT(*) FROM visitors').fetchone()[0]
                summary = db.execute('SELECT COUNT(*), AVG(rating) FROM reviews').fetchone()
                reviews = [dict(row) for row in db.execute('SELECT name,rating FROM reviews ORDER BY created DESC, id DESC LIMIT 50')]
            return self.reply(200, dict(visitors=count, count=summary[0], average=summary[1], reviews=reviews))
        if path == '/api/admin':
            if not self.authorized():
                return self.reply(401, {'error': 'غير مصرح'})
            with connect() as db:
                leads = [dict(row) for row in db.execute('SELECT * FROM leads ORDER BY id DESC')]
            for row in leads:
                row['data'] = json.loads(row['data'])
            return self.reply(200, {'leads': leads})
        if not self.static_allowed():
            return self.send_error(404)
        super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ['/api/visit', '/api/leads', '/api/reviews']:
            return self.reply(404, {'error': 'غير موجود'})
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.reply(403, {'error': 'مصدر غير مسموح'})
        try:
            if 'application/json' not in self.headers.get('Content-Type', ''):
                raise ValueError()
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 20000:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError()
            now = datetime.now(timezone.utc).isoformat()
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie', ''))
            visitor = cookies.get('rasdad_visitor')
            visitor = visitor.value if visitor else ''
            if not re.fullmatch(r'[a-f0-9]{64}', visitor):
                visitor = secrets.token_hex(32)
            with connect() as db:
                if path == '/api/visit':
                    db.execute('INSERT OR IGNORE INTO visitors VALUES (?,?)', (visitor, now))
                elif path == '/api/leads':
                    kind = data.get('kind')
                    required = ['name', 'phone', 'entity', 'type', 'description'] if kind == 'request' else ['name', 'email', 'message']
                    if kind not in ['request', 'inquiry'] or any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
                        raise ValueError()
                    if any(not isinstance(v, str) or len(v) > 5000 for k, v in data.items() if k != 'publicConsent'):
                        raise ValueError()
                    data.pop('publicConsent', None)
                    if len(data['name'].strip()) < 2 or len(data['name']) > 100:
                        raise ValueError()
                    if kind == 'request' and not re.fullmatch(r'(?:(?:00966|966|0)?5\d{8})', re.sub(r'[\s()+-]', '', data['phone'])):
                        raise ValueError()
                    if data.get('email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', data['email']):
                        raise ValueError()
                    db.execute('INSERT INTO leads(kind,data,created) VALUES (?,?,?)', (kind, json.dumps(data, ensure_ascii=False), now))
                else:
                    name, rating = data.get('name'), data.get('rating')
                    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 80 or type(rating) is not int or not 1 <= rating <= 5:
                        raise ValueError()
                    db.execute('INSERT OR IGNORE INTO visitors VALUES (?,?)', (visitor, now))
                    db.execute('INSERT INTO reviews(visitor,name,rating,comment,created) VALUES (?,?,?,?,?) ON CONFLICT(visitor) DO UPDATE SET name=excluded.name,rating=excluded.rating,comment=excluded.comment,created=excluded.created', (visitor, name.strip(), rating, '', now))
            secure = '; Secure' if origin and origin.startswith('https:') else ''
            return self.reply(200, {'ok': True}, f'rasdad_visitor={visitor}; HttpOnly; SameSite=Lax; Path=/; Max-Age=31536000{secure}')
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.reply(400, {'error': 'يرجى التحقق من البيانات المدخلة.'})
        except sqlite3.Error:
            return self.reply(503, {'error': 'تعذر الحفظ، حاول لاحقًا.'})

if __name__ == '__main__':
    print('Admin access key:', TOKEN, flush=True)
    print('RASDAD: http://127.0.0.1:8000 — admin: /admin.html', flush=True)
    ThreadingHTTPServer((os.environ.get('RASDAD_HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))), Handler).serve_forever()
