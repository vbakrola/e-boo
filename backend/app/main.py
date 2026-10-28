"""Ubuntu Lab Manager - FastAPI Main Application Entry Point."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import PermissionProfile, SystemSetting
from backend.app.worker import run_worker_loop
from backend.app.routers import (
    auth, devices, profiles, provisioning, users, tasks, audit, settings as settings_router, agent_api
)


def seed_default_permission_profiles(db):
    """Seed standard Ubuntu Lab permission profiles if not present."""
    default_profiles = [
        {
            "name": "Student",
            "description": "Standard Linux account for students. Includes bash shell, home directory, student group membership. No sudo access.",
            "shell": "/bin/bash",
            "create_home": True,
            "primary_group": "students",
            "supplementary_groups": "dialout,plugdev",
            "sudo_policy": "none",
            "is_system": True
        },
        {
            "name": "Lab Assistant",
            "description": "Support account for laboratory teaching assistants. No sudo access by default, permissions strictly scoped.",
            "shell": "/bin/bash",
            "create_home": True,
            "primary_group": "labassistants",
            "supplementary_groups": "students,dialout,plugdev,wireshark",
            "sudo_policy": "none",
            "is_system": True
        },
        {
            "name": "Administrator",
            "description": "Restricted administrative account according to explicit lab policy. Allows service restarts and package queries without arbitrary root access.",
            "shell": "/bin/bash",
            "create_home": True,
            "primary_group": "sudo",
            "supplementary_groups": "adm,systemd-journal",
            "sudo_policy": "restricted",
            "is_system": True
        }
    ]

    for p_data in default_profiles:
        existing = db.query(PermissionProfile).filter(PermissionProfile.name == p_data["name"]).first()
        if not existing:
            profile = PermissionProfile(**p_data)
            db.add(profile)
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # 1. Initialize DB tables
    Base.metadata.create_all(bind=engine)

    # 2. Seed default permission profiles
    db = SessionLocal()
    try:
        seed_default_permission_profiles(db)
    finally:
        db.close()

    # 3. Start background worker loop
    worker_task = asyncio.create_task(run_worker_loop())

    yield

    # Cancellation upon server stop
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LAN-only Central Management Server for Ubuntu Computer Laboratories",
    lifespan=lifespan
)

# CORS Middleware for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN environments: allow frontend access from any LAN IP or port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject hardened HTTP security headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Include Routers
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(profiles.router)
app.include_router(provisioning.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(audit.router)
app.include_router(settings_router.router)
app.include_router(agent_api.router)


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """LAN health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "lan-production"
    }
