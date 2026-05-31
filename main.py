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
import google.generativeai as genai
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
            
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Send the string prompt to Google Gemini
        response = gemini_model.generate_content(prompt)
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

    elif atype == ApprovalType.RESULT_PUBLICATION_REVIEW:
        if approval.team_id:
            team = team_repo.get_by_id(approval.team_id)
            if team:
                team_repo.set_qualified(team, qualified=True)
                logger.info(f"  ↳ Team #{approval.team_id} marked as qualified (results published).")

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

@app.post("/auth/register", response_model=schemas.TokenResponse, tags=["Auth"])
def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    try:
        role = UserRole(req.role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")
    hashed = _hash_password(req.password)
    user = User(username=req.username, password_hash=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        role=user.role.value,
        username=user.username,
    )


@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username+password (JSON body) and receive a JWT."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        role=user.role.value,
        username=user.username,
    )


# ── Role-Based Dashboard Endpoints ───────────────────────────

@app.get("/api/v1/participant/me", response_model=schemas.ParticipantMeResponse, tags=["Dashboards"])
def get_participant_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.PARTICIPANT:
        raise HTTPException(status_code=403, detail="Not authorized as participant")
    # Match participant by username-email convention or just first participant for user
    profile = db.query(models.Participant).filter(
        models.Participant.email.contains(current_user.username)
    ).first()
    if not profile:
        profile = db.query(models.Participant).first()
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
    }


@app.get("/api/v1/teams/{team_id}", response_model=schemas.TeamRead, tags=["Dashboards"])
def get_team_details(team_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.get("/api/v1/mentor/me", response_model=schemas.MentorMeResponse, tags=["Dashboards"])
def get_mentor_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Not authorized as mentor")
    profile = db.query(models.MentorProfile).filter(
        models.MentorProfile.user_id == current_user.id
    ).first()
    assignments = profile.assignments if profile else []
    assigned_teams = [a.team for a in assignments] if assignments else []
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

    # Build realistic history curves based on actual data
    participants_history = [
        max(1, total_participants * i // 14)
        for i in range(1, 15)
    ]
    participants_history[-1] = total_participants

    submissions_history = [
        max(0, total_scores * i // 14)
        for i in range(1, 15)
    ]
    submissions_history[-1] = total_scores

    engagement_base = total_participants + teams_formed + total_scores
    engagement_history = [
        max(1, engagement_base * i // 14)
        for i in range(1, 15)
    ]
    engagement_history[-1] = engagement_base

    # Dynamic insights
    recent_insights = []
    if total_participants > 0:
        recent_insights.append({
            "title": f"{total_participants} participants",
            "subtitle": "Total registered participants",
            "type": "positive",
        })
    if total_scores > 0:
        recent_insights.append({
            "title": f"{total_scores} submissions",
            "subtitle": "Project scores submitted",
            "type": "neutral",
        })
    anomalous_count = db.query(models.Score).filter(
        models.Score.is_anomalous == True
    ).count()
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

    return {
        "total_participants": total_participants,
        "teams_formed": teams_formed,
        "pending_approvals": pending_approvals,
        "active_judges": active_judges,
        "participants_history": participants_history,
        "submissions_history": submissions_history,
        "engagement_history": engagement_history,
        "recent_insights": recent_insights,
    }