"""JanSuno local API: citizen-controlled complaint drafts, never government submissions."""
import os
import sqlite3
import uuid
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

def local_path(name, default):
    p = Path(os.getenv(name, default))
    return p if p.is_absolute() else ROOT / p

DB_PATH = local_path('DATABASE_PATH', './jansuno.db')
UPLOAD_DIR = local_path('UPLOAD_DIR', './uploads')
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB', '5')) * 1024 * 1024
app = FastAPI(title='JanSuno Local API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(',') if s.strip()], allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['*'])
app.mount('/uploads', StaticFiles(directory=UPLOAD_DIR), name='uploads')

CATEGORIES = {'Roads & potholes', 'Garbage & sanitation', 'Water supply', 'Drainage & sewage', 'Street lighting', 'Other civic issue'}
PORTALS = {
    'Rajasthan': {'url': 'https://sampark.rajasthan.gov.in/', 'name': 'Rajasthan Sampark', 'scope': 'state', 'steps': 'Choose Lodge Grievance (शिकायत दर्ज करें) on the portal.'},
    'Delhi': {'url': 'https://pgms.delhi.gov.in/', 'name': 'Delhi PGMS', 'scope': 'state', 'steps': 'Choose Lodge Grievance.'},
    'Uttar Pradesh': {'url': 'https://jansunwai.up.nic.in/', 'name': 'UP Jansunwai', 'scope': 'state', 'steps': 'Choose शिकायत पंजीकरण / Register Grievance and complete mobile verification.'},
    'Bihar': {'url': 'https://lokshikayat.bihar.gov.in/', 'name': 'Bihar Lok Shikayat', 'scope': 'state', 'steps': 'Choose नया परिवाद दर्ज करें / Register a new grievance.'}
}
CENTRAL_PORTAL = {'url': 'https://pgportal.gov.in/', 'name': 'CPGRAMS — Central Grievance Portal', 'scope': 'general', 'steps': 'Verify this authority handles your issue before submitting. Local municipal complaints may require your city authority.'}
JAIPUR_PORTAL = {'url': 'https://samadhan.jaipurmc.org/ComplaintRegistrationByWebsite/', 'name': 'Jaipur Nagar Nigam — Register Complaint', 'scope': 'municipal', 'steps': 'Choose Register Complain, fill required fields and submit on the municipal site.'}
LOCAL_CATEGORIES = {'Roads & potholes', 'Garbage & sanitation', 'Water supply', 'Drainage & sewage', 'Street lighting', 'Other civic issue'}

def select_portal(state: str, city: str, category: str):
    city_name = city.strip().casefold().replace(' ', '')
    if state.strip().casefold() == 'rajasthan' and city_name in {'jaipur', 'जयपुर'} and category in LOCAL_CATEGORIES:
        return JAIPUR_PORTAL.copy()
    return (PORTALS.get(state) or CENTRAL_PORTAL).copy()

@app.get('/api/portal')
def portal_lookup(state: str = Query(...), city: str = Query(''), category: str = Query('Other civic issue')):
    return select_portal(state, city, category)

@app.get('/api/reverse-geocode')
def reverse_geocode(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    # Explicit location lookup, only on user click. Does not store or automatically track users.
    url = f'https://nominatim.openstreetmap.org/reverse?format=jsonv2&addressdetails=1&zoom=18&lat={lat:.7f}&lon={lon:.7f}'
    req = Request(url, headers={'User-Agent': 'JanSunoLocal/1.1 (local civic complaint drafting application)', 'Accept-Language': 'en'})
    try:
        with urlopen(req, timeout=10) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(503, 'Address lookup unavailable. GPS coordinates were captured; please enter state/city manually.') from exc
    address = data.get('address') or {}
    # Nominatim admin level 4 usually represents Indian state; state_district is NOT the state.
    state = address.get('state') or address.get('union_territory') or ''
    aliases = {'NCT of Delhi': 'Delhi', 'National Capital Territory of Delhi': 'Delhi', 'Orissa': 'Odisha', 'Uttaranchal': 'Uttarakhand'}
    state = aliases.get(state, state)
    city = next((address[k] for k in ('city','town','municipality','city_district','village','suburb') if address.get(k)), '')
    landmark = ', '.join(str(address[k]) for k in ('road','neighbourhood','suburb') if address.get(k))
    return {'state': state, 'city': city, 'landmark': landmark, 'display_name': data.get('display_name',''), 'source': 'OpenStreetMap Nominatim', 'latitude': lat, 'longitude': lon}


def connect():
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    return cx

with connect() as c:
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, state TEXT NOT NULL, city TEXT NOT NULL, landmark TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, latitude REAL, longitude REAL, photo_path TEXT, status TEXT NOT NULL DEFAULT 'Draft', portal_url TEXT NOT NULL)''')

class StatusUpdate(BaseModel):
    status: Literal['Draft', 'Ready to submit', 'Submitted externally', 'Resolved']


def as_payload(row):
    r = dict(row)
    r['photo_url'] = '/uploads/' + r['photo_path'] if r['photo_path'] else None
    return r

@app.get('/api/health')
def health():
    return {'ok': True, 'mode': 'local', 'government_submission': False}

@app.get('/api/complaints')
def list_complaints():
    with connect() as c:
        return [as_payload(r) for r in c.execute('SELECT * FROM complaints ORDER BY created_at DESC')]

@app.get('/api/complaints/{complaint_id}')
def get_complaint(complaint_id: str):
    with connect() as c:
        r = c.execute('SELECT * FROM complaints WHERE id=?', (complaint_id,)).fetchone()
    if not r: raise HTTPException(404, 'Complaint not found')
    return as_payload(r)

@app.post('/api/complaints', status_code=201)
async def create_complaint(
    state: str = Form(...), city: str = Form(...), landmark: str = Form(''),
    category: str = Form(...), description: str = Form(''),
    latitude: float | None = Form(None), longitude: float | None = Form(None),
    photo: UploadFile | None = File(None)
):
    state, city, landmark, description = [v.strip() for v in (state, city, landmark, description)]
    if not state or not city: raise HTTPException(422, 'State and city are required')
    if category not in CATEGORIES: raise HTTPException(422, 'Unknown issue category')
    if any(len(s) > limit for s, limit in [(state, 120), (city, 120), (landmark, 250), (description, 2000)]): raise HTTPException(422, 'Field too long')
    if latitude is not None and not (-90 <= latitude <= 90): raise HTTPException(422, 'Invalid latitude')
    if longitude is not None and not (-180 <= longitude <= 180): raise HTTPException(422, 'Invalid longitude')
    stored = None
    if photo and photo.filename:
        content = await photo.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES: raise HTTPException(413, 'Photo must be 5 MB or less')
        signatures = [(b'\xff\xd8\xff', '.jpg'), (b'\x89PNG\r\n\x1a\n', '.png'), (b'RIFF', '.webp')]
        extension = next((ext for sig, ext in signatures if content.startswith(sig)), None)
        if extension == '.webp' and content[8:12] != b'WEBP': extension = None
        if not extension: raise HTTPException(415, 'Use a JPG, PNG, or WebP photo')
        stored = f'{uuid.uuid4().hex}{extension}'
        (UPLOAD_DIR / stored).write_bytes(content)
    now = datetime.now(timezone.utc).isoformat()
    complaint_id = 'JS-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:6].upper()
    portal = select_portal(state, city, category)['url']
    with connect() as c:
        c.execute('''INSERT INTO complaints (id,created_at,updated_at,state,city,landmark,category,description,latitude,longitude,photo_path,status,portal_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (complaint_id, now, now, state, city, landmark, category, description, latitude, longitude, stored, 'Draft', portal))
        r = c.execute('SELECT * FROM complaints WHERE id=?', (complaint_id,)).fetchone()
    return as_payload(r)

@app.patch('/api/complaints/{complaint_id}/status')
def update_status(complaint_id: str, patch: StatusUpdate):
    with connect() as c:
        result = c.execute('UPDATE complaints SET status=?,updated_at=? WHERE id=?', (patch.status, datetime.now(timezone.utc).isoformat(), complaint_id))
        if result.rowcount == 0: raise HTTPException(404, 'Complaint not found')
        r = c.execute('SELECT * FROM complaints WHERE id=?', (complaint_id,)).fetchone()
    return as_payload(r)

@app.get('/api/complaints/{complaint_id}/draft')
def draft(complaint_id: str, lang: Literal['en', 'hi'] = 'en'):
    data = get_complaint(complaint_id)
    where = f"{data['landmark']}, {data['city']}, {data['state']}" if data['landmark'] else f"{data['city']}, {data['state']}"
    category = data['category']
    details = data['description'] or ('The problem is affecting local residents and requires attention.' if lang == 'en' else 'यह समस्या स्थानीय निवासियों को प्रभावित कर रही है।')
    if lang == 'hi':
        title = f'{where} में {category} की समस्या के संबंध में शिकायत'
        body = f'सेवा में,\nसंबंधित अधिकारी महोदय/महोदया,\n\nविषय: {title}\n\nमैं आपके संज्ञान में {where} में {category} से संबंधित एक नागरिक समस्या लाना चाहता/चाहती हूँ।\n\nसमस्या का विवरण: {details}\n\nकृपया इस मामले की जांच कर उचित कार्रवाई करें। यदि आवश्यक हो, तो संलग्न फोटो का संदर्भ लें।\n\nधन्यवाद,\nएक चिंतित नागरिक'
    else:
        title = f'Civic complaint regarding {category.lower()} in {where}'
        body = f'To,\nThe Concerned Civic Authority\n\nSubject: {title}\n\nI would like to bring to your attention a civic issue concerning {category.lower()} at {where}.\n\nIssue details: {details}\n\nI request the relevant department to inspect the issue and take appropriate corrective action. A supporting photograph is available if required.\n\nThank you,\nA concerned resident'
    portal = select_portal(data['state'], data['city'], data['category'])
    return {'title': title, 'body': body, 'portal_url': portal['url'], 'portal': portal, 'disclaimer': 'JanSuno does not submit to a government authority. Open the portal, sign in, and submit yourself.'}
