from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import os
import uuid
from datetime import datetime
import secrets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'money_mornings')

# MongoDB connection
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Money Mornings API", version="1.0.0")
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials for dashboard access"""
    admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'MoneyMornings2025!')
    
    if not (secrets.compare_digest(credentials.username, admin_user) and 
            secrets.compare_digest(credentials.password, admin_pass)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

# Pydantic Models
class ApplicationCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    business_name: Optional[str] = None
    service_interest: str
    funding_amount: Optional[str] = None
    time_in_business: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    business_name: Optional[str] = None
    service_interest: str
    funding_amount: Optional[str] = None
    time_in_business: Optional[str] = None
    submission_date: datetime
    status: str

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

# API Routes
@app.get("/")
async def root():
    return {"message": "Money Mornings Empire API", "version": "1.0.0"}

@app.get("/api/")
async def api_root():
    return {"message": "Money Mornings API - Ready to serve!"}

@app.get("/api/applications")
async def get_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Number of applications to return"),
    skip: int = Query(0, description="Number of applications to skip")
):
    """Get all application submissions with optional filtering"""
    try:
        # Build query filter
        query_filter = {}
        if status:
            query_filter["status"] = status
        
        # Get applications from database
        cursor = db.applications.find(query_filter).sort("submission_date", -1).skip(skip).limit(limit)
        applications = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for app in applications:
            if '_id' in app:
                app['_id'] = str(app['_id'])
        
        logger.info(f"Retrieved {len(applications)} applications")
        return applications
        
    except Exception as e:
        logger.error(f"Error retrieving applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/applications/submit")
async def submit_application(app_data: ApplicationCreate):
    """Submit a new Money Mornings application"""
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
        logger.info(f"New application submitted: {application['email']}")
        
        return {
            "message": "Application submitted successfully", 
            "id": application["id"],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    """Get a specific application by ID"""
    try:
        application = await db.applications.find_one({"id": application_id})
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Convert ObjectId to string
        if '_id' in application:
            application['_id'] = str(application['_id'])
        
        return application
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving application {application_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/applications/{application_id}")
async def update_application(application_id: str, update_data: ApplicationUpdate):
    """Update application status and notes"""
    try:
        # Prepare update data
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        # Update the application
        result = await db.applications.update_one(
            {"id": application_id},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Return updated application
        updated_app = await db.applications.find_one({"id": application_id})
        if '_id' in updated_app:
            updated_app['_id'] = str(updated_app['_id'])
        
        return updated_app
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating application {application_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications/stats/summary")
async def get_application_stats():
    """Get application submission statistics"""
    try:
        total_applications = await db.applications.count_documents({})
        pending_applications = await db.applications.count_documents({"status": "pending"})
        qualified_applications = await db.applications.count_documents({"status": "qualified"})
        approved_applications = await db.applications.count_documents({"status": "approved"})
        
        # Get recent submissions (last 7 days)
        seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_applications = await db.applications.count_documents({
            "submission_date": {"$gte": seven_days_ago}
        })
        
        return {
            "total_applications": total_applications,
            "pending_applications": pending_applications,
            "qualified_applications": qualified_applications,
            "approved_applications": approved_applications,
            "recent_applications_7_days": recent_applications
        }
        
    except Exception as e:
        logger.error(f"Error getting application stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(username: str = Depends(verify_admin)):
    """Secure admin dashboard to view applications - requires authentication"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Money Mornings Empire - Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        </style>
    </head>
    <body class="bg-gray-100">
        <div class="min-h-screen">
            <header class="bg-green-600 text-white shadow-lg">
                <div class="max-w-7xl mx-auto px-4 py-6">
                    <h1 class="text-3xl font-bold">Money Mornings Empire - Admin Dashboard</h1>
                    <p class="text-green-100 mt-2">Manage application submissions</p>
                </div>
            </header>
            
            <main class="max-w-7xl mx-auto px-4 py-8">
                <div id="stats" class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <!-- Stats will be loaded here -->
                </div>
                
                <div class="bg-white rounded-lg shadow-lg">
                    <div class="px-6 py-4 border-b border-gray-200">
                        <h2 class="text-xl font-semibold text-gray-900">Recent Applications</h2>
                        <div class="mt-2 flex space-x-4">
                            <button onclick="loadApplications('all')" class="text-sm bg-green-500 text-white px-3 py-1 rounded">All</button>
                            <button onclick="loadApplications('pending')" class="text-sm bg-yellow-500 text-white px-3 py-1 rounded">Pending</button>
                            <button onclick="loadApplications('qualified')" class="text-sm bg-blue-500 text-white px-3 py-1 rounded">Qualified</button>
                            <button onclick="loadApplications('approved')" class="text-sm bg-green-600 text-white px-3 py-1 rounded">Approved</button>
                        </div>
                    </div>
                    <div id="applications" class="p-6">
                        <!-- Applications will be loaded here -->
                    </div>
                </div>
            </main>
        </div>
        
        <script>
            // Load application statistics
            async function loadStats() {
                try {
                    const response = await fetch('/api/applications/stats/summary');
                    const stats = await response.json();
                    
                    document.getElementById('stats').innerHTML = `
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-lg font-semibold text-gray-900">Total Applications</h3>
                            <p class="text-3xl font-bold text-green-600">${stats.total_applications}</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-lg font-semibold text-gray-900">Pending</h3>
                            <p class="text-3xl font-bold text-yellow-600">${stats.pending_applications}</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-lg font-semibold text-gray-900">Qualified</h3>
                            <p class="text-3xl font-bold text-blue-600">${stats.qualified_applications}</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-lg font-semibold text-gray-900">Approved</h3>
                            <p class="text-3xl font-bold text-green-600">${stats.approved_applications}</p>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }
            
            // Load applications
            async function loadApplications(status = 'all') {
                try {
                    const url = status === 'all' ? '/api/applications' : `/api/applications?status=${status}`;
                    const response = await fetch(url);
                    const applications = await response.json();
                    
                    let html = '';
                    if (applications.length === 0) {
                        html = '<p class="text-gray-500 text-center py-8">No applications found.</p>';
                    } else {
                        html = `
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Service</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Funding</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white divide-y divide-gray-200">
                        `;
                        
                        applications.forEach(app => {
                            const statusColor = {
                                'pending': 'bg-yellow-100 text-yellow-800',
                                'qualified': 'bg-blue-100 text-blue-800',
                                'approved': 'bg-green-100 text-green-800',
                                'rejected': 'bg-red-100 text-red-800'
                            }[app.status] || 'bg-gray-100 text-gray-800';
                            
                            html += `
                                <tr>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        ${app.first_name} ${app.last_name}
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        <a href="mailto:${app.email}" class="text-blue-600 hover:text-blue-800">${app.email}</a>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        <a href="tel:${app.phone}" class="text-blue-600 hover:text-blue-800">${app.phone}</a>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        ${app.service_interest.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        ${app.funding_amount || 'N/A'}
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColor}">
                                            ${app.status}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        ${new Date(app.submission_date).toLocaleDateString()}
                                    </td>
                                </tr>
                            `;
                        });
                        
                        html += `
                                    </tbody>
                                </table>
                            </div>
                        `;
                    }
                    
                    document.getElementById('applications').innerHTML = html;
                } catch (error) {
                    console.error('Error loading applications:', error);
                    document.getElementById('applications').innerHTML = '<p class="text-red-500 text-center py-8">Error loading applications.</p>';
                }
            }
            
            // Load data on page load
            window.onload = function() {
                loadStats();
                loadApplications();
            };
            
            // Refresh data every 30 seconds
            setInterval(() => {
                loadStats();
                loadApplications();
            }, 30000);
        </script>
    </body>
    </html>
    """

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Money Mornings API starting up...")
    try:
        # Test database connection
        await client.server_info()
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Money Mornings API shutting down...")
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
