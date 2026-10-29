# Deploy JanSuno frontend on Vercel

## 1. Test the frontend locally
Open `frontend/` in a terminal and run `npm install` and `npm run build`.

## 2. Push this project to a PRIVATE GitHub repository
In the project directory, use GitHub Desktop or Git (`git init`, `git add .`, `git commit -m "JanSuno deployment"`, then push it). Do not commit any real `.env` files or personal data.

## 3. Import on Vercel
At https://vercel.com/new import the repository.
- Framework: Vite
- Root Directory: `frontend`
- Build command: `npm run build`
- Output Directory: `dist`

## 4. Connect the backend
Deploy `backend/` separately as a Python web service, for example on Render. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Install: `pip install -r requirements.txt`. Configure its CORS_ORIGINS with your Vercel HTTPS origin. Set the Vercel frontend project environment variable `VITE_API_BASE_URL` to your backend's HTTPS base URL, and redeploy.

IMPORTANT: current backend uses SQLite and local disk photo storage. Ordinary ephemeral hosting is NOT sufficient for durable complaint data or photos. Replace with managed Postgres and object storage before production, or choose a backend host with persistent disk and configure DATABASE_PATH and UPLOAD_DIR accordingly. A public deployment should also add account-based authorization and spam protection because complaint history currently is not account-isolated.

GPS requires HTTPS and the visitor's browser permission; a desktop's location may be approximate.

If frontend-only deployed without a backend URL, the page loads but form/API actions do not work.
