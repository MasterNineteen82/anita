from uvicorn.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from app import app as flask_app

# Create a FastAPI instance
api = FastAPI(title="Smart Card Manager API", 
              description="API for managing and working with smart cards",
              version="1.0.0")

# Mount the Flask app
api.mount("/", WSGIMiddleware(flask_app))

# For direct FastAPI routes if needed
@api.get("/api/status")
def status():
    return {"status": "operational", "server": "FastAPI"}