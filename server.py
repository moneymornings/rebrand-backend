from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import uuid
from datetime import datetime
import secrets

# Environment variables
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'money_mornings')

# MongoDB connection
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Money Mornings API")
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'MoneyMornings2025!')
    
    if not (secrets.compare_digest(credentials.username, admin_user) and 
            secrets.compare_digest(credentials.password, admin_pass)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

class ApplicationCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    business_name: Optional[str] = None
    service_interest: str
    funding_amount: Optional[str] = None
    time_in_business: Optional[str] = None

@app.get("/api/")
async def root():
    return {"message": "Money Mornings API - Ready!"}

@app.get("/api/applications")
async def get_applications():
    try:
        applications = await db.applications.find().to_list(100)
        
        # Convert ObjectId to string for JSON serialization
        for app in applications:
            if '_id' in app:
                app['_id'] = str(app['_id'])
        
        return applications
        
    except Exception as e:
        print(f"Error retrieving applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/applications/submit")
async def submit_application(app_data: ApplicationCreate):
    try:
        application = {
            "id": str(uuid.uuid4()),
            "first_name": app_data.first_name,
            "last_name": app_data.last_name,
            "email": app_data.email,
            "phone": app_data.phone,
            "business_name": app_data.business_name,
            "service_interest": app_data.service_interest,
            "funding_amount": app_data.funding_amount,
            "time_in_business": app_data.time_in_business,
            "submission_date": datetime.utcnow(),
            "status": "pending"
        }
        
        result = await db.applications.insert_one(application)
        return {"message": "Application submitted successfully", "id": application["id"]}
        
    except Exception as e:
        print(f"Error submitting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(username: str = Depends(verify_admin)):
    return """<!DOCTYPE html>
<html>
<head>
    <title>Money Mornings Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="max-w-6xl mx-auto p-6">
        <h1 class="text-3xl font-bold mb-6">Money Mornings Admin</h1>
        <div id="applications" class="bg-white p-6 rounded-lg shadow"></div>
    </div>
    <script>
        async function loadApplications() {
            try {
                const response = await fetch('/api/applications');
                const apps = await response.json();
                
                let html = '<h2 class="text-xl font-semibold mb-4">Applications</h2>';
                if (apps.length === 0) {
                    html += '<p>No applications yet.</p>';
                } else {
                    html += '<div class="space-y-4">';
                    apps.forEach(app => {
                        html += `
                            <div class="border p-4 rounded">
                                <h3 class="font-semibold">${app.first_name} ${app.last_name}</h3>
                                <p>Email: <a href="mailto:${app.email}" class="text-blue-600">${app.email}</a></p>
                                <p>Phone: ${app.phone}</p>
                                <p>Service: ${app.service_interest}</p>
                                <p>Status: <span class="bg-yellow-100 px-2 py-1 rounded">${app.status}</span></p>
                                <p>Date: ${new Date(app.submission_date).toLocaleDateString()}</p>
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                
                document.getElementById('applications').innerHTML = html;
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('applications').innerHTML = '<p class="text-red-500">Error loading applications</p>';
            }
        }
        
        loadApplications();
        setInterval(loadApplications, 30000);
    </script>
</body>
</html>"""

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
