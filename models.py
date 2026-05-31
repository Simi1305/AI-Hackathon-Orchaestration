from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    ForeignKey, Text, DateTime, Enum
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum


# ──────────────────────────────────────────────
# ENUMS  (used as DB-level constraints)
# ──────────────────────────────────────────────

class ApprovalType(str, enum.Enum):
    TEAM_REVIEW                 = "TEAM_REVIEW"
    MENTOR_ASSIGNMENT_REVIEW    = "MENTOR_ASSIGNMENT_REVIEW"
    MESSAGE_SENDING_REVIEW      = "MESSAGE_SENDING_REVIEW"
    ANOMALY_REVIEW              = "ANOMALY_REVIEW"
    RESULT_PUBLICATION_REVIEW   = "RESULT_PUBLICATION_REVIEW"
    PROGRESSION_INVITE_REVIEW   = "PROGRESSION_INVITE_REVIEW"


class ApprovalStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class EventStage(str, enum.Enum):
    SETUP           = "SETUP"
    TEAM_FORMATION  = "TEAM_FORMATION"
    EVALUATION      = "EVALUATION"
    RESULTS         = "RESULTS"
    COMPLETED       = "COMPLETED"


class CommunicationStatus(str, enum.Enum):
    DRAFTED   = "DRAFTED"
    PENDING   = "PENDING"      # awaiting approval
    SENT      = "SENT"
    FAILED    = "FAILED"


class UserRole(str, enum.Enum):
    ORGANIZER   = "ORGANIZER"
    PARTICIPANT = "PARTICIPANT"
    MENTOR      = "MENTOR"
    JUDGE       = "JUDGE"


# ──────────────────────────────────────────────
# PARTICIPANT
# ──────────────────────────────────────────────

class Participant(Base):
    __tablename__ = "participants"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, index=True)
    email       = Column(String, unique=True, index=True)
    institution = Column(String)
    skill_tags  = Column(String)   # comma-separated e.g. "ML,Backend,DevOps"
    experience  = Column(String)   # "junior" | "mid" | "senior"
    team_id     = Column(Integer, ForeignKey("teams.id"), nullable=True)
    jwt_token   = Column(String, nullable=True)   # signed participant portal token

    # ── relationships ──
    team = relationship("Team", back_populates="members")

    def skills_list(self) -> list[str]:
        """Helper: return skill_tags as a Python list."""
        if not self.skill_tags:
            return []
        return [s.strip() for s in self.skill_tags.split(",") if s.strip()]

    def __repr__(self):
        return f"<Participant {self.name} | {self.institution} | {self.skill_tags}>"


# ──────────────────────────────────────────────
# TEAM
# ──────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String, unique=True)           # e.g. "Team Orion"
    challenge           = Column(String, nullable=True)         # assigned problem/track
    rationale           = Column(Text, nullable=True)           # LLM-generated rationale
    compatibility_score = Column(Float, nullable=True)          # team compatibility metric
    final_score         = Column(Float, nullable=True)          # consolidated score
    rank                = Column(Integer, nullable=True)        # leaderboard rank
    is_approved         = Column(Boolean, default=False)        # committee approved?
    is_qualified        = Column(Boolean, default=False)        # qualified for next round?
    created_at          = Column(DateTime, default=datetime.utcnow)

    # ── relationships ──
    members           = relationship("Participant", back_populates="team")
    scores            = relationship("Score", back_populates="team")
    approvals         = relationship("Approval", back_populates="team")
    mentor_assignment = relationship("MentorAssignment", back_populates="team", uselist=False)

    def skill_coverage(self) -> dict[str, int]:
        """Returns a frequency map of all skills across team members."""
        coverage: dict[str, int] = {}
        for member in self.members:
            for skill in member.skills_list():
                coverage[skill] = coverage.get(skill, 0) + 1
        return coverage

    def __repr__(self):
        return f"<Team {self.name} | score={self.final_score}>"


# ──────────────────────────────────────────────
# MENTOR ASSIGNMENT
# ──────────────────────────────────────────────

class MentorAssignment(Base):
    __tablename__ = "mentor_assignments"

    id         = Column(Integer, primary_key=True, index=True)
    mentor_id  = Column(Integer, ForeignKey("mentor_profiles.id"))
    team_id    = Column(Integer, ForeignKey("teams.id"), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── relationships ──
    mentor = relationship("MentorProfile", back_populates="assignments")
    team   = relationship("Team", back_populates="mentor_assignment")

    def __repr__(self):
        return f"<MentorAssignment mentor={self.mentor_id} team={self.team_id}>"


# ──────────────────────────────────────────────
# JUDGE / EVALUATOR
# ──────────────────────────────────────────────

class Judge(Base):
    __tablename__ = "judges"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String)
    email       = Column(String, unique=True, index=True)
    expertise   = Column(String, nullable=True)   # e.g. "ML, Systems"
    jwt_token   = Column(String, nullable=True)   # signed evaluator portal token

    # ── relationships ──
    scores = relationship("Score", back_populates="judge")

    def __repr__(self):
        return f"<Judge {self.name}>"


# ──────────────────────────────────────────────
# SCORE  (one row per judge per team)
# ──────────────────────────────────────────────

class Score(Base):
    __tablename__ = "scores"

    id              = Column(Integer, primary_key=True, index=True)
    team_id         = Column(Integer, ForeignKey("teams.id"))
    judge_id        = Column(Integer, ForeignKey("judges.id"))

    # Granular rubric scores (each out of 10)
    innovation      = Column(Float, nullable=True)
    technical_depth = Column(Float, nullable=True)
    presentation    = Column(Float, nullable=True)
    feasibility     = Column(Float, nullable=True)
    impact          = Column(Float, nullable=True)

    weighted_total  = Column(Float, nullable=True)   # computed after submission
    is_anomalous    = Column(Boolean, default=False) # flagged by anomaly engine
    submitted_at    = Column(DateTime, default=datetime.utcnow)
    notes           = Column(Text, nullable=True)    # judge's qualitative notes

    # ── relationships ──
    team  = relationship("Team", back_populates="scores")
    judge = relationship("Judge", back_populates="scores")

    def __repr__(self):
        return f"<Score team={self.team_id} judge={self.judge_id} total={self.weighted_total}>"


# ──────────────────────────────────────────────
# APPROVAL GATE
# ──────────────────────────────────────────────

class Approval(Base):
    __tablename__ = "approvals"

    id              = Column(Integer, primary_key=True, index=True)
    approval_type   = Column(Enum(ApprovalType))
    status          = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)

    # Context — what is being approved?
    team_id         = Column(Integer, ForeignKey("teams.id"), nullable=True)
    reference_id    = Column(Integer, nullable=True)   # generic FK (score_id, comm_id, etc.)
    payload         = Column(Text, nullable=True)      # JSON blob — preview data for committee

    # Audit trail
    requested_at    = Column(DateTime, default=datetime.utcnow)
    resolved_at     = Column(DateTime, nullable=True)
    resolved_by     = Column(String, nullable=True)    # committee member name/id
    reject_reason   = Column(Text, nullable=True)

    # ── relationships ──
    team = relationship("Team", back_populates="approvals")

    # ── valid state transitions ──
    TRANSITIONS: dict = {
        ApprovalStatus.PENDING:  [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED],
        ApprovalStatus.APPROVED: [ApprovalStatus.EXECUTED],
        ApprovalStatus.REJECTED: [ApprovalStatus.PENDING],   # after reconfiguration
        ApprovalStatus.EXECUTED: [],                          # terminal state
    }

    def can_transition_to(self, new_status: ApprovalStatus) -> bool:
        return new_status in self.TRANSITIONS.get(self.status, [])

    def __repr__(self):
        return f"<Approval {self.approval_type} | {self.status}>"


# ──────────────────────────────────────────────
# COMMUNICATION LOG
# ──────────────────────────────────────────────

class Communication(Base):
    __tablename__ = "communications"

    id                 = Column(Integer, primary_key=True, index=True)
    recipient_email    = Column(String)
    recipient_name     = Column(String)
    communication_type = Column(String)   # e.g. "email", "notification"
    subject            = Column(String)
    body               = Column(Text)
    status             = Column(Enum(CommunicationStatus), default=CommunicationStatus.DRAFTED)
    event_stage        = Column(Enum(EventStage), nullable=True)   # which pipeline stage triggered this
    approval_id        = Column(Integer, ForeignKey("approvals.id"), nullable=True)
    sent_at            = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Communication to={self.recipient_email} | {self.status}>"


# ──────────────────────────────────────────────
# EVENT STATE  (single-row config table)
# ──────────────────────────────────────────────

class EventConfig(Base):
    __tablename__ = "event_config"

    id                      = Column(Integer, primary_key=True, default=1)
    event_name              = Column(String, default="Hackathon 2025")
    current_stage           = Column(Enum(EventStage), default=EventStage.SETUP)

    # Team formation rules
    team_size               = Column(Integer, default=3)
    max_same_institution    = Column(Integer, default=1)
    required_skills         = Column(String, nullable=True)  # comma-separated

    # Scoring weights (must sum to 1.0)
    weight_innovation       = Column(Float, default=0.25)
    weight_technical_depth  = Column(Float, default=0.30)
    weight_presentation     = Column(Float, default=0.15)
    weight_feasibility      = Column(Float, default=0.15)
    weight_impact           = Column(Float, default=0.15)

    # Anomaly detection threshold (std deviations)
    anomaly_threshold       = Column(Float, default=2.0)

    updated_at              = Column(DateTime, default=datetime.utcnow)

    def weights_dict(self) -> dict[str, float]:
        return {
            "innovation":       self.weight_innovation,
            "technical_depth":  self.weight_technical_depth,
            "presentation":     self.weight_presentation,
            "feasibility":      self.weight_feasibility,
            "impact":           self.weight_impact,
        }

    def __repr__(self):
        return f"<EventConfig stage={self.current_stage}>"


# ──────────────────────────────────────────────
# USER (authentication)
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)
    role          = Column(Enum(UserRole), default=UserRole.PARTICIPANT)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username} | {self.role}>"


# ──────────────────────────────────────────────
# MENTOR PROFILE
# ──────────────────────────────────────────────

class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), unique=True)
    expertise = Column(String, nullable=True)
    capacity  = Column(Integer, default=3)

    # ── relationships ──
    user        = relationship("User")
    assignments = relationship("MentorAssignment", back_populates="mentor")

    def __repr__(self):
        return f"<MentorProfile user_id={self.user_id}>"


# ──────────────────────────────────────────────
# JUDGE PROFILE
# ──────────────────────────────────────────────

class JudgeProfile(Base):
    __tablename__ = "judge_profiles"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), unique=True)
    expertise = Column(String, nullable=True)

    # ── relationships ──
    user = relationship("User")

    def __repr__(self):
        return f"<JudgeProfile user_id={self.user_id}>"


# ──────────────────────────────────────────────
# MESSAGE (chat)
# ──────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    sender_id  = Column(Integer, ForeignKey("users.id"))
    content    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message id={self.id} sender={self.sender_id}>"