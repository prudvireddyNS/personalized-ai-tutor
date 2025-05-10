# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from routes import user as user_routes
from routes import tutor as tutor_routes
from routes import session as session_routes 

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Edu AI Tutor API",
    description="API for interacting with the AI Tutor and managing user data.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(user_routes.router)
app.include_router(tutor_routes.router)
app.include_router(session_routes.router) 

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Edu AI Tutor API"}
