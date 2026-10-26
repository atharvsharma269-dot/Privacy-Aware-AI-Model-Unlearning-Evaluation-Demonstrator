from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from ..services.f1_service import f1_service

router = APIRouter(prefix="/api/f1", tags=["Formula 1 Live Unlearning Demo"])


class QueryFactRequest(BaseModel):
    question: str = Field(..., description="Natural language question about an F1 driver")
    driver_id: Optional[str] = Field(None, description="Optional driver ID constraint e.g. F1-001")


class ForgetFactRequest(BaseModel):
    driver_id: str = Field(..., description="Driver ID e.g. F1-001")
    attribute: str = Field(..., description="Specific attribute key to unlearn e.g. team_for_2020_title")


class VerifyRetentionRequest(BaseModel):
    driver_id: str = Field(..., description="Driver ID e.g. F1-001")
    check_attribute: str = Field(..., description="Unrelated attribute to verify persistence e.g. car_for_2008_title")


@router.get("/drivers")
def get_all_drivers():
    """Retrieve all F1 drivers in the knowledge store with current unlearning status."""
    return f1_service.list_drivers()


@router.get("/drivers/{driver_id}")
def get_driver_by_id(driver_id: str):
    """Retrieve full active and original facts for a specific driver."""
    try:
        return f1_service.get_driver_details(driver_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ask")
def ask_question(req: QueryFactRequest):
    """Ask a question against the active F1 knowledge store."""
    result = f1_service.query_fact(req.question, req.driver_id)
    return result


@router.post("/forget")
def forget_fact(req: ForgetFactRequest):
    """Execute fact unlearning on a specific attribute for a driver."""
    try:
        return f1_service.forget_fact(req.driver_id, req.attribute)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/verify-retention")
def verify_retention(req: VerifyRetentionRequest):
    """Verify that an unrelated fact remains completely intact after unlearning."""
    try:
        return f1_service.verify_retention(req.driver_id, req.check_attribute)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reset")
def reset_demo():
    """Reset the working store back to the immutable source dataset."""
    return f1_service.reset_dataset()


@router.get("/timeline")
def get_audit_timeline():
    """Retrieve live audit timeline of all queries, unlearning, and retention verifications."""
    return f1_service.get_audit_timeline()

