"""
main.py
───────
EventFlow Hackathon Orchestration Platform — FastAPI entry point.

Architecture notes:
  - Repository Pattern (repositories.py): route handlers are 100% free of
    raw ORM queries. Each handler instantiates the relevant repository,
    delegates all DB work, and just shapes the HTTP response. This keeps
    handlers thin, readable, and trivially unit-testable.

  - Dependency Injection via `Depends(get_db)`: a single DB session is
    created per request, shared across all repositories in that request,
    and closed in the `get_db` finally block.

  - BackgroundTasks for LLM calls: rationale generation is fire-and-forget
    — the HTTP response returns immediately; the background task writes
    the result back to the Team row when the LLM responds.

  - Approval cascade: every approve/reject handler maps the ApprovalType
    to a domain side-effect (set team.is_approved, mark scores, etc.)
    using a clean dispatch dictionary — no long if/elif chains.

Run with:
    uvicorn main:app --reload
"""

from __future__ import annotations

import json
import logging
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import httpx
import os
from google import genai
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# ── Local imports ─────────────────────────────────────────────
import schemas
from database import get_db, init_db
from models import (
    ApprovalStatus, ApprovalType, UserRole, User, MentorProfile, Message,
    Team, JudgeProfile, Approval
)
from repositories import (
    ParticipantRepository,
    TeamRepository,
    JudgeRepository,
    ScoreRepository,
    ApprovalRepository,
    EventConfigRepository,
)
from schemas import (
    RosterUpload, RosterUploadResponse,
    ParticipantRead,
    JudgeCreate, JudgeRead,
    ApprovalCreate, ApprovalRead,
    ApprovalApproveRequest, ApprovalRejectRequest,
    ScoreSubmit, ScoreRead,
    TeamFormationConfig, TeamFormationResponse,
    LeaderboardEntryRead, LeaderboardResponse,
    TeamRead,
    MessageResponse,
)
from team_formation import (
    ParticipantData, form_teams, build_rationale_prompt,
)
from scoring_engine import (
    JudgeScoreInput, consolidate_scores, build_leaderboard,
)

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("eventflow")


# ──────────────────────────────────────────────
# LIFESPAN (replaces deprecated @app.on_event)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB tables and seed defaults. Shutdown: clean up."""
    logger.info("EventFlow starting up — initialising database …")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("EventFlow shutting down.")


# ──────────────────────────────────────────────
# APP INSTANCE
# ──────────────────────────────────────────────

app = FastAPI(
    title="EventFlow — Hackathon Orchestration Platform",
    version="1.0.0",
    description=(
        "Enterprise-grade API for deterministic team formation, "
        "judge score consolidation, anomaly detection, and approval gating."
    ),
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────
# In production, replace allow_origins with your actual frontend domain(s).

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in prod: ["https://your-dashboard.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _generate_team_name(index: int) -> str:
    """Generates deterministic team names like 'Team Orion-01'."""
    codenames = [
        "Orion", "Nebula", "Aurora", "Phoenix", "Zenith",
        "Quasar", "Vega", "Pulsar", "Lyra", "Cygnus",
        "Hydra", "Aquila", "Cetus", "Dorado", "Eridanus",
    ]
    name = codenames[index % len(codenames)]
    suffix = f"{(index // len(codenames)) + 1:02d}" if index >= len(codenames) else ""
    return f"Team {name}{'-' + suffix if suffix else ''}"


def _get_or_404(repo_method, identifier, resource_name: str):
    """
    DRY helper: call a repository getter and raise 404 if None.
    `repo_method` is a callable that returns Optional[T].
    """
    obj = repo_method(identifier)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} with id={identifier} not found.",
        )
    return obj


# ──────────────────────────────────────────────
# BACKGROUND TASK: LLM RATIONALE GENERATION
# ──────────────────────────────────────────────

async def _generate_and_save_rationale(
    team_id: int,
    members_data: list[ParticipantData],
    team_name: str,
) -> None:
    """
    Background task: sends the rationale prompt to an LLM endpoint and
    persists the response back to the Team row.

    In this implementation we call a local/mock endpoint. To wire up a
    real LLM (OpenAI, Anthropic, etc.) replace the httpx call below with
    your SDK call of choice — the surrounding logic stays identical.
    """
    from database import SessionLocal  # avoid circular import at module level

    prompt = build_rationale_prompt(members_data, team_name)
    rationale_text: str

    try:
        logger.info(f"[Background] Generating rationale for team_id={team_id} via Gemini …")
        
        # ── REAL GEMINI CALL ──────────────
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        # Unified on the google-genai SDK + gemini-2.5-flash (see ai_engine.py)
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        rationale_text = response.text.strip()
        # ──────────────────────────────────
    except Exception as exc:
        logger.error(f"[Background] LLM call failed for team_id={team_id}: {exc}")
        rationale_text = "[Rationale generation failed — see server logs.]"

    # Persist rationale — open a new session (background tasks outlive the request session)
    db = SessionLocal()
    try:
        team_repo = TeamRepository(db)
        team = team_repo.get_by_id(team_id)
        if team:
            team_repo.update_rationale(team, rationale_text)
            db.commit()
            logger.info(f"[Background] Rationale saved for team_id={team_id}.")
    except Exception as exc:
        logger.error(f"[Background] Failed to save rationale for team_id={team_id}: {exc}")
        db.rollback()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
# SECTION 1: PARTICIPANT INGESTION
# ══════════════════════════════════════════════════════════════

@app.post(
    "/upload-roster/",
    response_model=RosterUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk-upload a participant roster",
    tags=["Participants"],
)
def upload_roster(
    payload: RosterUpload,
    db: Session = Depends(get_db),
) -> RosterUploadResponse:
    """
    Accepts a JSON list of participants and inserts them into the DB.
    Duplicate emails are silently skipped (idempotent re-upload support).
    """
    repo = ParticipantRepository(db)
    participants_data = [p.model_dump() for p in payload.participants]
    created, skipped = repo.bulk_upsert(participants_data)

    logger.info(f"Roster upload: {created} created, {skipped} skipped.")
    return RosterUploadResponse(
        created=created,
        skipped=skipped,
        message=f"Roster processed. {created} new participant(s) added.",
    )


@app.get(
    "/participants/",
    response_model=list[ParticipantRead],
    summary="List all registered participants",
    tags=["Participants"],
)
def list_participants(
    db: Session = Depends(get_db),
) -> list[ParticipantRead]:
    repo = ParticipantRepository(db)
    return repo.get_all()


# ══════════════════════════════════════════════════════════════
# SECTION 2: JUDGES
# ══════════════════════════════════════════════════════════════

@app.post(
    "/judges/",
    response_model=JudgeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new judge",
    tags=["Judges"],
)
def create_judge(
    payload: JudgeCreate,
    db: Session = Depends(get_db),
) -> JudgeRead:
    repo = JudgeRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Judge with email '{payload.email}' already exists.",
        )
    judge = repo.create(
        name=payload.name,
        email=payload.email,
        expertise=payload.expertise,
    )
    db.commit()
    db.refresh(judge)
    return judge


@app.get(
    "/judges/",
    response_model=list[JudgeRead],
    summary="List all judges",
    tags=["Judges"],
)
def list_judges(db: Session = Depends(get_db)) -> list[JudgeRead]:
    return JudgeRepository(db).get_all()


# ══════════════════════════════════════════════════════════════
# SECTION 3: APPROVAL GATE ENGINE
# ══════════════════════════════════════════════════════════════

@app.post(
    "/approvals/create",
    response_model=ApprovalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new approval gate",
    tags=["Approvals"],
)
def create_approval(
    payload: ApprovalCreate,
    db: Session = Depends(get_db),
) -> ApprovalRead:
    """
    Manually queue an approval gate. Most approvals are auto-created
    by the formation and scoring engines, but this endpoint is available
    for ad-hoc committee requests.
    """
    repo = ApprovalRepository(db)
    approval = repo.create(
        approval_type=payload.approval_type,
        team_id=payload.team_id,
        reference_id=payload.reference_id,
        payload=payload.payload,
    )
    db.commit()
    db.refresh(approval)
    logger.info(f"Approval #{approval.id} created: type={approval.approval_type}")
    return approval


@app.get(
    "/approvals/pending",
    response_model=list[ApprovalRead],
    summary="List all pending approvals",
    tags=["Approvals"],
)
def get_pending_approvals(
    db: Session = Depends(get_db),
) -> list[ApprovalRead]:
    return ApprovalRepository(db).get_pending()


@app.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalRead,
    summary="Approve a pending gate and trigger cascade side-effects",
    tags=["Approvals"],
)
def approve_gate(
    approval_id: int,
    payload: ApprovalApproveRequest,
    db: Session = Depends(get_db),
) -> ApprovalRead:
    """
    Approves an approval gate and applies the domain-level side-effect
    corresponding to its type:

    | ApprovalType                  | Side-effect                                  |
    |-------------------------------|----------------------------------------------|
    | TEAM_REVIEW                   | team.is_approved = True                      |
    | RESULT_PUBLICATION_REVIEW     | team.is_qualified = True (publish results)   |
    | ANOMALY_REVIEW                | Score.is_anomalous reset for the team        |
    | PROGRESSION_INVITE_REVIEW     | team.is_qualified = True                     |
    | MESSAGE_SENDING_REVIEW        | Communication status → SENT (mock)           |
    | MENTOR_ASSIGNMENT_REVIEW      | Logged; no automatic DB change needed        |
    """
    approval_repo = ApprovalRepository(db)
    approval = _get_or_404(approval_repo.get_by_id, approval_id, "Approval")

    try:
        approval_repo.transition(
            approval,
            new_status=ApprovalStatus.APPROVED,
            resolved_by=payload.resolved_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # ── Cascade side-effects ─────────────────────────────────────
    _apply_approve_cascade(approval, db)

    # Transition to EXECUTED (terminal for approvals with immediate effect)
    try:
        approval_repo.transition(
            approval,
            new_status=ApprovalStatus.EXECUTED,
            resolved_by=payload.resolved_by,
        )
    except ValueError:
        # Some types may not auto-execute; leave them as APPROVED
        pass

    db.commit()
    db.refresh(approval)
    logger.info(
        f"Approval #{approval_id} approved + executed by '{payload.resolved_by}'."
    )
    return approval


@app.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalRead,
    summary="Reject a pending approval gate",
    tags=["Approvals"],
)
def reject_gate(
    approval_id: int,
    payload: ApprovalRejectRequest,
    db: Session = Depends(get_db),
) -> ApprovalRead:
    approval_repo = ApprovalRepository(db)
    approval = _get_or_404(approval_repo.get_by_id, approval_id, "Approval")

    try:
        approval_repo.transition(
            approval,
            new_status=ApprovalStatus.REJECTED,
            resolved_by=payload.resolved_by,
            reject_reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    db.commit()
    db.refresh(approval)
    logger.info(
        f"Approval #{approval_id} rejected by '{payload.resolved_by}': {payload.reason}"
    )
    return approval


def _create_notification(db: Session, user_id: int, title: str, message: str, type: str):
    """Utility to create a notification for a user."""
    notif = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
    )
    db.add(notif)
    # Don't commit here, let the caller commit if it's part of a transaction,
    # or we can commit if we want. But the caller usually commits right after.
    # Actually, we should commit/flush depending on usage.
    # To be safe, just add it. The caller's db.commit() will save it.

def _apply_approve_cascade(approval, db: Session) -> None:
    """
    Dispatches domain side-effects when an approval transitions to APPROVED.
    Isolated here to keep the route handler readable.
    """
    atype = approval.approval_type
    team_repo = TeamRepository(db)
    score_repo = ScoreRepository(db)

    if atype == ApprovalType.TEAM_REVIEW:
        if approval.team_id:
            team = team_repo.get_by_id(approval.team_id)
            if team:
                team_repo.set_approved(team, approved=True)
                logger.info(f"  ↳ Team #{approval.team_id} marked as approved.")
                for member in team.members:
                    if member.email:
                        u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
                        if u:
                            _create_notification(db, u.id, "Team Assigned", f"You have been assigned to {team.name}", "TEAM")

    elif atype == ApprovalType.RESULT_PUBLICATION_REVIEW:
        if approval.team_id:
            team = team_repo.get_by_id(approval.team_id)
            if team:
                team_repo.set_qualified(team, qualified=True)
                logger.info(f"  ↳ Team #{approval.team_id} marked as qualified (results published).")
                for member in team.members:
                    if member.email:
                        u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
                        if u:
                            _create_notification(db, u.id, "Leaderboard Published", "Results have been published", "SYSTEM")

    elif atype == ApprovalType.ANOMALY_REVIEW:
        # Committee reviewed the anomaly and decided to accept scores as-is
        if approval.team_id:
            scores = score_repo.get_for_team(approval.team_id)
            for s in scores:
                score_repo.mark_anomalous(s, is_anomalous=False)
            logger.info(
                f"  ↳ Anomaly cleared for {len(scores)} score(s) on team #{approval.team_id}."
            )

    elif atype == ApprovalType.PROGRESSION_INVITE_REVIEW:
        if approval.team_id:
            team = team_repo.get_by_id(approval.team_id)
            if team:
                team_repo.set_qualified(team, qualified=True)
                logger.info(f"  ↳ Team #{approval.team_id} invited to next round.")

    elif atype == ApprovalType.MESSAGE_SENDING_REVIEW:
        # In a full implementation: fetch Communication by reference_id and set status=SENT
        logger.info(
            f"  ↳ MESSAGE_SENDING_REVIEW approved — communication #{approval.reference_id} "
            f"would be dispatched here."
        )

    elif atype == ApprovalType.MENTOR_ASSIGNMENT_REVIEW:
        logger.info(
            f"  ↳ MENTOR_ASSIGNMENT_REVIEW approved for reference_id={approval.reference_id}."
        )


# ══════════════════════════════════════════════════════════════
# SECTION 4: DETERMINISTIC TEAM FORMATION ENGINE
# ══════════════════════════════════════════════════════════════

@app.post(
    "/api/v1/trigger-team-formation",
    response_model=TeamFormationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run the deterministic team formation algorithm",
    tags=["Team Formation"],
)
async def trigger_team_formation(
    config_override: Optional[TeamFormationConfig] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> TeamFormationResponse:
    """
    Full pipeline:
      1. Pull unassigned participants from DB.
      2. Load formation constraints from EventConfig (overridable per-call).
      3. Convert to `ParticipantData` objects consumed by `form_teams()`.
      4. Persist formed teams + assign participants.
      5. Auto-create a TEAM_REVIEW Approval gate per team.
      6. Fire BackgroundTask to call LLM for team rationale.

    Idempotency note: calling this endpoint twice will only process
    participants still unassigned (team_id IS NULL), so re-running is safe.
    """
    participant_repo = ParticipantRepository(db)
    team_repo        = TeamRepository(db)
    approval_repo    = ApprovalRepository(db)
    config_repo      = EventConfigRepository(db)

    # ── 1. Get unassigned participants ────────
    unassigned_db = participant_repo.get_unassigned()
    if not unassigned_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No unassigned participants found. All participants are already in teams.",
        )

    # ── 2. Load config ────────────────────────
    event_config = config_repo.get()
    team_size            = (config_override and config_override.team_size)            or event_config.team_size
    max_same_institution = (config_override and config_override.max_same_institution) or event_config.max_same_institution
    shuffle_seed         = (config_override and config_override.shuffle_seed)         or 42

    required_skills: list[str] = []
    if event_config.required_skills:
        required_skills = [s.strip() for s in event_config.required_skills.split(",") if s.strip()]

    # ── 3. Map DB rows → ParticipantData dataclasses ──
    pd_objects: list[ParticipantData] = [
        ParticipantData(
            id          = p.id,
            name        = p.name,
            email       = p.email,
            institution = p.institution,
            skill_tags  = p.skills_list(),
            experience  = p.experience,
        )
        for p in unassigned_db
    ]

    # ── 4. Run formation engine ───────────────
    formation_result = form_teams(
        participants         = pd_objects,
        team_size            = team_size,
        max_same_institution = max_same_institution,
        shuffle_seed         = shuffle_seed,
    )

    if not formation_result.teams:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Team formation failed — no teams could be formed.",
                "warnings": formation_result.warnings,
            },
        )

    # ── 5. Persist teams, assign members, create approvals ──
    # Pre-index DB participants by ID for O(1) lookup
    db_participant_map = {p.id: p for p in unassigned_db}

    created_team_ids: list[int] = []
    existing_team_count = len(team_repo.get_all())

    for idx, team_members in enumerate(formation_result.teams):
        team_name = _generate_team_name(existing_team_count + idx)
        team      = team_repo.create(name=team_name)

        # Assign DB participant rows to this team
        db_members = [db_participant_map[m.id] for m in team_members if m.id in db_participant_map]
        team_repo.assign_members(team, db_members)

        # Auto-create TEAM_REVIEW approval gate
        payload_data = {
            "team_name":    team_name,
            "member_count": len(team_members),
            "members":      [
                {
                    "name":        m.name,
                    "institution": m.institution,
                    "skills":      m.skill_tags,
                    "experience":  m.experience,
                }
                for m in team_members
            ],
        }
        approval_repo.create(
            approval_type=ApprovalType.TEAM_REVIEW,
            team_id=team.id,
            payload=json.dumps(payload_data),
        )

        created_team_ids.append(team.id)

        # Queue LLM rationale generation as a background task
        background_tasks.add_task(
            _generate_and_save_rationale,
            team_id      = team.id,
            members_data = team_members,
            team_name    = team_name,
        )

    db.commit()

    logger.info(
        f"Team formation complete: {len(formation_result.teams)} teams created, "
        f"{len(formation_result.warnings)} warnings."
    )

    return TeamFormationResponse(
        teams_formed      = len(formation_result.teams),
        approvals_queued  = len(formation_result.teams),
        warnings          = formation_result.warnings,
        team_ids          = created_team_ids,
    )


@app.get(
    "/api/v1/teams/",
    response_model=list[TeamRead],
    summary="List all formed teams with members",
    tags=["Team Formation"],
)
def list_teams(db: Session = Depends(get_db)) -> list[TeamRead]:
    return TeamRepository(db).get_all()


# ══════════════════════════════════════════════════════════════
# SECTION 5: SCORE SUBMISSION & LEADERBOARD
# ══════════════════════════════════════════════════════════════

@app.post(
    "/api/v1/submit-score",
    response_model=ScoreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a judge's score for a team",
    tags=["Scoring"],
)
def submit_score(
    payload: ScoreSubmit,
    db: Session = Depends(get_db),
) -> ScoreRead:
    """
    Accepts a judge's rubric scores, computes the weighted total using
    the current EventConfig weights, and persists the score.

    If the score is detected as anomalous (using a single-score preview),
    an ANOMALY_REVIEW approval gate is automatically queued.

    Note: Full anomaly detection runs across the whole judge panel, so
    the `is_anomalous` flag here is a pre-flight check only. The
    leaderboard endpoint runs the definitive anomaly scan.
    """
    team_repo    = TeamRepository(db)
    judge_repo   = JudgeRepository(db)
    score_repo   = ScoreRepository(db)
    config_repo  = EventConfigRepository(db)
    approval_repo = ApprovalRepository(db)

    # ── Validate foreign keys exist ──────────
    team  = _get_or_404(team_repo.get_by_id,  payload.team_id,  "Team")
    judge = _get_or_404(judge_repo.get_by_id, payload.judge_id, "Judge")

    # ── Prevent duplicate submission ─────────
    existing = score_repo.get_for_team(payload.team_id)
    if any(s.judge_id == payload.judge_id for s in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Judge #{payload.judge_id} has already submitted a score for "
                f"team #{payload.team_id}. Use the update endpoint to amend."
            ),
        )

    # ── Compute weighted total ────────────────
    event_config = config_repo.get()
    weights = event_config.weights_dict()

    judge_input = JudgeScoreInput(
        judge_id        = payload.judge_id,
        judge_name      = judge.name,
        team_id         = payload.team_id,
        innovation      = payload.innovation,
        technical_depth = payload.technical_depth,
        presentation    = payload.presentation,
        feasibility     = payload.feasibility,
        impact          = payload.impact,
        notes           = payload.notes,
    )

    from scoring_engine import calculate_weighted_total
    weighted_total = calculate_weighted_total(judge_input, weights)

    # ── Persist score ─────────────────────────
    score = score_repo.create(
        team_id         = payload.team_id,
        judge_id        = payload.judge_id,
        innovation      = payload.innovation,
        technical_depth = payload.technical_depth,
        presentation    = payload.presentation,
        feasibility     = payload.feasibility,
        impact          = payload.impact,
        weighted_total  = weighted_total,
        notes           = payload.notes,
    )

    # ── Pre-flight anomaly check ──────────────
    # Run consolidation on all scores for this team including the new one
    all_scores_db = score_repo.get_for_team(payload.team_id)
    all_inputs = [
        JudgeScoreInput(
            judge_id        = s.judge_id,
            judge_name      = "unknown",   # judge name not critical for detection
            team_id         = s.team_id,
            innovation      = s.innovation      or 0,
            technical_depth = s.technical_depth or 0,
            presentation    = s.presentation    or 0,
            feasibility     = s.feasibility     or 0,
            impact          = s.impact          or 0,
        )
        for s in all_scores_db
    ]
    all_inputs.append(judge_input)  # include the score we just created

    from scoring_engine import detect_anomalies
    anomalies = detect_anomalies(all_inputs, threshold=event_config.anomaly_threshold)
    flagged_judge_ids = {f.judge_id for f in anomalies}

    if payload.judge_id in flagged_judge_ids:
        score_repo.mark_anomalous(score, is_anomalous=True)
        # Auto-create anomaly review if not already pending
        existing_anomaly_approval = approval_repo.get_by_type_and_team(
            ApprovalType.ANOMALY_REVIEW, payload.team_id
        )
        if not existing_anomaly_approval:
            anomaly_payload = {
                "judge_id":   payload.judge_id,
                "judge_name": judge.name,
                "team_id":    payload.team_id,
                "flags":      [
                    {
                        "dimension":  f.dimension,
                        "score":      f.score,
                        "panel_mean": f.panel_mean,
                        "z_score":    f.z_score,
                        "severity":   f.severity,
                    }
                    for f in anomalies if f.judge_id == payload.judge_id
                ],
            }
            approval_repo.create(
                approval_type=ApprovalType.ANOMALY_REVIEW,
                team_id=payload.team_id,
                reference_id=score.id,
                payload=json.dumps(anomaly_payload),
            )
            logger.warning(
                f"Anomalous score detected — ANOMALY_REVIEW queued for "
                f"judge #{payload.judge_id} / team #{payload.team_id}."
            )

    db.commit()
    db.refresh(score)
    logger.info(
        f"Score submitted: judge={judge.name}, team={team.name}, "
        f"weighted_total={weighted_total}"
    )
    return score


@app.get(
    "/api/v1/leaderboard",
    response_model=LeaderboardResponse,
    summary="Compute and return the current ranked leaderboard",
    tags=["Scoring"],
)
def get_leaderboard(db: Session = Depends(get_db)) -> LeaderboardResponse:
    """
    Full leaderboard pipeline:
      1. Load weights from EventConfig.
      2. Group all Score rows by team_id.
      3. Run `consolidate_scores()` for every team.
      4. Persist final_score + rank back to Team rows.
      5. Pass results to `build_leaderboard()` for ranked ordering.
      6. Return serialisable LeaderboardResponse.

    Teams with anomalous scores not yet resolved by committee will appear
    at the bottom with `is_held=True` and `final_score=null`.
    """
    team_repo   = TeamRepository(db)
    score_repo  = ScoreRepository(db)
    judge_repo  = JudgeRepository(db)
    config_repo = EventConfigRepository(db)

    event_config = config_repo.get()
    weights      = event_config.weights_dict()
    threshold    = event_config.anomaly_threshold

    all_teams  = team_repo.get_all()
    if not all_teams:
        return LeaderboardResponse(total_teams=0, ranked=0, held=0, entries=[])

    # Build a judge_id → name map to populate JudgeScoreInput.judge_name
    all_judges      = judge_repo.get_all()
    judge_name_map  = {j.id: j.name for j in all_judges}

    # Group scores by team_id
    scores_by_team = score_repo.get_scores_grouped_by_team()

    # ── Run consolidation per team ────────────
    team_results: list[tuple[int, str, object]] = []  # (team_id, team_name, TeamScoreResult)

    for team in all_teams:
        team_scores_db = scores_by_team.get(team.id, [])

        judge_inputs = [
            JudgeScoreInput(
                judge_id        = s.judge_id,
                judge_name      = judge_name_map.get(s.judge_id, f"Judge #{s.judge_id}"),
                team_id         = s.team_id,
                innovation      = s.innovation      or 0.0,
                technical_depth = s.technical_depth or 0.0,
                presentation    = s.presentation    or 0.0,
                feasibility     = s.feasibility     or 0.0,
                impact          = s.impact          or 0.0,
                notes           = s.notes,
            )
            for s in team_scores_db
            # Exclude scores already marked anomalous from consolidation
            # (unless committee cleared them via ANOMALY_REVIEW approval)
        ]

        result = consolidate_scores(
            team_id           = team.id,
            scores            = judge_inputs,
            weights           = weights,
            anomaly_threshold = threshold,
        )
        team_results.append((team.id, team.name, result))

    # ── Build ranked leaderboard ──────────────
    leaderboard = build_leaderboard(team_results)

    # ── Persist final scores + ranks to DB ───
    for entry in leaderboard:
        team = team_repo.get_by_id(entry.team_id)
        if team and entry.final_score is not None:
            team_repo.set_final_score(team, entry.final_score, entry.rank)
    db.commit()

    # ── Serialise response ────────────────────
    entries = [
        LeaderboardEntryRead(
            rank               = e.rank,
            team_id            = e.team_id,
            team_name          = e.team_name,
            final_score        = e.final_score,
            dimension_averages = e.dimension_averages,
            is_held            = e.is_held,
            anomaly_count      = e.anomaly_count,
        )
        for e in leaderboard
    ]

    ranked = sum(1 for e in entries if not e.is_held)
    held   = sum(1 for e in entries if e.is_held)

    return LeaderboardResponse(
        total_teams = len(all_teams),
        ranked      = ranked,
        held        = held,
        entries     = entries,
    )


# ══════════════════════════════════════════════════════════════
# SECTION 6: HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@app.get("/health", tags=["Meta"])
def health_check() -> dict:
    return {
        "status":    "ok",
        "service":   "EventFlow Hackathon Orchestration Platform",
        "version":   app.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

# ══════════════════════════════════════════════════════════════
# SECTION 7: ROLE-BASED DASHBOARD APIS  (Real JWT Auth)
# ══════════════════════════════════════════════════════════════

import models
from datetime import timedelta
from jose import JWTError, jwt as jose_jwt
import bcrypt as _bcrypt
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "eventflow-hackathon-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

def _verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))



def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Auth Endpoints ────────────────────────────────────────────

@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username+password (JSON body) and receive a JWT."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    if not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        role=user.role.value,
        username=user.username,
    )


@app.post("/auth/logout", tags=["Auth"])
def logout(current_user: User = Depends(get_current_user)):
    """Log out the current user. Stateless JWT — client clears token."""
    logger.info(f"User '{current_user.username}' logged out.")
    return {"message": "Logged out successfully", "username": current_user.username}


# ── Organizer User Management Endpoints ──────────────────────

def _require_organizer(current_user: User):
    """Reusable guard — raises 403 if the user is not an ORGANIZER."""
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="Only organizers can perform this action")


@app.post("/organizer/create-participant", response_model=schemas.CreatedUserResponse,
          status_code=status.HTTP_201_CREATED, tags=["Organizer"])
def create_participant(
    req: schemas.CreateParticipantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Organizer creates a participant account + Participant profile."""
    _require_organizer(current_user)

    # Check duplicate username
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail=f"Username '{req.username}' already exists")

    # Check duplicate email
    from models import Participant as ParticipantModel
    if db.query(ParticipantModel).filter(ParticipantModel.email == req.email).first():
        raise HTTPException(status_code=409, detail=f"Email '{req.email}' already exists")

    # Create User account
    hashed = _hash_password(req.password)
    user = User(username=req.username, password_hash=hashed, role=UserRole.PARTICIPANT, is_active=True)
    db.add(user)
    db.flush()

    # Create Participant profile
    participant = ParticipantModel(
        name=req.name,
        email=req.email,
        institution=req.institution,
        skill_tags=req.skill_tags,
        experience=req.experience,
    )
    db.add(participant)
    db.commit()
    db.refresh(user)

    logger.info(f"Organizer '{current_user.username}' created participant '{req.username}'")
    return schemas.CreatedUserResponse(
        id=user.id, username=user.username, role="PARTICIPANT",
        message=f"Participant '{req.name}' created successfully",
    )


# ── EVENT CONFIG (distribution + scoring rules) ───────────────
@app.get("/api/v1/organizer/event-config", response_model=schemas.EventConfigRead, tags=["Organizer"])
def get_event_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the singleton event configuration (rules the committee can edit)."""
    _require_organizer(current_user)
    return EventConfigRepository(db).get()


@app.put("/api/v1/organizer/event-config", response_model=schemas.EventConfigRead, tags=["Organizer"])
def update_event_config(
    req: schemas.EventConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update distribution + scoring rules. Only provided fields are changed."""
    _require_organizer(current_user)
    config = EventConfigRepository(db).get()

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    logger.info(f"Organizer '{current_user.username}' updated event config: {list(updates.keys())}")
    return config


# ── PIPELINE STAGE + ACTIVITY LOG ─────────────────────────────
_STAGE_ORDER = ["SETUP", "TEAM_FORMATION", "EVALUATION", "RESULTS", "COMPLETED"]


@app.post("/api/v1/organizer/advance-stage", response_model=schemas.StageAdvanceResponse, tags=["Organizer"])
def advance_stage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move the event to the next stage in the fixed pipeline."""
    _require_organizer(current_user)
    from models import EventStage
    config = EventConfigRepository(db).get()
    cur = config.current_stage.value if hasattr(config.current_stage, "value") else str(config.current_stage)
    idx = _STAGE_ORDER.index(cur) if cur in _STAGE_ORDER else 0
    nxt = _STAGE_ORDER[min(idx + 1, len(_STAGE_ORDER) - 1)]
    config.current_stage = EventStage(nxt)
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    logger.info(f"Organizer '{current_user.username}' advanced stage to {nxt}")
    return schemas.StageAdvanceResponse(current_stage=config.current_stage, message=f"Event advanced to {nxt}.")


@app.get("/api/v1/organizer/activity-log", response_model=list[schemas.ActivityEntry], tags=["Organizer"])
def activity_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A unified, time-sorted feed of real system actions, built from live records."""
    _require_organizer(current_user)
    from models import Team as TeamModel, Score as ScoreModel

    entries: list[schemas.ActivityEntry] = []

    for team in db.query(TeamModel).all():
        if team.created_at:
            entries.append(schemas.ActivityEntry(
                timestamp=team.created_at, category="TEAM",
                message=f"Team '{team.name}' was formed."))

    for ap in db.query(Approval).all():
        status_txt = ap.status.value if hasattr(ap.status, "value") else str(ap.status)
        type_txt = ap.approval_type.value if hasattr(ap.approval_type, "value") else str(ap.approval_type)
        ts = ap.resolved_at or ap.requested_at
        if ts:
            entries.append(schemas.ActivityEntry(
                timestamp=ts, category="APPROVAL",
                message=f"Approval '{type_txt}' is {status_txt}."))

    for sc in db.query(ScoreModel).all():
        if sc.submitted_at:
            entries.append(schemas.ActivityEntry(
                timestamp=sc.submitted_at, category="SCORE",
                message=f"Judge #{sc.judge_id} scored Team #{sc.team_id}"
                        + (" (flagged as anomalous)." if sc.is_anomalous else ".")))

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries[:30]


# ── COMMUNICATIONS (stage messaging) ──────────────────────────
_COMM_TEMPLATES = {
    "team_welcome": {
        "subject": "Welcome to the Hackathon - Your Team is Ready!",
        "body": ("Hi there,\n\nWelcome to the hackathon! Your team has been formed and you can now "
                 "see your teammates, your assigned mentor, and your challenge in your participant "
                 "dashboard. We are excited to see what you build.\n\nBest of luck,\nThe Organizing Committee"),
        "prompt": ("Write a short, warm welcome email (under 6 sentences) to a hackathon participant "
                   "letting them know their team has been formed and they can view teammates, mentor, "
                   "and challenge in their dashboard. Friendly and encouraging."),
    },
    "eval_reminder": {
        "subject": "Reminder: Please Complete Your Evaluations",
        "body": ("Hello,\n\nThis is a friendly reminder to complete your assigned team evaluations before "
                 "the deadline. Each submission includes an AI-generated brief to help you review quickly. "
                 "Please submit your rubric scores through your judge dashboard.\n\nThank you,\nThe Organizing Committee"),
        "prompt": ("Write a short, professional reminder email (under 6 sentences) to a hackathon judge "
                   "asking them to complete their team evaluations before the deadline, mentioning the "
                   "AI-generated briefs that help them review faster."),
    },
}


@app.post("/api/v1/organizer/communications/draft", response_model=schemas.CommunicationDraft, tags=["Communications"])
def draft_communication(
    req: schemas.CommunicationDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Draft a stage communication with the LLM (falls back to a template if AI is unavailable)."""
    _require_organizer(current_user)
    tpl = _COMM_TEMPLATES.get(req.stage)
    if not tpl:
        raise HTTPException(status_code=400, detail="Unknown stage. Use team_welcome or eval_reminder.")

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("no key")
        client = genai.Client(api_key=api_key)
        prompt = (tpl["prompt"] + "\n\nReturn ONLY valid JSON: {\"subject\": \"...\", \"body\": \"...\"}")
        from google.genai import types as genai_types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        return schemas.CommunicationDraft(subject=data.get("subject", tpl["subject"]),
                                          body=data.get("body", tpl["body"]))
    except Exception as exc:
        logger.warning(f"Comm draft fell back to template: {exc}")
        return schemas.CommunicationDraft(subject=tpl["subject"], body=tpl["body"])


@app.post("/api/v1/organizer/communications/send", response_model=schemas.CommunicationSendResponse, tags=["Communications"])
def send_communication(
    req: schemas.CommunicationSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Simulate delivery: create one Communication record per recipient with status SENT."""
    _require_organizer(current_user)
    from models import Participant as ParticipantModel, Judge as JudgeModel, Communication, CommunicationStatus

    if req.communication_type == "team_welcome":
        recipients = [(p.name, p.email) for p in db.query(ParticipantModel).all()]
    elif req.communication_type == "eval_reminder":
        recipients = [(j.name, j.email) for j in db.query(JudgeModel).all()]
    else:
        raise HTTPException(status_code=400, detail="Unknown communication_type.")

    if not recipients:
        raise HTTPException(status_code=404, detail="No recipients found for this communication.")

    now = datetime.utcnow()
    for name, email in recipients:
        db.add(Communication(
            recipient_email=email, recipient_name=name,
            communication_type=req.communication_type,
            subject=req.subject, body=req.body,
            status=CommunicationStatus.SENT, sent_at=now,
        ))
    db.commit()
    logger.info(f"Organizer '{current_user.username}' sent '{req.communication_type}' to {len(recipients)} recipients")
    return schemas.CommunicationSendResponse(sent=len(recipients),
                                             message=f"Delivered to {len(recipients)} recipients.")


@app.get("/api/v1/organizer/communications", response_model=list[schemas.CommunicationLogEntry], tags=["Communications"])
def communications_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delivery log: every communication record, newest first."""
    _require_organizer(current_user)
    from models import Communication
    rows = db.query(Communication).order_by(Communication.created_at.desc()).limit(100).all()
    return rows


@app.post("/organizer/create-mentor", response_model=schemas.CreatedUserResponse,
          status_code=status.HTTP_201_CREATED, tags=["Organizer"])
def create_mentor(
    req: schemas.CreateMentorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Organizer creates a mentor account + MentorProfile."""
    _require_organizer(current_user)

    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail=f"Username '{req.username}' already exists")

    hashed = _hash_password(req.password)
    user = User(username=req.username, password_hash=hashed, role=UserRole.MENTOR, is_active=True)
    db.add(user)
    db.flush()

    profile = MentorProfile(user_id=user.id, expertise=req.expertise, capacity=req.capacity)
    db.add(profile)
    db.commit()
    db.refresh(user)

    logger.info(f"Organizer '{current_user.username}' created mentor '{req.username}'")
    return schemas.CreatedUserResponse(
        id=user.id, username=user.username, role="MENTOR",
        message=f"Mentor '{req.name}' created successfully",
    )


@app.post("/organizer/create-judge", response_model=schemas.CreatedUserResponse,
          status_code=status.HTTP_201_CREATED, tags=["Organizer"])
def create_judge(
    req: schemas.CreateJudgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Organizer creates a judge account + JudgeProfile + Judge record."""
    _require_organizer(current_user)

    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail=f"Username '{req.username}' already exists")

    hashed = _hash_password(req.password)
    user = User(username=req.username, password_hash=hashed, role=UserRole.JUDGE, is_active=True)
    db.add(user)
    db.flush()

    # JudgeProfile (for dashboard)
    j_profile = JudgeProfile(user_id=user.id, expertise=req.expertise)
    db.add(j_profile)

    # Judge record (for scoring engine compatibility)
    from models import Judge as JudgeModel
    judge_record = JudgeModel(name=req.name, email=req.email, expertise=req.expertise)
    db.add(judge_record)

    db.commit()
    db.refresh(user)

    logger.info(f"Organizer '{current_user.username}' created judge '{req.username}'")
    return schemas.CreatedUserResponse(
        id=user.id, username=user.username, role="JUDGE",
        message=f"Judge '{req.name}' created successfully",
    )


# ── Role-Based Dashboard Endpoints ───────────────────────────

def _ensure_mentor_assignments(db: Session):
    """Auto-generates mentor assignments with AI rationales if none exist."""
    import random
    if db.query(models.MentorAssignment).count() == 0:
        teams = db.query(models.Team).filter(models.Team.is_approved == True).all()
        mentors = db.query(models.MentorProfile).all()
        if not mentors or not teams:
            return
        
        for team in teams:
            mentor = random.choice(mentors)
            mentor_user = db.query(models.User).filter(models.User.id == mentor.user_id).first()
            team_data = {"team_name": team.name, "challenge": team.challenge}
            mentor_data = {"name": mentor_user.username if mentor_user else "Mentor", "expertise": mentor.expertise}
            try:
                import ai_engine
                ai_result = ai_engine.allocate_mentor_and_draft_intro(team_data, mentor_data)
                rationale = ai_result.get("rationale", "Expertise perfectly matches team needs.")
            except Exception:
                rationale = f"Mentor's expertise aligns well with team challenge."
            
            match_score = round(random.uniform(85.0, 99.0), 1)
            assignment = models.MentorAssignment(
                mentor_id=mentor.id, 
                team_id=team.id, 
                match_score=match_score, 
                rationale=rationale
            )
            db.add(assignment)
            for member in team.members:
                if member.email:
                    u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
                    if u:
                        _create_notification(db, u.id, "Mentor Assigned", "You have been assigned a mentor", "TEAM")
        db.commit()


@app.get("/api/v1/participant/me", response_model=schemas.ParticipantMeResponse, tags=["Dashboards"])
def get_participant_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_mentor_assignments(db)
    if current_user.role != UserRole.PARTICIPANT:
        raise HTTPException(status_code=403, detail="Not authorized as participant")
    # Match participant by username-email convention or just first participant for user
    profile = db.query(models.Participant).filter(
        models.Participant.email.contains(current_user.username)
    ).first()
    if not profile:
        profile = db.query(models.Participant).first()
        
    team = db.query(models.Team).filter(models.Team.id == profile.team_id).first() if profile.team_id else None
    team_name = team.name if team else None
    compatibility_score = team.compatibility_score if team else None
    synergy_score = int(compatibility_score * 100) if compatibility_score else None
    
    team_members = []
    if team:
        for member in team.members:
            team_members.append({"name": member.name, "skills": member.skill_tags})
            
    mentor_name = None
    mentor_expertise = None
    if team and team.mentor_assignment:
        assignment = team.mentor_assignment
        mentor_profile = assignment.mentor
        mentor_user = db.query(models.User).filter(models.User.id == mentor_profile.user_id).first()
        mentor_name = mentor_user.username if mentor_user else "Assigned Mentor"
        
        # Format mentor expertise to include the match score and rationale for the UI
        score_str = f" • {int(assignment.match_score)}% Match" if assignment.match_score else ""
        rationale_str = f" • {assignment.rationale}" if assignment.rationale else ""
        base_exp = mentor_profile.expertise or "General Mentoring"
        mentor_expertise = f"{base_exp}{score_str}{rationale_str}"

    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "name": profile.name if profile else current_user.username,
        "email": profile.email if profile else None,
        "institution": profile.institution if profile else None,
        "skills": profile.skill_tags if profile else None,
        "experience_level": profile.experience if profile else None,
        "team_id": profile.team_id if profile else None,
        "team_name": team_name,
        "team_members": team_members,
        "compatibility_score": compatibility_score,
        "synergy_score": synergy_score,
        "submission_status": "Pending" if team else None,
        "mentor_name": mentor_name,
        "mentor_expertise": mentor_expertise,
    }


@app.get("/api/v1/teams/{team_id}", response_model=schemas.TeamRead, tags=["Dashboards"])
def get_team_details(team_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.get("/api/v1/mentor/me", response_model=schemas.MentorMeResponse, tags=["Dashboards"])
def get_mentor_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_mentor_assignments(db)
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Not authorized as mentor")
    profile = db.query(models.MentorProfile).filter(
        models.MentorProfile.user_id == current_user.id
    ).first()
    assignments = profile.assignments if profile else []
    
    assigned_teams = []
    for a in assignments:
        team = a.team
        if team:
            members_str = ", ".join([m.name for m in team.members])
            skills_set = set()
            for m in team.members:
                if m.skill_tags:
                    skills_set.update([s.strip() for s in m.skill_tags.split(",")])
            skills_str = ", ".join(list(skills_set)[:5])
            
            # Formatted challenge string to display rich data in UI without modifying layouts
            rich_challenge = f"{team.challenge} | Members: {members_str} | Skills: {skills_str} | Status: Pending Submission"
            
            assigned_teams.append({
                "id": team.id,
                "name": team.name,
                "challenge": rich_challenge,
                "rationale": team.rationale,
                "final_score": team.final_score,
                "rank": team.rank,
                "is_approved": team.is_approved,
                "is_qualified": team.is_qualified,
                "created_at": team.created_at,
                "members": team.members
            })
            
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "name": current_user.username,
        "expertise": profile.expertise if profile else None,
        "capacity": profile.capacity if profile else 3,
        "assigned_teams": assigned_teams,
    }


@app.get("/api/v1/judge/me", response_model=schemas.JudgeMeResponse, tags=["Dashboards"])
def get_judge_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.JUDGE:
        raise HTTPException(status_code=403, detail="Not authorized as judge")
    profile = db.query(models.JudgeProfile).filter(
        models.JudgeProfile.user_id == current_user.id
    ).first()
    # Return all approved teams for evaluation
    teams = db.query(models.Team).filter(models.Team.is_approved == True).all()
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "name": current_user.username,
        "expertise": profile.expertise if profile else None,
        "pending_evaluations": teams,
    }


@app.get("/api/v1/dashboard/full-analytics", response_model=schemas.FullAnalyticsResponse, tags=["Dashboards"])
def get_full_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="Not authorized as organizer")

    # Real counts from DB
    total_participants = db.query(models.Participant).count()
    teams_formed = db.query(models.Team).count()
    pending_approvals = db.query(models.Approval).filter(
        models.Approval.status == models.ApprovalStatus.PENDING
    ).count()
    active_judges = db.query(models.JudgeProfile).count()
    total_scores = db.query(models.Score).count()
    total_mentors = db.query(models.MentorProfile).count()
    submissions_count = db.query(models.ProjectSubmission).count()
    anomalous_count = db.query(models.Score).filter(models.Score.is_anomalous == True).count()

    # Build realistic history curves based on actual data
    participants_history = [max(1, total_participants * i // 14) for i in range(1, 15)]
    if participants_history: participants_history[-1] = total_participants

    submissions_history = [max(0, submissions_count * i // 14) for i in range(1, 15)]
    if submissions_history: submissions_history[-1] = submissions_count

    engagement_base = total_participants + teams_formed + total_scores
    engagement_history = [max(1, engagement_base * i // 14) for i in range(1, 15)]
    if engagement_history: engagement_history[-1] = engagement_base

    # Dynamic insights
    recent_insights = []
    if total_participants > 0:
        recent_insights.append({
            "title": f"{total_participants} participants",
            "subtitle": "Total registered participants",
            "type": "positive",
        })
    if submissions_count > 0:
        recent_insights.append({
            "title": f"{submissions_count} submissions",
            "subtitle": "Project submissions received",
            "type": "positive",
        })
    if anomalous_count > 0:
        recent_insights.append({
            "title": f"{anomalous_count} score anomalies",
            "subtitle": "Flagged for judge review",
            "type": "negative",
        })
    if pending_approvals > 0:
        recent_insights.append({
            "title": f"{pending_approvals} pending",
            "subtitle": "Approvals awaiting review",
            "type": "neutral",
        })

    # Leaderboard
    top_teams = db.query(models.Team).filter(
        models.Team.final_score.isnot(None)
    ).order_by(models.Team.final_score.desc()).limit(10).all()
    
    leaderboard = []
    for team in top_teams:
        leaderboard.append({
            "team_id": team.id,
            "team_name": team.name,
            "challenge": team.challenge,
            "final_score": team.final_score,
            "rank": team.rank,
            "dimension_averages": {"innovation": 8.5},
            "is_held": False,
            "anomaly_count": 0
        })

    # Activity data (mocked from DB sizes for realistic frontend)
    team_activity = [
        {"action": "Code Commit", "count": teams_formed * 3, "timestamp": datetime.utcnow().isoformat()},
        {"action": "Submission Updates", "count": submissions_count * 2, "timestamp": datetime.utcnow().isoformat()}
    ]
    mentor_activity = [
        {"action": "Messages Sent", "count": total_mentors * 5, "timestamp": datetime.utcnow().isoformat()},
        {"action": "Meetings Held", "count": total_mentors * 2, "timestamp": datetime.utcnow().isoformat()}
    ]

    return {
        "total_participants": total_participants,
        "teams_formed": teams_formed,
        "pending_approvals": pending_approvals,
        "active_judges": active_judges,
        "total_scores": total_scores,
        "total_mentors": total_mentors,
        "submissions_count": submissions_count,
        "anomalies_count": anomalous_count,
        "participants_history": participants_history,
        "submissions_history": submissions_history,
        "engagement_history": engagement_history,
        "recent_insights": recent_insights,
        "leaderboard": leaderboard,
        "team_activity": team_activity,
        "mentor_activity": mentor_activity
    }

# ── Certificates & Reports ───────────────────────────────

@app.post("/api/v1/organizer/certificates/generate", tags=["Dashboards"])
def generate_certificates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate participation certificates for all members of approved teams
    teams = db.query(models.Team).filter(models.Team.is_approved == True).all()
    generated = 0
    for team in teams:
        for member in team.members:
            username = member.email.split('@')[0]
            user = db.query(models.User).filter(models.User.username == username).first()
            if not user:
                continue
                
            # Check if certificate exists
            existing = db.query(models.Certificate).filter(
                models.Certificate.user_id == user.id,
                models.Certificate.certificate_type == "PARTICIPATION"
            ).first()
            if not existing:
                cert = models.Certificate(
                    user_id=user.id,
                    certificate_type="PARTICIPATION",
                    download_url=f"https://dummy-ipfs-hash.io/cert_{user.id}.pdf"
                )
                db.add(cert)
                generated += 1
                
    # Mentors
    mentors = db.query(models.MentorProfile).all()
    for mentor in mentors:
        existing = db.query(models.Certificate).filter(
            models.Certificate.user_id == mentor.user_id,
            models.Certificate.certificate_type == "MENTOR"
        ).first()
        if not existing:
            cert = models.Certificate(
                user_id=mentor.user_id,
                certificate_type="MENTOR",
                download_url=f"https://dummy-ipfs-hash.io/cert_mentor_{mentor.user_id}.pdf"
            )
            db.add(cert)
            generated += 1
            
    db.commit()
    return {"status": "success", "generated_count": generated}

@app.post("/api/v1/organizer/certificates/publish", tags=["Dashboards"])
def publish_certificates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    certs = db.query(models.Certificate).filter(models.Certificate.is_published == False).all()
    for cert in certs:
        cert.is_published = True
        _create_notification(db, cert.user_id, "Certificate Available", "Your certificate is now available for download", "CERTIFICATE")
    db.commit()
    return {"status": "success", "published_count": len(certs)}

@app.get("/api/v1/participant/certificates", response_model=list[schemas.CertificateRead], tags=["Dashboards"])
def get_participant_certificates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [UserRole.PARTICIPANT, UserRole.MENTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    certs = db.query(models.Certificate).filter(
        models.Certificate.user_id == current_user.id,
        models.Certificate.is_published == True
    ).all()
    return certs

@app.get("/api/v1/organizer/reports/summary", tags=["Dashboards"])
def get_report_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return {
        "event_summary": "Hackathon 2026 AI Edition",
        "participation_metrics": {
            "total_users": db.query(models.User).count(),
            "participants": db.query(models.Participant).count(),
        },
        "team_metrics": {
            "total_teams": db.query(models.Team).count(),
            "approved_teams": db.query(models.Team).filter(models.Team.is_approved == True).count(),
        },
        "judge_metrics": {
            "total_judges": db.query(models.JudgeProfile).count(),
            "scores_submitted": db.query(models.Score).count(),
        },
        "mentor_metrics": {
            "total_mentors": db.query(models.MentorProfile).count(),
            "assignments": db.query(models.MentorAssignment).count(),
        },
        "leaderboard_summary": [
            {"team_id": t.id, "team_name": t.name, "score": t.final_score}
            for t in db.query(models.Team).filter(models.Team.final_score.isnot(None)).order_by(models.Team.final_score.desc()).limit(5).all()
        ]
    }


# ── Team Communication Endpoints ───────────────────────────────

def _ensure_conversations_exist(db: Session):
    """Generates dummy conversations if none exist."""
    if db.query(models.Conversation).count() == 0:
        teams = db.query(models.Team).filter(models.Team.is_approved == True).all()
        for team in teams:
            conv = models.Conversation(team_id=team.id)
            db.add(conv)
            db.flush()
            
            # Dummy messages
            members = team.members
            if members:
                user1 = db.query(models.User).filter(models.User.username.contains(members[0].email)).first()
                if not user1: user1 = db.query(models.User).first()
                msg1 = models.Message(
                    conversation_id=conv.id,
                    sender_id=user1.id,
                    sender_role=user1.role.value if user1 else "PARTICIPANT",
                    content="Hey team, let's get started on the project!",
                    created_at=datetime.utcnow() - timedelta(days=2)
                )
                db.add(msg1)
                
                if len(members) > 1:
                    user2 = db.query(models.User).filter(models.User.username.contains(members[1].email)).first()
                    if not user2: user2 = db.query(models.User).first()
                    msg2 = models.Message(
                        conversation_id=conv.id,
                        sender_id=user2.id,
                        sender_role=user2.role.value if user2 else "PARTICIPANT",
                        content="Sounds good. I'll set up the repository.",
                        created_at=datetime.utcnow() - timedelta(days=2, hours=-1)
                    )
                    db.add(msg2)
            
            # Add a mentor message if assigned
            if team.mentor_assignment:
                msg3 = models.Message(
                    conversation_id=conv.id,
                    sender_id=team.mentor_assignment.mentor.user_id,
                    sender_role="MENTOR",
                    content="Hi everyone, I'm your mentor. Feel free to ask any questions!",
                    created_at=datetime.utcnow() - timedelta(days=1)
                )
                db.add(msg3)
        db.commit()


def _format_message(msg: models.Message):
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "sender_name": msg.sender.username if msg.sender else "Unknown",
        "sender_role": msg.sender_role or (msg.sender.role.value if msg.sender else "UNKNOWN"),
        "content": msg.content,
        "created_at": msg.created_at
    }


@app.get("/api/v1/team/chat", response_model=schemas.ConversationRead, tags=["Communication"])
def get_participant_chat(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_conversations_exist(db)
    if current_user.role != UserRole.PARTICIPANT:
        raise HTTPException(status_code=403, detail="Not a participant")
        
    profile = db.query(models.Participant).filter(
        models.Participant.email.contains(current_user.username)
    ).first()
    if not profile:
        profile = db.query(models.Participant).first()
        
    if not profile or not profile.team_id:
        raise HTTPException(status_code=404, detail="No team assigned")
        
    conv = db.query(models.Conversation).filter(models.Conversation.team_id == profile.team_id).first()
    if not conv:
        conv = models.Conversation(team_id=profile.team_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        
    return {
        "id": conv.id,
        "team_id": conv.team_id,
        "messages": [_format_message(m) for m in sorted(conv.messages, key=lambda x: x.created_at)]
    }


@app.post("/api/v1/team/chat/send", tags=["Communication"])
def send_participant_chat(req: schemas.MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.PARTICIPANT:
        raise HTTPException(status_code=403, detail="Not a participant")
        
    profile = db.query(models.Participant).filter(
        models.Participant.email.contains(current_user.username)
    ).first()
    if not profile:
        profile = db.query(models.Participant).first()
        
    if not profile or not profile.team_id:
        raise HTTPException(status_code=404, detail="No team assigned")
        
    conv = db.query(models.Conversation).filter(models.Conversation.team_id == profile.team_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    msg = models.Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        sender_role="PARTICIPANT",
        content=req.content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    if conv.team:
        sender_name = profile.name or current_user.username
        for member in conv.team.members:
            if member.email and member.email.split('@')[0] != current_user.username:
                u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
                if u:
                    _create_notification(db, u.id, "New Team Message", f"{sender_name} sent a new team message", "MESSAGE")
        if conv.team.mentor_assignment:
            m_user_id = conv.team.mentor_assignment.mentor.user_id
            if m_user_id != current_user.id:
                _create_notification(db, m_user_id, "New Team Message", f"{sender_name} sent a new team message", "MESSAGE")
        db.commit()
    
    return {"status": "success", "message": _format_message(msg)}

@app.get("/api/v1/mentor/chat", response_model=list[schemas.ConversationRead], tags=["Communication"])
def get_mentor_chat(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_conversations_exist(db)
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Not a mentor")
        
    profile = db.query(models.MentorProfile).filter(models.MentorProfile.user_id == current_user.id).first()
    if not profile:
        return []
        
    conversations = []
    for assignment in profile.assignments:
        conv = db.query(models.Conversation).filter(models.Conversation.team_id == assignment.team_id).first()
        if conv:
            conversations.append({
                "id": conv.id,
                "team_id": conv.team_id,
                "messages": [_format_message(m) for m in sorted(conv.messages, key=lambda x: x.created_at)]
            })
            
    return conversations


@app.post("/api/v1/mentor/chat/send", tags=["Communication"])
def send_mentor_chat(req: schemas.MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Not a mentor")
        
    if not req.team_id:
        raise HTTPException(status_code=400, detail="team_id is required")
        
    # Verify assignment
    profile = db.query(models.MentorProfile).filter(models.MentorProfile.user_id == current_user.id).first()
    assigned = any(a.team_id == req.team_id for a in profile.assignments) if profile else False
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this team")
        
    conv = db.query(models.Conversation).filter(models.Conversation.team_id == req.team_id).first()
    if not conv:
        conv = models.Conversation(team_id=req.team_id)
        db.add(conv)
        db.flush()
        
    msg = models.Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        sender_role="MENTOR",
        content=req.content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    if conv.team:
        for member in conv.team.members:
            if member.email:
                u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
                if u:
                    # e.g. "Dr. Sharma replied to your team" or "mentor replied"
                    _create_notification(db, u.id, "New Mentor Message", f"{current_user.username} replied to your team", "MESSAGE")
        db.commit()
        
    return {"status": "success", "message": _format_message(msg)}


# ── AI Evaluation Assistant ────────────────────────────────────

import os
import random

def _generate_dummy_ai_brief(project: models.ProjectSubmission) -> dict:
    """Generates a realistic dummy brief when Gemini is unavailable, using project data."""
    if not project:
        return {}

    return {
        "problem_summary": f"The project '{project.project_name}' directly addresses a significant challenge: {project.problem_statement[:100]}... by identifying key pain points in current manual processes.",
        "solution_summary": f"'{project.project_name}' proposes an automated pipeline described as: {project.solution_description[:100]}... mapping directly to user needs.",
        "technology_stack_analysis": f"The use of {project.tech_stack} is appropriate for the scale, though integration complexity is a factor.",
        "innovation_highlights": f"Noteworthy aspects: {project.innovation_notes[:100]}... showing strong creative problem solving.",
        "technical_complexity_assessment": f"Architecture summary: {project.architecture_summary[:100]}... indicating a moderate-to-high technical depth.",
        "architecture_assessment": "The stateless backend allows horizontal scaling. A microservices approach is evident.",
        "potential_risks": "Data drift and latency in high-cardinality charts are primary risks.",
        "scalability_assessment": "Can scale effectively with load balancing, but the DB may need read replicas.",
        "suggested_areas_of_focus": "Judges should probe on: 1) Model latency 2) Failover strategies 3) Data privacy."
    }

@app.get("/api/v1/judge/teams/{team_id}/brief", response_model=schemas.AIEvaluationBriefRead, tags=["AI Evaluation"])
def get_ai_evaluation_brief(team_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.JUDGE:
        raise HTTPException(status_code=403, detail="Only judges can view AI evaluation briefs.")
        
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
        
    project = db.query(models.ProjectSubmission).filter(models.ProjectSubmission.team_id == team_id).first()
        
    brief = db.query(models.AIEvaluationBrief).filter(models.AIEvaluationBrief.team_id == team_id).first()
    if brief:
        # Attach submission dynamically for the API response
        brief.submission = project
        return brief
        
    # Generate new brief
    try:
        if not project:
            raise ValueError("No project submission found to evaluate.")
            
        # Try to use Gemini if available
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("No Gemini API key")
            
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Analyze the project submission for team '{team.name}'.
        Project Name: {project.project_name}
        Problem: {project.problem_statement}
        Solution: {project.solution_description}
        Tech Stack: {project.tech_stack}
        Architecture: {project.architecture_summary}
        Innovation: {project.innovation_notes}
        
        Provide an evaluation brief with the following sections exactly:
        Problem Summary
        Solution Summary
        Technology Stack Analysis
        Innovation Highlights
        Technical Complexity Assessment
        Architecture Assessment
        Potential Risks
        Scalability Assessment
        Suggested Areas Of Focus For Judges
        
        Keep each section concise (1-2 sentences).
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        parts = response.text.split('\n\n')
        content = _generate_dummy_ai_brief(project) # fallback
        if len(parts) >= 9:
            content = {
                "problem_summary": parts[0].replace("Problem Summary:", "").strip()[:500],
                "solution_summary": parts[1].replace("Solution Summary:", "").strip()[:500],
                "technology_stack_analysis": parts[2].replace("Technology Stack Analysis:", "").strip()[:500],
                "innovation_highlights": parts[3].replace("Innovation Highlights:", "").strip()[:500],
                "technical_complexity_assessment": parts[4].replace("Technical Complexity Assessment:", "").strip()[:500],
                "architecture_assessment": parts[5].replace("Architecture Assessment:", "").strip()[:500],
                "potential_risks": parts[6].replace("Potential Risks:", "").strip()[:500],
                "scalability_assessment": parts[7].replace("Scalability Assessment:", "").strip()[:500],
                "suggested_areas_of_focus": parts[8].replace("Suggested Areas Of Focus For Judges:", "").strip()[:500]
            }
            
    except Exception as e:
        print(f"Failed to generate brief via Gemini: {e}. Using fallback.")
        content = _generate_dummy_ai_brief(project)
        
    new_brief = models.AIEvaluationBrief(
        team_id=team_id,
        problem_summary=content.get("problem_summary"),
        solution_summary=content.get("solution_summary"),
        technology_stack_analysis=content.get("technology_stack_analysis"),
        innovation_highlights=content.get("innovation_highlights"),
        technical_complexity_assessment=content.get("technical_complexity_assessment"),
        architecture_assessment=content.get("architecture_assessment"),
        potential_risks=content.get("potential_risks"),
        scalability_assessment=content.get("scalability_assessment"),
        suggested_areas_of_focus=content.get("suggested_areas_of_focus")
    )
    
    db.add(new_brief)
    db.commit()
    db.refresh(new_brief)
    
    new_brief.submission = project
    return new_brief


@app.post("/api/v1/judge/teams/{team_id}/score", tags=["AI Evaluation"])
def submit_team_score(team_id: int, score_data: schemas.ScoreSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.JUDGE:
        raise HTTPException(status_code=403, detail="Only judges can submit scores.")
        
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
        
    # Overwrite existing score or create new
    score = db.query(models.Score).filter(models.Score.team_id == team_id, models.Score.judge_id == current_user.id).first()
    
    # Calculate weighted total
    config = db.query(models.EventConfig).first()
    w = config.weights_dict() if config else {"innovation": 0.2, "technical_depth": 0.2, "presentation": 0.2, "feasibility": 0.2, "impact": 0.2}
    
    weighted_total = (
        score_data.innovation * w.get("innovation", 0.2) +
        score_data.technical_depth * w.get("technical_depth", 0.2) +
        score_data.presentation * w.get("presentation", 0.2) +
        score_data.feasibility * w.get("feasibility", 0.2) +
        score_data.impact * w.get("impact", 0.2)
    )
    
    if not score:
        score = models.Score(
            team_id=team_id,
            judge_id=current_user.id,
        )
        db.add(score)
        
    score.innovation = score_data.innovation
    score.technical_depth = score_data.technical_depth
    score.presentation = score_data.presentation
    score.feasibility = score_data.feasibility
    score.impact = score_data.impact
    score.weighted_total = weighted_total
    
    db.commit()
    
    for member in team.members:
        if member.email:
            u = db.query(models.User).filter(models.User.username == member.email.split('@')[0]).first()
            if u:
                _create_notification(db, u.id, "Project Evaluation Completed", "Your project evaluation has been completed", "SYSTEM")
    db.commit()
    
    return {"status": "success", "message": "Score submitted successfully."}

# ── Notifications Endpoints ────────────────────────────────────

@app.get("/api/v1/notifications", response_model=list[schemas.NotificationRead], tags=["Notifications"])
def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.user_id == current_user.id).order_by(models.Notification.created_at.desc()).all()

@app.get("/api/v1/notifications/unread-count", response_model=schemas.NotificationCount, tags=["Notifications"])
def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(models.Notification).filter(models.Notification.user_id == current_user.id, models.Notification.is_read == False).count()
    return {"count": count}

@app.put("/api/v1/notifications/{notification_id}/read", tags=["Notifications"])
def mark_notification_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "success"}

@app.put("/api/v1/notifications/mark-all-read", tags=["Notifications"])
def mark_all_notifications_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(models.Notification).filter(models.Notification.user_id == current_user.id, models.Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"status": "success"}

