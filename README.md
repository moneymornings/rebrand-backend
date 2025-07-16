# Money Mornings Empire - Backend

FastAPI backend for Money Mornings Empire business funding application system.

## Features
- Secure admin dashboard with HTTP Basic Authentication
- Application form submission and storage
- MongoDB integration
- Email notification system
- RESTful API endpoints

## Environment Variables Required
- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name (money_mornings)
- `ADMIN_USERNAME`: Admin dashboard username
- `ADMIN_PASSWORD`: Admin dashboard password
- `NOTIFICATION_EMAIL`: Email for notifications

## Endpoints
- `GET /admin`: Secure admin dashboard
- `POST /api/applications/submit`: Submit new application
- `GET /api/applications`: Get all applications
- `GET /api/applications/stats/summary`: Get statistics

## Deployment
Designed for Railway deployment with automatic environment detection.
