from fastapi import FastAPI, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import logging
import traceback
import uuid as _uuid

from src.core.config import settings
from src.core.escalation import EscalationRouter
from src.core.notifications import NotificationService
from src.ingestion import ingest_document
from src.agents.classifier import ClassifierAgent
from src.agents.explainer import ExplainerAgent
from src.agents.form_guide import FormGuideAgent
from src.agents.risk_scanner import RiskScannerAgent
from src.agents.expungement import ExpungementAgent
from src.memory.db import DatabaseManager
from src.payments.stripe_client import StripeClient
from src.payments import check_access

app = FastAPI(title="LegalClear API", version="1.0")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
classifier = ClassifierAgent()
explainer = ExplainerAgent()
form_guide = FormGuideAgent()
risk_scanner = RiskScannerAgent()
expungement = ExpungementAgent()
db = DatabaseManager()
stripe_client = StripeClient()
escalation_router = EscalationRouter()
notifications = NotificationService()

FORM_CATEGORIES = [
    "government_form", "court_filing",
    "small_claims_complaint", "small_claims_response",
    "small_claims_judgment"
]

# Part B routers (Phase 15+). Each phase's router declares its own
# /api/* prefix; HTTP paths match source spec even though the on-disk
# location is backend/src/api/routers/ rather than .../routes/.
from src.api.routers.intake import router as intake_router        # noqa: E402
from src.api.routers.small_claims import router as small_claims_router  # noqa: E402
from src.api.routers.criminal import router as criminal_router      # noqa: E402
from src.api.routers.discovery import router as discovery_router    # noqa: E402
from src.api.routers.property_casualty import router as property_casualty_router  # noqa: E402
from src.api.routers.expungement import router as expungement_router  # noqa: E402
from src.api.routers.landlord import router as landlord_router  # noqa: E402
from src.api.routers.traffic import router as traffic_router  # noqa: E402
from src.api.routers.police_report import router as police_report_router  # noqa: E402
from src.api.routers.case_law import router as case_law_router  # noqa: E402
from src.api.routers.packet import router as packet_router  # noqa: E402
from src.api.routers.forms import router as forms_router  # noqa: E402
from src.api.routers.law import router as law_router          # noqa: E402
from src.api.routers.deadline import router as deadline_router  # noqa: E402
from src.api.routers.triage import router as triage_router        # noqa: E402
from src.api.routers.reminders import router as reminders_router  # noqa: E402
from src.api.routers.analysis import router as analysis_router    # noqa: E402
from src.api.routers.chat import router as chat_router           # noqa: E402
from src.api.routers.wills_trusts import router as wills_trusts_router  # noqa: E402
app.include_router(intake_router)
app.include_router(small_claims_router)
app.include_router(criminal_router)
app.include_router(discovery_router)
app.include_router(property_casualty_router)
app.include_router(expungement_router)
app.include_router(landlord_router)
app.include_router(traffic_router)
app.include_router(police_report_router)
app.include_router(case_law_router)
app.include_router(packet_router)
app.include_router(forms_router)
app.include_router(law_router)
app.include_router(deadline_router)
app.include_router(triage_router)
app.include_router(reminders_router)
app.include_router(analysis_router)
app.include_router(chat_router)
app.include_router(wills_trusts_router)

# Compliance framework router — mounted if package is installed.
# Install: cd compliance && uv sync; set PYTHONPATH=compliance/src.
try:
    import sys as _sys
    from pathlib import Path as _Path
    _compliance_src = _Path(__file__).parents[4] / "compliance" / "src"
    if _compliance_src.exists() and str(_compliance_src) not in _sys.path:
        _sys.path.insert(0, str(_compliance_src))
    from compliance.api.router import router as _compliance_router  # noqa: E402
    app.include_router(_compliance_router)
    logger.info("Compliance router mounted at /compliance/*")
except Exception:
    logger.warning(
        "Compliance package not available — /compliance/* endpoints disabled. "
        "Install with: cd compliance && uv sync"
    )

def verify_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

class EligibilityRequest(BaseModel):
    jurisdiction: str
    offense_description: str
    years_since_offense: int
    lang: str = "en"

class ProcessRequest(BaseModel):
    lang: str = "en"

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0", "product": "LegalClear"}

@app.post("/eligibility")
async def check_eligibility(req: EligibilityRequest):
    try:
        return await expungement.check_eligibility(
            req.jurisdiction, req.offense_description, req.years_since_offense, req.lang
        )
    except Exception as e:
        logger.error(f"Eligibility check failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Eligibility check failed: {str(e)}")

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.verify_webhook(payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        session_id = obj.get("metadata", {}).get("session_id")
        if session_id:
            db.update_payment_status(session_id, "paid")
    elif event_type == "payment_intent.payment_failed":
        session_id = obj.get("metadata", {}).get("session_id")
        if session_id:
            db.update_payment_status(session_id, "failed")
    elif event_type == "customer.subscription.created":
        user_id = obj.get("metadata", {}).get("user_id")
        if user_id:
            db.update_user_subscription(user_id, "active", obj["id"])
    elif event_type == "customer.subscription.deleted":
        user_id = obj.get("metadata", {}).get("user_id")
        if user_id:
            db.update_user_subscription(user_id, "cancelled", None)
    elif event_type == "checkout.session.completed":
        # Phase 23 — $35 Filing Packet purchase. The packet_id rides in
        # the session metadata set by /api/packet/build. We mark the
        # packet paid in the in-memory store + best-effort Supabase
        # mirror so the gated /download endpoint unlocks.
        packet_id = obj.get("metadata", {}).get("packet_id")
        if packet_id:
            from src.services.packet_builder import mark_packet_paid
            mark_packet_paid(packet_id)
            if db.client is not None:
                try:
                    db.client.table("packets").update(
                        {"status": "paid"}
                    ).eq("id", packet_id).execute()
                except Exception as exc:
                    logger.debug(
                        f"Supabase packets mark-paid mirror skipped: {exc}"
                    )

    return {"status": "success"}

@app.delete("/api/documents/{document_id}", dependencies=[Depends(verify_api_key)])
async def delete_document(document_id: str, session_id: str):
    """On-demand document delete. Scoped to the caller's session — the
    backend never deletes a document that doesn't belong to the session."""
    deleted = db.delete_document(document_id, session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found or does not belong to this session."
        )
    return {"deleted": document_id}

@app.post("/user", dependencies=[Depends(verify_api_key)])
async def create_user(email: str, lang: str = "en"):
    return db.get_or_create_user(email, lang)

@app.get("/user/{user_id}", dependencies=[Depends(verify_api_key)])
async def get_user_endpoint(user_id: str):
    return db.get_user(user_id)

@app.post("/user/{user_id}/push-token", dependencies=[Depends(verify_api_key)])
async def add_push_token(user_id: str, expo_token: str, platform: str):
    return db.save_push_token(user_id, expo_token, platform)

@app.post("/subscribe/{user_id}", dependencies=[Depends(verify_api_key)])
async def subscribe(user_id: str, email: str, success_url: str, cancel_url: str):
    return stripe_client.create_subscription_checkout(email, user_id, success_url, cancel_url)

@app.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_document(
    request: Request,
    user_id: str = Header(),
    filename: str = Header(),
    email: str = Header(),
    lang: str = Header(default="en")
):
    try:
        # Normalize user_id — generate UUID if input is non-UUID string
        try:
            _uuid.UUID(str(user_id))
        except (ValueError, TypeError, AttributeError):
            user_id = str(_uuid.uuid4())

        data = await request.body()
        doc = await ingest_document(data, filename)
        if doc.get("error"):
            return {"error": True, "message": doc.get("message")}

        classification = await classifier.classify(doc)
        escalation = escalation_router.route(classification, lang)
        tier = classifier.get_price_tier(doc)

        user = db.get_user(user_id)
        if not user:
            user = db.get_or_create_user(email, lang)

        session_id = db.create_session(
            user_id=user["id"] if user and user.get("id") else user_id,
            filename=filename,
            token_count=doc.get("token_estimate", 0),
            price_tier=tier["tier"],
            price_usd=float(tier["price_usd"]),
            payment_type="free"
        )

        document_id = db.create_document(session_id, doc.get("text", ""))

        return {
            "session_id": session_id,
            "document_id": document_id,
            "classification": classification,
            "escalation": escalation,
            "price": tier
        }
    except Exception as e:
        logger.error(f"Upload failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")

@app.post("/process/{session_id}", dependencies=[Depends(verify_api_key)])
async def process_document(session_id: str, background_tasks: BackgroundTasks, lang: str = "en"):
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        user = db.get_user(session["user_id"])

        if db.client is None:
            raise HTTPException(status_code=503, detail="Database unavailable")

        docs = db.client.table("documents").select("*").eq("session_id", session_id).execute()
        if not docs.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_record = docs.data[0]
        document_id = doc_record["id"]
        document_text = doc_record["document_text"]

        doc = {"text": document_text}
        classification = await classifier.classify(doc)

        # Run explanation and risk scan concurrently — both only depend on
        # classification which is already resolved at this point.
        explanation, risk_scan = await asyncio.gather(
            explainer.explain(doc, classification, lang),
            risk_scanner.scan(doc, classification, lang),
        )

        async def _noop() -> dict:
            return {}

        doc_category = classification.get("document_category")
        form_results, exp_results = await asyncio.gather(
            form_guide.guide(doc, classification, lang)
            if doc_category in FORM_CATEGORIES
            else _noop(),
            expungement.guide(doc, classification, lang)
            if doc_category == "expungement_petition"
            else _noop(),
        )

        escalation = escalation_router.route(classification, lang)

        db.save_results(
            document_id=document_id,
            classification=classification,
            explanation=explanation,
            form_guide=form_results,
            risk_scan=risk_scan,
            expungement_guide=exp_results,
            escalation=escalation,
            language=lang
        )

        # Phase 1: PII redaction — run after extraction, before returning
        redaction = db.redact_document_pii(document_id)
        if redaction.get("error"):
            logger.warning(f"PII redaction issue for {document_id}: {redaction['error']}")

        db.log_usage(
            category=classification.get("document_category", "unknown"),
            jurisdiction=classification.get("jurisdiction_name", "unknown"),
            language=lang,
            price_tier=session.get("price_tier", "small"),
            processing_time=0.0
        )

        if user:
            background_tasks.add_task(notifications.send_push, user["id"], "Analysis Complete", "Your document analysis is ready to view.")

        return {
            "document_id": document_id,
            "classification": classification,
            "explanation": explanation,
            "risk_scan": risk_scan,
            "form_guide": form_results,
            "expungement": exp_results,
            "escalation": escalation
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/chat/{document_id}", dependencies=[Depends(verify_api_key)])
async def chat(document_id: str, body: ChatRequest):
    question = body.message
    lang = body.lang
    try:
        doc_record = db.get_document(document_id)
        if not doc_record:
            raise HTTPException(status_code=404)

        doc = {"text": doc_record.get("document_text", "")}
        classification = doc_record.get("classification", {})
        explanation = doc_record.get("explanation", {})
        history = db.get_history(document_id)

        form_guide_res = doc_record.get("form_guide", {})
        if form_guide_res and "sections" in form_guide_res:
            qa = await form_guide.answer_form_question(doc, classification, form_guide_res, question, history, lang)
        else:
            qa = await explainer.answer_question(doc, classification, explanation, question, history, lang)

        db.save_message(document_id, "user", question, lang)
        db.save_message(document_id, "assistant", qa.get("answer", ""), lang)

        return qa
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/document/{document_id}", dependencies=[Depends(verify_api_key)])
async def get_document(document_id: str):
    try:
        return db.get_document(document_id)
    except Exception as e:
        logger.error(f"get_document failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")

@app.get("/documents/{user_id}", dependencies=[Depends(verify_api_key)])
async def get_documents(user_id: str):
    return db.get_user_documents(user_id)

@app.post("/florida-filing/prepare", dependencies=[Depends(verify_api_key)])
async def prepare_florida_filing(case_data: dict, user_id: str = Header()):
    filing_count = db.count_filings(user_id)
    if filing_count >= 1:
        raise HTTPException(
            status_code=402,
            detail="First filing free. Upgrade for expert guidance on next steps."
        )

    from src.platforms.florida_courts import PDFAGenerator, CountyRouter, ManualFilingHelper
    gen = PDFAGenerator()
    router = CountyRouter()
    helper = ManualFilingHelper()

    # In a real deployed environment, replace "/tmp/lc_test_packet/" with bounded dir.
    packet = gen.generate_packet(case_data, "/tmp/lc_filings/")
    route = router.route(case_data.get("county", ""))
    instr = helper.get_instructions(case_data.get("county", ""), "en")
    btn = helper.get_deep_link_button(case_data.get("county", ""))

    db.record_filing(user_id, case_data.get("document_id", ""), "florida", "FL")

    return {
        "packet": packet,
        "route": route,
        "instructions": instr,
        "button": btn
    }
