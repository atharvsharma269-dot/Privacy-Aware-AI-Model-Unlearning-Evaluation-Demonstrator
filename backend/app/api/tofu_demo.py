import json
import asyncio
import queue
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from ..services.tofu_service import tofu_service

router = APIRouter(prefix="/api/tofu", tags=["TOFU Benchmark Live Unlearning Demo"])


class QueryQARequest(BaseModel):
    question: str = Field(..., description="Natural language question about a TOFU fictitious author")
    author_id: Optional[str] = Field(None, description="Optional author ID constraint e.g. TOFU-000")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class ForgetAuthorRequest(BaseModel):
    author_id: str = Field(..., description="Author ID e.g. TOFU-000 to completely unlearn (all 20 QA records)")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class ForgetQARequest(BaseModel):
    author_id: str = Field(..., description="Author ID e.g. TOFU-000")
    qa_id: str = Field(..., description="Specific QA ID e.g. TOFU-QA-0000 or attribute name")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class VerifyRetentionRequest(BaseModel):
    author_id: str = Field(..., description="Author ID e.g. TOFU-000")
    check_qa_id: Optional[str] = Field(None, description="Optional specific QA ID to check retention")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class ForgetAttributeRequest(BaseModel):
    author_id: str = Field(..., description="Author ID e.g. TOFU-000")
    attribute: str = Field(..., description="Attribute/fact key (e.g. fact_1, fact_2, or 'birth date')")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class ForgetGroupRequest(BaseModel):
    cohort_id: Optional[int] = Field(None, description="Cohort ID (0 to 9) to purge entirely")
    author_ids: Optional[List[str]] = Field(None, description="Explicit list of Author IDs to purge")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class ImpactAnalysisRequest(BaseModel):
    scope_type: str = Field(..., description="Scope type: AUTHOR, QA, ATTRIBUTE, GROUP")
    target_id: str = Field(..., description="Target identifier (e.g. TOFU-000, TOFU-QA-0001, Cohort 0, forget10)")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class CreateChatSessionRequest(BaseModel):
    title: Optional[str] = Field("TOFU Privacy Session", description="Session Title")
    dataset_name: Optional[str] = Field("tofu", description="Target dataset")
    author_id: Optional[str] = Field(None, description="Active author context")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class PostChatMessageRequest(BaseModel):
    content: str = Field(..., description="User query message text")
    author_id: Optional[str] = Field(None, description="Target author ID")
    mode: Optional[str] = Field("deterministic", description="Mode: deterministic or external_llm")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID scope")


class RepairStaleStateRequest(BaseModel):
    confirmed: bool = Field(..., description="Explicit administrative confirmation to execute repair")
    target_experiment_id: Optional[str] = Field(None, description="Optional target experiment ID to restore")


@router.get("/authors")
def get_all_authors(
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    experiment_id: Optional[str] = Query(None, description="Experiment ID scope"),
):
    """Retrieve all 200 TOFU authors in the knowledge store with unlearning status scoped by experiment."""
    return tofu_service.list_authors(experiment_id=experiment_id, limit=limit, offset=offset)


@router.get("/unlearning/registry")
def get_global_unlearning_registry(experiment_id: Optional[str] = Query(None, description="Experiment ID scope")):
    """Retrieve confirmed unlearning entries in persistent registry scoped by experiment."""
    return tofu_service.get_global_registry(experiment_id=experiment_id)


@router.get("/authors/{author_id}")
def get_author_by_id(author_id: str, experiment_id: Optional[str] = Query(None, description="Experiment ID scope")):
    """Retrieve full dossier for an author with all 20 question-answer records scoped by experiment."""
    try:
        return tofu_service.get_author_details(author_id, experiment_id=experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/authors/{author_id}/status")
def get_author_status(author_id: str, experiment_id: Optional[str] = Query(None, description="Experiment ID scope")):
    """Retrieve current authoritative lifecycle status for an author scoped by experiment."""
    try:
        return tofu_service.get_author_status(author_id, experiment_id=experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/authors/{author_id}/diff")
def get_author_diff(author_id: str, experiment_id: Optional[str] = Query(None, description="Experiment ID scope")):
    """Retrieve live Before/After forensic verification diff for an author scoped by experiment."""
    try:
        return tofu_service.get_author_diff(author_id, experiment_id=experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/authors/{author_id}/events")
async def author_status_events(author_id: str, experiment_id: Optional[str] = Query(None, description="Experiment ID scope")):
    """Stream Server-Sent Events (SSE) for author unlearning status changes scoped by experiment."""
    q = queue.Queue(maxsize=50)
    tofu_service.subscribe_author_status(author_id, q)

    async def event_generator():
        try:
            initial_state = tofu_service.get_author_status(author_id, experiment_id=experiment_id)
            yield f"data: {json.dumps(initial_state)}\n\n"

            while True:
                try:
                    event = q.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.5)
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            tofu_service.unsubscribe_author_status(author_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/ask")
def ask_question(req: QueryQARequest):
    """Query a question against the active TOFU knowledge store scoped by experiment."""
    return tofu_service.query_qa(req.question, req.author_id, experiment_id=req.experiment_id)


@router.post("/forget-author")
def forget_author(req: ForgetAuthorRequest):
    """Execute complete author-level unlearning across all 20 QA pairs for a target author scoped by experiment."""
    try:
        return tofu_service.forget_author(req.author_id, experiment_id=req.experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/forget-qa")
def forget_qa(req: ForgetQARequest):
    """Execute fine-grained question-answer unlearning on an individual record scoped by experiment."""
    try:
        return tofu_service.forget_qa(req.author_id, req.qa_id, experiment_id=req.experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/verify-retention")
def verify_retention(req: VerifyRetentionRequest):
    """Verify that non-target QA records and retain-set authors remain completely intact scoped by experiment."""
    try:
        return tofu_service.verify_retention(req.author_id, req.check_qa_id, experiment_id=req.experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reset")
def reset_demo(experiment_id: Optional[str] = Query(None)):
    """Reset active working store back to immutable official TOFU dataset scoped by experiment."""
    return tofu_service.reset_dataset(experiment_id=experiment_id)


@router.post("/admin/reset-baseline")
def reset_baseline(experiment_id: Optional[str] = Query(None)):
    """Administrative operation to restore active test environment to pristine TOFU baseline."""
    return tofu_service.reset_dataset(admin_confirmed=True, experiment_id=experiment_id)


@router.get("/admin/repair-stale-state/preview")
@router.post("/admin/repair-stale-state/preview")
def preview_repair_stale_state(experiment_id: Optional[str] = Query(None)):
    """Inspect persistent forgetting state across experiments and produce an administrative repair preview."""
    return tofu_service.preview_stale_state_repair(active_experiment_id=experiment_id)


@router.post("/admin/repair-stale-state/execute")
def execute_repair_stale_state(req: RepairStaleStateRequest):
    """Execute safe administrative repair of stale forgetting state with explicit confirmation."""
    try:
        return tofu_service.execute_stale_state_repair(confirmed=req.confirmed, target_experiment_id=req.target_experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/manifest")
def get_pristine_manifest():
    """Retrieve cryptographic and structural manifest of the pristine official TOFU benchmark."""
    return tofu_service.get_pristine_manifest()


@router.get("/timeline")
def get_audit_timeline():
    """Retrieve live audit timeline of all queries, unlearning, and retention verifications."""
    return tofu_service.get_audit_timeline()


@router.post("/forget-attribute")
def forget_attribute(req: ForgetAttributeRequest):
    """Execute fine-grained unlearning for a specific author attribute/fact scoped by experiment."""
    try:
        return tofu_service.forget_attribute(req.author_id, req.attribute, experiment_id=req.experiment_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/forget-group")
def forget_group(req: ForgetGroupRequest):
    """Execute group-level unlearning across an entire cohort or author group scoped by experiment."""
    try:
        return tofu_service.forget_group(cohort_id=req.cohort_id, author_ids=req.author_ids, experiment_id=req.experiment_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/impact-analysis")
def compute_impact(req: ImpactAnalysisRequest):
    """Calculate pre-deletion impact analysis and projected utility delta scoped by experiment."""
    return tofu_service.compute_forget_impact(req.scope_type, req.target_id, experiment_id=req.experiment_id)


@router.get("/provenance/{author_id}")
def get_provenance(author_id: str):
    """Retrieve complete data lineage and provenance DAG for an author and related checkpoints."""
    return tofu_service.get_provenance_graph(author_id)


@router.post("/red-team/{author_id}")
def run_red_team_audit(author_id: str):
    """Run simulated adversarial 5-probe privacy attack suite against an author."""
    return tofu_service.run_privacy_red_team(author_id)


@router.post("/retention-regression/{author_id}")
def run_retention_regression(author_id: str):
    """Run regression evaluation across non-target authors to confirm preserved utility."""
    return tofu_service.run_retention_regression(author_id)


@router.get("/deletion-report")
def get_deletion_report(request_id: str = "REQ-INIT", author_id: str = "TOFU-000", scope: str = "ALL"):
    """Retrieve a technical experimental deletion verification report."""
    return tofu_service.generate_deletion_report(request_id, author_id, scope)


# --- Chat Assistant Endpoints ---

@router.get("/chat/sessions")
def list_chat_sessions(experiment_id: Optional[str] = Query(None)):
    """List all interactive chat sessions, optionally scoped by experiment_id."""
    return tofu_service.list_chat_sessions(experiment_id=experiment_id)


@router.post("/chat/sessions")
def create_chat_session(req: CreateChatSessionRequest):
    """Create a new chat conversation session scoped by experiment_id."""
    return tofu_service.create_chat_session(
        title=req.title,
        dataset_name=req.dataset_name,
        author_id=req.author_id,
        experiment_id=req.experiment_id,
    )


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str):
    """Retrieve messages and context for a chat session."""
    try:
        return tofu_service.get_chat_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/chat/sessions")
def delete_all_chat_sessions():
    """Delete all chat sessions and their messages."""
    return tofu_service.delete_all_chat_sessions()


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str):
    """Delete a single chat session."""
    try:
        return tofu_service.delete_chat_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/chat/sessions/{session_id}/messages")
def post_chat_message(session_id: str, req: PostChatMessageRequest):
    """Send a user message and receive retrieval-grounded assistant response with source citations scoped by experiment."""
    try:
        return tofu_service.post_chat_message(
            session_id=session_id,
            user_text=req.content,
            author_id=req.author_id,
            mode=req.mode or "deterministic",
            experiment_id=req.experiment_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
