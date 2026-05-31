"""
repositories.py
───────────────
Repository Pattern — a thin data-access layer that sits between the
route handlers and SQLAlchemy.

Why Repository Pattern here?
  - Route handlers stay clean: zero raw ORM queries, zero `.commit()` calls
    scattered across the file — all DB logic is co-located per resource.
  - Testability: swap the real repository for an in-memory mock in unit tests
    without touching the route layer.
  - Single Responsibility: each repository owns exactly one model's CRUD +
    domain-specific queries, making the codebase easy to navigate.
  - Consistent error surface: DB exceptions bubble up from one place, not
    from anywhere a `.query()` call could live.

Each repository receives the `db: Session` as a constructor argument so
FastAPI's `Depends(get_db)` works without friction.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Participant, Team, Judge, Score, Approval, Communication,
    EventConfig, ApprovalStatus, ApprovalType,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# BASE REPOSITORY
# ══════════════════════════════════════════════════════════════

class BaseRepository:
    def __init__(self, db: Session):
        self.db = db


# ══════════════════════════════════════════════════════════════
# PARTICIPANT REPOSITORY
# ══════════════════════════════════════════════════════════════

class ParticipantRepository(BaseRepository):

    def create(self, name: str, email: str, institution: str,
               skill_tags: str, experience: str) -> Participant:
        p = Participant(
            name=name,
            email=email,
            institution=institution,
            skill_tags=skill_tags,
            experience=experience,
        )
        self.db.add(p)
        self.db.flush()   # get the ID without committing
        return p

    def get_by_email(self, email: str) -> Optional[Participant]:
        return self.db.query(Participant).filter(Participant.email == email).first()

    def get_all(self) -> list[Participant]:
        return self.db.query(Participant).all()

    def get_unassigned(self) -> list[Participant]:
        """Returns participants not yet assigned to a team."""
        return (
            self.db.query(Participant)
            .filter(Participant.team_id.is_(None))
            .all()
        )

    def bulk_upsert(
        self, participants_data: list[dict]
    ) -> tuple[int, int]:
        """
        Insert new participants; skip duplicates by email.
        Returns (created_count, skipped_count).
        """
        created, skipped = 0, 0
        for data in participants_data:
            if self.get_by_email(data["email"]):
                skipped += 1
                continue
            self.create(**data)
            created += 1
        self.db.commit()
        return created, skipped


# ══════════════════════════════════════════════════════════════
# TEAM REPOSITORY
# ══════════════════════════════════════════════════════════════

class TeamRepository(BaseRepository):

    def create(self, name: str) -> Team:
        team = Team(name=name)
        self.db.add(team)
        self.db.flush()
        return team

    def get_by_id(self, team_id: int) -> Optional[Team]:
        return self.db.query(Team).filter(Team.id == team_id).first()

    def get_all(self) -> list[Team]:
        return self.db.query(Team).all()

    def set_approved(self, team: Team, approved: bool = True) -> Team:
        team.is_approved = approved
        self.db.flush()
        return team

    def set_qualified(self, team: Team, qualified: bool = True) -> Team:
        team.is_qualified = qualified
        self.db.flush()
        return team

    def update_rationale(self, team: Team, rationale: str) -> Team:
        team.rationale = rationale
        self.db.flush()
        return team

    def assign_members(self, team: Team, participants: list[Participant]) -> Team:
        for p in participants:
            p.team_id = team.id
        self.db.flush()
        return team

    def set_final_score(self, team: Team, score: float, rank: int) -> Team:
        team.final_score = score
        team.rank = rank
        self.db.flush()
        return team


# ══════════════════════════════════════════════════════════════
# JUDGE REPOSITORY
# ══════════════════════════════════════════════════════════════

class JudgeRepository(BaseRepository):

    def create(self, name: str, email: str,
               expertise: Optional[str] = None) -> Judge:
        judge = Judge(name=name, email=email, expertise=expertise)
        self.db.add(judge)
        self.db.flush()
        return judge

    def get_by_id(self, judge_id: int) -> Optional[Judge]:
        return self.db.query(Judge).filter(Judge.id == judge_id).first()

    def get_by_email(self, email: str) -> Optional[Judge]:
        return self.db.query(Judge).filter(Judge.email == email).first()

    def get_all(self) -> list[Judge]:
        return self.db.query(Judge).all()


# ══════════════════════════════════════════════════════════════
# SCORE REPOSITORY
# ══════════════════════════════════════════════════════════════

class ScoreRepository(BaseRepository):

    def create(
        self,
        team_id: int,
        judge_id: int,
        innovation: float,
        technical_depth: float,
        presentation: float,
        feasibility: float,
        impact: float,
        weighted_total: float,
        notes: Optional[str] = None,
    ) -> Score:
        score = Score(
            team_id=team_id,
            judge_id=judge_id,
            innovation=innovation,
            technical_depth=technical_depth,
            presentation=presentation,
            feasibility=feasibility,
            impact=impact,
            weighted_total=weighted_total,
            notes=notes,
        )
        self.db.add(score)
        self.db.flush()
        return score

    def get_for_team(self, team_id: int) -> list[Score]:
        return self.db.query(Score).filter(Score.team_id == team_id).all()

    def get_all(self) -> list[Score]:
        return self.db.query(Score).all()

    def mark_anomalous(self, score: Score, is_anomalous: bool = True) -> Score:
        score.is_anomalous = is_anomalous
        self.db.flush()
        return score

    def get_scores_grouped_by_team(self) -> dict[int, list[Score]]:
        """Returns {team_id: [Score, ...]} for all scores."""
        all_scores = self.get_all()
        grouped: dict[int, list[Score]] = {}
        for s in all_scores:
            grouped.setdefault(s.team_id, []).append(s)
        return grouped


# ══════════════════════════════════════════════════════════════
# APPROVAL REPOSITORY
# ══════════════════════════════════════════════════════════════

class ApprovalRepository(BaseRepository):

    def create(
        self,
        approval_type: ApprovalType,
        team_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        payload: Optional[str] = None,
    ) -> Approval:
        approval = Approval(
            approval_type=approval_type,
            team_id=team_id,
            reference_id=reference_id,
            payload=payload,
            status=ApprovalStatus.PENDING,
        )
        self.db.add(approval)
        self.db.flush()
        return approval

    def get_by_id(self, approval_id: int) -> Optional[Approval]:
        return self.db.query(Approval).filter(Approval.id == approval_id).first()

    def get_pending(self) -> list[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.requested_at)
            .all()
        )

    def get_by_type_and_team(
        self, approval_type: ApprovalType, team_id: int
    ) -> Optional[Approval]:
        return (
            self.db.query(Approval)
            .filter(
                Approval.approval_type == approval_type,
                Approval.team_id == team_id,
                Approval.status == ApprovalStatus.PENDING,
            )
            .first()
        )

    def transition(
        self,
        approval: Approval,
        new_status: ApprovalStatus,
        resolved_by: str,
        reject_reason: Optional[str] = None,
    ) -> Approval:
        """
        Performs a guarded state transition using the model's own
        `can_transition_to` logic — prevents illegal state jumps.
        """
        if not approval.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition approval #{approval.id} "
                f"from {approval.status} → {new_status}."
            )
        approval.status = new_status
        approval.resolved_at = datetime.utcnow()
        approval.resolved_by = resolved_by
        if reject_reason:
            approval.reject_reason = reject_reason
        self.db.flush()
        return approval


# ══════════════════════════════════════════════════════════════
# EVENT CONFIG REPOSITORY
# ══════════════════════════════════════════════════════════════

class EventConfigRepository(BaseRepository):

    def get(self) -> EventConfig:
        """Returns the singleton EventConfig row (id=1). Always exists after init."""
        config = self.db.query(EventConfig).filter(EventConfig.id == 1).first()
        if config is None:
            # Defensive: seed it if missing (should never happen post-init)
            config = EventConfig(id=1)
            self.db.add(config)
            self.db.commit()
            logger.warning("EventConfig was missing — re-seeded with defaults.")
        return config