# JanSuno — Local Development Edition

A standalone Windows-friendly React + Vite frontend and FastAPI + SQLite backend. It does **not** require ChatGPT Sites hosting or any API keys.

## Requirements
- Windows 10/11, [Node.js LTS](https://nodejs.org/) (18+; 20+ recommended), Python 3.10+ (3.11/3.12 recommended), VS Code.
- Internet is needed for initial npm/pip installs and for opening government portals; the local app itself works without any external API.

## Quick start in VS Code (Windows PowerShell)
1. Extract the ZIP to a normal folder, open that folder in VS Code.
2. Open **Terminal > New Terminal**, run:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3. Open a **second** VS Code terminal:

```powershell
cd frontend
npm install
npm run dev
```

4. Open **http://127.0.0.1:5173**. Backend docs: **http://127.0.0.1:8000/docs**; health: **http://127.0.0.1:8000/api/health**.

**Alternative Windows shortcuts:** Double click `start-backend.bat` and `start-frontend.bat` in separate windows (after installing Python and Node). The backend script installs dependencies and creates `.venv` on its first run.

## Features
- Responsive JanSuno-inspired home, complaint form, explanation, saved complaints, and review screens.
- JPG/PNG/WebP optional upload (max 5 MB). Form requires state, city, and issue category.
- Optional GPS coordinates (user's browser permission), optional browser voice dictation (best in Chrome/Edge).
- English/Hindi interface and complaint draft. For more accurate government-ready Hindi, review and edit copied text manually.
- Local SQLite complaint IDs and local editable statuses; uploaded photos stored in `backend/uploads/`.
- Official portal links for Rajasthan, Delhi, Uttar Pradesh and Bihar, and CPGRAMS fallback for other states. **These are starting links, not verified jurisdiction routing.** Verify the correct authority on the official portal.

## IMPORTANT: what the application does NOT do
- Does not automatically lodge complaints, log in, transmit photos/text to a government portal, or track real government-case status.
- Does not analyze photo content with AI. Complaint drafts are templates based on selected category, location, and user description. This retains the source Sites MVP's explicitly labeled demo behavior.
- No account login or access control. **Run on localhost only.** Anyone with access to the local machine and database files may see stored complaint data and photos. Do not expose the backend to a public network without authentication and security hardening.
- This is a **reconstruction** based on the saved JanSuno Sites page content, not the original unpublished Sites source code. Exact styling and unavailable behavior may differ.

## Project structure
```
JanSuno-Local/
├── frontend/
│   ├── package.json, index.html, vite.config.js, .env.example
│   └── src/main.jsx, src/style.css
├── backend/
│   ├── requirements.txt, .env.example
│   └── app/__init__.py, app/main.py
├── start-backend.bat
├── start-frontend.bat
└── README.md
```

## Data, privacy and reset
- Do not upload confidential material: photos and complaint drafts are saved in plaintext on your PC.
- To reset local complaint history, stop FastAPI and delete `backend/jansuno.db` and uploaded files in `backend/uploads/`.
- `backend/.env` is local only; customize database and upload directories there.
- In development the Vite proxy forwards `/api` and `/uploads` to FastAPI on port 8000.
- When deploying elsewhere you must configure an API base URL and CORS properly; this package targets **local Windows development**.

## Useful troubleshooting
- `py` not recognized: install Python, select Add Python to PATH, or use `python` instead of `py`.
- `npm` not recognized: install Node.js LTS, then restart VS Code.
- PowerShell blocks virtual-env activation: the commands above invoke `python.exe` directly and do **not** require activation.
- Network request failed: confirm FastAPI is still running on 127.0.0.1:8000.
- Voice input unavailable: use Chrome/Edge and allow microphone access; type the details instead.
- GPS may be inaccurate or unavailable; manually enter state and city regardless.


## Location and precise complaint portal (v1.1)

- Run the site using **http://localhost:5173** on your own computer. Browsers permit geolocation on `localhost` or HTTPS, but usually not on `http://192.168.x.x`.
- Allow Location for `localhost` in browser permissions, and enable **Settings > Privacy & security > Location > Location services** on Windows. Desktop GPS may be approximate based on Wi-Fi/IP; check the result.
- Click **Use my location**. This captures coordinates, calls the local FastAPI `/api/reverse-geocode` endpoint, and attempts to fill state, city and nearby road. Address lookup uses OpenStreetMap Nominatim over the internet; it can fail or be rate-limited. It only runs after your click. Coordinates and proposed address should be reviewed before submitting.
- If it fails, manually enter State, City and Landmark. The form still works without GPS.
- The result page now shows the **named destination** and the selected complaint URL. Verified municipal direct page for Jaipur: `https://samadhan.jaipurmc.org/ComplaintRegistrationByWebsite/`. State portals: Rajasthan Sampark, Delhi PGMS, UP Jansunwai, Bihar Lok Shikayat. Others fall back to CPGRAMS, clearly labelled as general; this is NOT an assurance the portal handles municipal complaints.
- This is a directory of verified starting pages, not a fully exhaustive city-by-city registry. Official sites may change their URLs or require CAPTCHA/login/OTP. No complaint is directly submitted. Previously saved complaints use the updated dynamic portal recommendation in their draft view.
- API check: `http://127.0.0.1:8000/api/portal?state=Rajasthan&city=Jaipur&category=Roads%20%26%20potholes`.
