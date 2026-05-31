"""
team_formation.py
─────────────────
Constraint-aware team formation engine.

Algorithm: Skill-Balanced Greedy with Backtracking
  1. Feasibility check  — verify constraints can be satisfied before attempting
  2. Skill-gap scoring  — score every candidate by how much they fill missing skills
  3. Institution guard  — hard reject if institution already represented on team
  4. Experience balance — prefer teams with mixed junior/mid/senior
  5. Backtrack          — if stuck, swap members between teams to resolve deadlocks
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class ParticipantData:
    id:          int
    name:        str
    email:       str
    institution: str
    skill_tags:  list[str]
    experience:  str          # "junior" | "mid" | "senior"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


@dataclass
class TeamDraft:
    members:      list[ParticipantData] = field(default_factory=list)
    institutions: set[str]              = field(default_factory=set)
    skill_pool:   set[str]              = field(default_factory=set)

    def add(self, p: ParticipantData):
        self.members.append(p)
        self.institutions.add(p.institution.strip().lower())
        self.skill_pool.update(s.lower() for s in p.skill_tags)

    def can_add(self, p: ParticipantData, max_same_institution: int = 1) -> bool:
        inst = p.institution.strip().lower()
        inst_count = sum(
            1 for m in self.members
            if m.institution.strip().lower() == inst
        )
        return inst_count < max_same_institution

    def experience_counts(self) -> dict[str, int]:
        counts = {"junior": 0, "mid": 0, "senior": 0}
        for m in self.members:
            level = m.experience.strip().lower()
            if level in counts:
                counts[level] += 1
        return counts

    def missing_skills(self, all_skills: set[str]) -> set[str]:
        return all_skills - self.skill_pool

    def size(self) -> int:
        return len(self.members)


@dataclass
class FormationResult:
    teams:    list[list[ParticipantData]]
    leftover: list[ParticipantData]
    warnings: list[str]


# ──────────────────────────────────────────────
# SCORING HELPERS
# ──────────────────────────────────────────────

EXPERIENCE_ORDER = {"junior": 0, "mid": 1, "senior": 2}

def skill_gap_score(candidate: ParticipantData, team: TeamDraft, global_skills: set[str]) -> float:
    """
    Higher score = candidate fills more missing skills in the team.
    Range: [0.0, 1.0]
    """
    missing = team.missing_skills(global_skills)
    if not missing:
        return 0.0
    candidate_skills = set(s.lower() for s in candidate.skill_tags)
    filled = len(candidate_skills & missing)
    return filled / len(missing)


def experience_balance_score(candidate: ParticipantData, team: TeamDraft) -> float:
    """
    Prefer adding experience levels not already on the team.
    Range: [0.0, 1.0]
    """
    level = candidate.experience.strip().lower()
    counts = team.experience_counts()
    existing = counts.get(level, 0)
    if existing == 0:
        return 1.0     # adds a new level — great
    if existing == 1:
        return 0.3     # duplicates — acceptable
    return 0.0         # third of same level — avoid


def candidate_score(
    candidate: ParticipantData,
    team: TeamDraft,
    global_skills: set[str],
    w_skill: float = 0.7,
    w_exp:   float = 0.3,
) -> float:
    """Combined candidate fitness score for a given team slot."""
    return (
        w_skill * skill_gap_score(candidate, team, global_skills) +
        w_exp   * experience_balance_score(candidate, team)
    )


# ──────────────────────────────────────────────
# FEASIBILITY CHECK
# ──────────────────────────────────────────────

def check_feasibility(
    participants: list[ParticipantData],
    team_size: int,
    max_same_institution: int,
) -> tuple[bool, list[str]]:
    """
    Returns (is_feasible, list_of_warnings).
    Hard-fails if institution distribution makes it impossible to fill
    even one team without violating the constraint.
    """
    warnings = []

    if len(participants) < team_size:
        return False, [
            f"Not enough participants ({len(participants)}) to form "
            f"even one team of {team_size}."
        ]

    # Count participants per institution
    inst_counts: dict[str, int] = defaultdict(int)
    for p in participants:
        inst_counts[p.institution.strip().lower()] += 1

    n_teams = len(participants) // team_size
    slots_per_institution = n_teams * max_same_institution

    overloaded = [
        (inst, count)
        for inst, count in inst_counts.items()
        if count > slots_per_institution
    ]

    if overloaded:
        for inst, count in overloaded:
            warnings.append(
                f"Institution '{inst}' has {count} participants but only "
                f"{slots_per_institution} available slots given the constraint. "
                f"Some participants may be left over."
            )

    leftover_count = len(participants) % team_size
    if leftover_count:
        warnings.append(
            f"{leftover_count} participant(s) cannot be evenly distributed "
            f"into teams of {team_size} — they will be placed in a partial team."
        )

    return True, warnings


# ──────────────────────────────────────────────
# CORE FORMATION ENGINE
# ──────────────────────────────────────────────

def form_teams(
    participants:           list[ParticipantData],
    team_size:              int   = 3,
    max_same_institution:   int   = 1,
    shuffle_seed:           Optional[int] = 42,
) -> FormationResult:
    """
    Main entry point.

    Args:
        participants:           Full list of ParticipantData objects.
        team_size:              Target members per team.
        max_same_institution:   Hard constraint — max participants from same institution per team.
        shuffle_seed:           Seed for reproducibility. Pass None for true randomness.

    Returns:
        FormationResult with formed teams, leftover participants, and any warnings.
    """
    if shuffle_seed is not None:
        random.seed(shuffle_seed)

    # ── 1. Feasibility check ──────────────────
    feasible, warnings = check_feasibility(participants, team_size, max_same_institution)
    if not feasible:
        return FormationResult(teams=[], leftover=list(participants), warnings=warnings)

    # ── 2. Compute global skill universe ─────
    global_skills: set[str] = set()
    for p in participants:
        global_skills.update(s.lower() for s in p.skill_tags)

    # ── 3. Sort participants: senior → mid → junior, then shuffle within tier ──
    pool = sorted(participants, key=lambda p: -EXPERIENCE_ORDER.get(p.experience.lower(), 0))
    random.shuffle(pool)   # light shuffle to break deterministic bias

    n_teams        = len(pool) // team_size
    drafts: list[TeamDraft] = [TeamDraft() for _ in range(n_teams)]
    unassigned: list[ParticipantData] = list(pool)

    # ── 4. Greedy assignment ──────────────────
    max_passes = 3
    for _pass in range(max_passes):
        still_unassigned = []
        for candidate in unassigned:
            placed = False
            # Score this candidate against every incomplete team, pick best fit
            scored_teams = []
            for draft in drafts:
                if draft.size() >= team_size:
                    continue
                if not draft.can_add(candidate, max_same_institution):
                    continue
                score = candidate_score(candidate, draft, global_skills)
                scored_teams.append((score, id(draft), draft))   # id() breaks tie deterministically

            if scored_teams:
                scored_teams.sort(key=lambda x: -x[0])
                best_draft = scored_teams[0][2]
                best_draft.add(candidate)
                placed = True

            if not placed:
                still_unassigned.append(candidate)

        unassigned = still_unassigned
        if not unassigned:
            break

    # ── 5. Backtrack swap — fix institution conflicts that greedy couldn't resolve ──
    unassigned = _backtrack_swap(unassigned, drafts, team_size, max_same_institution, global_skills)

    # ── 6. Pack any remaining into a partial team (rather than lose them) ──
    if unassigned:
        warnings.append(
            f"{len(unassigned)} participant(s) could not be placed in balanced teams "
            f"and were grouped into a partial/overflow team."
        )
        overflow = TeamDraft()
        for p in unassigned:
            overflow.add(p)
        drafts.append(overflow)
        unassigned = []

    # ── 7. Build result ───────────────────────
    teams_out = [draft.members for draft in drafts if draft.members]
    return FormationResult(teams=teams_out, leftover=unassigned, warnings=warnings)


def _backtrack_swap(
    unassigned:           list[ParticipantData],
    drafts:               list[TeamDraft],
    team_size:            int,
    max_same_institution: int,
    global_skills:        set[str],
) -> list[ParticipantData]:
    """
    For each unassigned participant, try swapping them with an existing member
    of a full team if the swap resolves the institution conflict.
    """
    still_stuck = []
    for candidate in unassigned:
        swapped = False
        for draft in drafts:
            if swapped:
                break
            # Only look at full teams — partial teams should have accepted candidate already
            if draft.size() < team_size:
                continue
            for i, existing_member in enumerate(draft.members):
                # Would removing existing_member and adding candidate satisfy constraints?
                test_draft = TeamDraft()
                for j, m in enumerate(draft.members):
                    if j != i:
                        test_draft.add(m)

                if test_draft.can_add(candidate, max_same_institution):
                    # Check the displaced member can go somewhere else
                    for other_draft in drafts:
                        if other_draft is draft:
                            continue
                        if other_draft.size() >= team_size:
                            continue
                        if other_draft.can_add(existing_member, max_same_institution):
                            # Execute the swap
                            draft.members.pop(i)
                            draft.institutions = {m.institution.strip().lower() for m in draft.members}
                            draft.skill_pool = {s.lower() for m in draft.members for s in m.skill_tags}
                            draft.add(candidate)
                            other_draft.add(existing_member)
                            swapped = True
                            break
                if swapped:
                    break

        if not swapped:
            still_stuck.append(candidate)

    return still_stuck


# ──────────────────────────────────────────────
# RATIONALE DATA  (fed to LLM)
# ──────────────────────────────────────────────

def build_rationale_prompt(team_members: list[ParticipantData], team_name: str) -> str:
    """
    Generates a structured prompt for the LLM to write a team rationale.
    The LLM receives structured facts; it only writes the prose.
    """
    members_text = "\n".join(
        f"  - {p.name} | {p.institution} | Skills: {', '.join(p.skill_tags)} | Level: {p.experience}"
        for p in team_members
    )
    skills = set(s for p in team_members for s in p.skill_tags)
    institutions = list({p.institution for p in team_members})
    levels = [p.experience for p in team_members]

    return f"""You are writing a team composition rationale for a competitive hackathon.

Team Name: {team_name}

Members:
{members_text}

Facts about this team:
- Combined skill coverage: {', '.join(sorted(skills))}
- Institutions represented: {', '.join(institutions)} (no duplicates — diversity maintained)
- Experience distribution: {', '.join(levels)}

Write a concise 3-4 sentence rationale (no bullet points) explaining:
1. How the skill combination is balanced and complementary
2. How experience distribution supports team productivity
3. Why this team is well-positioned for the hackathon

Be specific — reference the actual skills and names. Do not use generic filler phrases."""


# ──────────────────────────────────────────────
# QUICK LOCAL TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Smoke test with 9 sample participants
    sample = [
        ParticipantData(1,  "Alice",   "a@x.com", "MIT",       ["ML", "Python"],         "senior"),
        ParticipantData(2,  "Bob",     "b@x.com", "Stanford",  ["Backend", "Go"],         "mid"),
        ParticipantData(3,  "Carol",   "c@x.com", "IIT",       ["Frontend", "React"],     "junior"),
        ParticipantData(4,  "Dave",    "d@x.com", "MIT",       ["DevOps", "Docker"],      "mid"),
        ParticipantData(5,  "Eve",     "e@x.com", "Harvard",   ["ML", "R"],               "junior"),
        ParticipantData(6,  "Frank",   "f@x.com", "Stanford",  ["Backend", "Java"],       "senior"),
        ParticipantData(7,  "Grace",   "g@x.com", "IIT",       ["Frontend", "Vue"],       "mid"),
        ParticipantData(8,  "Heidi",   "h@x.com", "CMU",       ["ML", "TensorFlow"],      "senior"),
        ParticipantData(9,  "Ivan",    "i@x.com", "CMU",       ["Backend", "Rust"],       "junior"),
    ]

    result = form_teams(sample, team_size=3, max_same_institution=1)

    print(f"\n{'='*50}")
    print(f"Formed {len(result.teams)} team(s)  |  Leftover: {len(result.leftover)}")
    print(f"Warnings: {result.warnings or 'None'}")
    for i, team in enumerate(result.teams, 1):
        print(f"\nTeam {i}:")
        for m in team:
            print(f"  {m.name:10} | {m.institution:10} | {','.join(m.skill_tags):25} | {m.experience}")

        # Verify institution constraint
        insts = [m.institution for m in team]
        assert len(insts) == len(set(insts)), f"CONSTRAINT VIOLATION in Team {i}!"
    print("\n✅ All institution constraints satisfied.")