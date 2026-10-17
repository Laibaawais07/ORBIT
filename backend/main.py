
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from backend.ui import router as ui_router
from backend.ai_workflow import run_orbit_ai_workflow
from backend.agent_routes import router as agent_router
from backend.verification_routes import router as verification_router
from backend.security import router as security_router, OrbitAccessMiddleware
from backend.completion_routes import router as completion_router
from backend.approvals import (
    create_approval_request,
    decide_approval,
    get_approval_request,
    list_approval_requests
)


# Initialize ORBIT FastAPI application
app = FastAPI(
    title="ORBIT - AI Opportunity & Growth Agent",
    version="1.2.0"
)
app.include_router(agent_router)
app.include_router(ui_router)
app.include_router(verification_router)
app.add_middleware(OrbitAccessMiddleware)
app.include_router(security_router)
app.include_router(completion_router)

# ---------------------------------------
# HOME ENDPOINT
# ---------------------------------------

@app.get("/")
def home():
    return {
        "project": "ORBIT",
        "message": "Welcome to ORBIT!",
        "status": "running"
    }


# ---------------------------------------
# HEALTH CHECK
# ---------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ORBIT Backend"
    }


# ---------------------------------------
# STUDENT PROFILE MODEL
# ---------------------------------------

class StudentProfile(BaseModel):
    academic_year: int = Field(ge=1, le=10)
    skills: list[str]
    category: str = "all"
    hours_per_week: int = Field(
        default=5,
        ge=1,
        le=80
    )


# ---------------------------------------
# AI-POWERED STUDENT ANALYSIS
# ---------------------------------------

@app.post("/api/analyze")
async def analyze_student(profile: StudentProfile):

    result = await run_orbit_ai_workflow(
        student_year=profile.academic_year,
        student_skills=profile.skills,
        category=profile.category,
        hours_per_week=profile.hours_per_week
    )

    return result


# ---------------------------------------
# HUMAN-IN-THE-LOOP APPROVAL MODELS
# ---------------------------------------

class ApprovalCreate(BaseModel):
    opportunity_id: int
    roadmap: dict


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]


# ---------------------------------------
# CREATE APPROVAL REQUEST
# ---------------------------------------

@app.post("/api/approvals")
def create_approval(data: ApprovalCreate):

    return create_approval_request(
        opportunity_id=data.opportunity_id,
        roadmap=data.roadmap
    )


# ---------------------------------------
# LIST ALL APPROVAL REQUESTS
# ---------------------------------------

@app.get("/api/approvals")
def list_approvals():

    return {
        "approvals": list_approval_requests()
    }


# ---------------------------------------
# GET APPROVAL REQUEST
# ---------------------------------------

@app.get("/api/approvals/{request_id}")
def get_approval(request_id: str):

    result = get_approval_request(request_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found"
        )

    return result


# ---------------------------------------
# APPROVE OR REJECT ROADMAP
# ---------------------------------------

@app.post("/api/approvals/{request_id}/decide")
def decide_on_approval(
    request_id: str,
    data: ApprovalDecision
):

    result = decide_approval(
        request_id=request_id,
        decision=data.decision
    )

    if "error" in result:

        status_code = (
            404
            if result["error"] == "Approval request not found"
            else 409
        )

        raise HTTPException(
            status_code=status_code,
            detail=result["error"]
        )

    return result


# ---------------------------------------
# ACCESS APPROVED ROADMAP ONLY
# ---------------------------------------

@app.get("/api/approvals/{request_id}/approved-roadmap")
def approved_roadmap(request_id: str):

    result = get_approval_request(request_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found"
        )

    if result["status"] != "approved":
        raise HTTPException(
            status_code=403,
            detail="Student approval required before roadmap use"
        )

    return {
        "request_id": request_id,
        "status": "approved",
        "roadmap": result["roadmap"]
    }
