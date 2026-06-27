/* ===========================================================
   MAGIYA — frontend API configuration
   Base URL of the FastAPI dashboard service (see api/main.py in the
   magiya-backend repo), deployed publicly on Render.

   To run against a local backend instead while developing:
     uvicorn api.main:app --reload --port 8001
   and temporarily change the line below to 'http://localhost:8001'.
   =========================================================== */
const MAGIYA_API_BASE = 'https://magiya-api.onrender.com';
