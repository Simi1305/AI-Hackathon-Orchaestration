"""
schemas.py
──────────
Pydantic v2 schemas for request validation and response serialisation.

Design philosophy:
  - Separate `Create` (input) and `Read` (output) schemas for every resource.
    This follows the Command-Query Responsibility Segregation (CQRS) principle
    at the schema layer — inputs are strict; outputs carry computed/DB fields.
  - `model_config = ConfigDict(from_attributes=True)` on every Read schema
    enables ORM-mode so FastAPI can serialise SQLAlchemy model instances
    directly without manual `.dict()` calls.
  - Enum types are re-exported from models so route handlers never need to
    import from models for validation purposes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic import ConfigDict

# Re-export enums so callers import from a single place
from models import (
    ApprovalType,
    ApprovalStatus,
    EventStage,
    CommunicationStatus,
    UserRole,
)


# ══════════════════════════════════════════════════════════════
# PARTICIPANT
# ══════════════════════════════════════════════════════════════

class ParticipantCreate(BaseModel):
    """Payload for registering a single participant."""

    name:        str        = Field(..., min_length=2, max_length=120)
    email:       EmailStr
    institution: str        = Field(..., min_length=2, max_length=200)
    skill_tags:  str        = Field(
        ...,
        description="Comma-separated skill list, e.g. 'ML,Backend,DevOps'",
        examples=["ML,Python,Docker"],
    )
    experience:  str        = Field(
        ...,
        pattern="^(junior|mid|senior)$",
        description="Must be one of: junior | mid | senior",
    )

    @field_validator("skill_tags")
    @classmethod
    def normalise_skills(cls, v: str) -> str:
        """Strip whitespace around each tag; remove empty tags."""
        cleaned = ",".join(s.strip() for s in v.split(",") if s.strip())
        if not cleaned:
            raise ValueError("skill_tags must contain at least one non-empty skill.")
        return cleaned


class ParticipantRead(BaseModel):
    """Full participant row returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id:          int
    name:        str
    email:       str
    institution: str
    skill_tags:  str
    experience:  str
    team_id:     Optional[int]


class RosterUpload(BaseModel):
    """Bulk participant ingestion payload."""

    participants: list[ParticipantCreate] = Field(
        ..., min_length=1, description="At least one participant required."
    )


class RosterUploadResponse(BaseModel):
    created:    int
    skipped:    int   # duplicates by email
    message:    str


# ══════════════════════════════════════════════════════════════
# APPROVAL GATE
# ══════════════════════════════════════════════════════════════

class ApprovalCreate(BaseModel):
    """Create a new approval gate manually (most are auto-created by engines)."""

    approval_type: ApprovalType
    team_id:       Optional[int]  = None
    reference_id:  Optional[int]  = None
    payload:       Optional[str]  = Field(
        None, description="JSON-serialised preview data for the committee dashboard."
    )


class ApprovalRead(BaseModel):
    """Full approval record with audit trail."""

    model_config = ConfigDict(from_attributes=True)

    id:            int
    approval_type: ApprovalType
    status:        ApprovalStatus
    team_id:       Optional[int]
    reference_id:  Optional[int]
    payload:       Optional[str]
    requested_at:  datetime
    resolved_at:   Optional[datetime]
    resolved_by:   Optional[str]
    reject_reason: Optional[str]


class ApprovalRejectRequest(BaseModel):
    """Body for the reject endpoint — reason is mandatory for auditability."""

    reason:      str  = Field(..., min_length=5, max_length=1000)
    resolved_by: str  = Field(..., min_length=2, max_length=200)


class ApprovalApproveRequest(BaseModel):
    """Body for the approve endpoint."""

    resolved_by: str = Field(..., min_length=2, max_length=200)


# ══════════════════════════════════════════════════════════════
# JUDGE
# ══════════════════════════════════════════════════════════════

class JudgeCreate(BaseModel):
    name:      str       = Field(..., min_length=2, max_length=120)
    email:     EmailStr
    expertise: Optional[str] = None


class JudgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:        int
    name:      str
    email:     str
    expertise: Optional[str]


# ══════════════════════════════════════════════════════════════
# SCORE SUBMISSION  (maps 1-to-1 with JudgeScoreInput dataclass)
# ══════════════════════════════════════════════════════════════

class ScoreSubmit(BaseModel):
    """
    Score submission payload from a judge portal.

    Each rubric dimension is validated to be in [0, 10].
    Mirrors `scoring_engine.JudgeScoreInput` exactly so we can unpack
    this schema directly into that dataclass.
    """

    team_id:         int
    judge_id:        int
    innovation:      float = Field(..., ge=0.0, le=10.0)
    technical_depth: float = Field(..., ge=0.0, le=10.0)
    presentation:    float = Field(..., ge=0.0, le=10.0)
    feasibility:     float = Field(..., ge=0.0, le=10.0)
    impact:          float = Field(..., ge=0.0, le=10.0)
    notes:           Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def check_not_all_zero(self) -> "ScoreSubmit":
        dims = [self.innovation, self.technical_depth,
                self.presentation, self.feasibility, self.impact]
        if all(d == 0.0 for d in dims):
            raise ValueError(
                "All rubric scores are 0.0 — this looks like an unintentional submission."
            )
        return self


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    team_id:         int
    judge_id:        int
    innovation:      Optional[float]
    technical_depth: Optional[float]
    presentation:    Optional[float]
    feasibility:     Optional[float]
    impact:          Optional[float]
    weighted_total:  Optional[float]
    is_anomalous:    bool
    submitted_at:    datetime
    notes:           Optional[str]


# ══════════════════════════════════════════════════════════════
# TEAM
# ══════════════════════════════════════════════════════════════

class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    name:         str
    challenge:    Optional[str]
    rationale:    Optional[str]
    final_score:  Optional[float]
    rank:         Optional[int]
    is_approved:  bool
    is_qualified: bool
    created_at:   datetime
    members:      list[ParticipantRead]


# ══════════════════════════════════════════════════════════════
# TEAM FORMATION TRIGGER
# ══════════════════════════════════════════════════════════════

class TeamFormationConfig(BaseModel):
    """Optional overrides for a single formation run (defaults come from EventConfig)."""

    team_size:            Optional[int] = Field(None, ge=2, le=10)
    max_same_institution: Optional[int] = Field(None, ge=1)
    shuffle_seed:         Optional[int] = None


class TeamFormationResponse(BaseModel):
    teams_formed:    int
    approvals_queued: int
    warnings:        list[str]
    team_ids:        list[int]


# ══════════════════════════════════════════════════════════════
# LEADERBOARD
# ══════════════════════════════════════════════════════════════

class LeaderboardEntryRead(BaseModel):
    """
    Serialisable version of scoring_engine.LeaderboardEntry.
    We don't use `from_attributes` here because LeaderboardEntry is a
    dataclass, not a SQLAlchemy model — direct construction is cleaner.
    """

    rank:               int
    team_id:            int
    team_name:          str
    final_score:        Optional[float]
    dimension_averages: dict[str, float]
    is_held:            bool
    anomaly_count:      int


class LeaderboardResponse(BaseModel):
    total_teams:    int
    ranked:         int          # teams with a score
    held:           int          # teams held pending anomaly resolution
    entries:        list[LeaderboardEntryRead]


# ══════════════════════════════════════════════════════════════
# GENERIC RESPONSES
# ══════════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    """Simple acknowledgement / status message."""
    message: str
    detail:  Optional[Any] = None


class ErrorResponse(BaseModel):
    error:  str
    detail: Optional[Any] = None

# ══════════════════════════════════════════════════════════════
# DASHBOARD RESPONSES
# ══════════════════════════════════════════════════════════════

class ParticipantMeResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    institution: Optional[str] = None
    skills: Optional[str] = None
    experience_level: Optional[str] = None
    github_url: Optional[str] = None
    team_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class MentorMeResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    expertise: Optional[str] = None
    capacity: int = 1
    assigned_teams: list[TeamRead] = []
    
    class Config:
        from_attributes = True

class JudgeMeResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    expertise: Optional[str] = None
    pending_evaluations: list[TeamRead] = []
    
    class Config:
        from_attributes = True

class FullAnalyticsResponse(BaseModel):
    total_participants: int
    teams_formed: int
    pending_approvals: int
    active_judges: int
    participants_history: list[int]
    submissions_history: list[int]
    engagement_history: list[int]
    recent_insights: list[dict]


# ══════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ══════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "PARTICIPANT"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str