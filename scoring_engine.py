"""
scoring_engine.py
─────────────────
Score consolidation + anomaly detection engine.

Anomaly Detection Strategy:
  - Z-score based: flag a judge's score if it deviates more than `threshold`
    standard deviations from the panel mean for that team+criterion.
  - Panel average strategy: if only 2 judges, use absolute deviation from mean instead.
  - Configurable per-event threshold (default: 2.0 std deviations).

Consolidation Strategy:
  - Weighted average across rubric dimensions (weights from EventConfig).
  - Anomalous scores are EXCLUDED from consolidation until committee resolves them.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

RUBRIC_DIMENSIONS = ["innovation", "technical_depth", "presentation", "feasibility", "impact"]

@dataclass
class JudgeScoreInput:
    judge_id:        int
    judge_name:      str
    team_id:         int
    innovation:      float
    technical_depth: float
    presentation:    float
    feasibility:     float
    impact:          float
    notes:           Optional[str] = None

    def as_dict(self) -> dict[str, float]:
        return {
            "innovation":       self.innovation,
            "technical_depth":  self.technical_depth,
            "presentation":     self.presentation,
            "feasibility":      self.feasibility,
            "impact":           self.impact,
        }

    def raw_average(self) -> float:
        vals = list(self.as_dict().values())
        return sum(vals) / len(vals)


@dataclass
class AnomalyFlag:
    judge_id:   int
    judge_name: str
    dimension:  str            # which rubric dimension was anomalous
    score:      float          # the judge's score
    panel_mean: float          # what everyone else gave
    z_score:    float          # how many std deviations away
    severity:   str            # "HIGH" | "MEDIUM"


@dataclass
class TeamScoreResult:
    team_id:              int
    final_score:          Optional[float]          # None if held due to anomalies
    dimension_averages:   dict[str, float]          # per-dimension panel averages
    judge_totals:         dict[int, float]          # judge_id → their weighted total
    anomalies:            list[AnomalyFlag]
    is_held:              bool                      # True = block result publication
    participating_judges: int
    excluded_judges:      list[int]                 # judge IDs excluded due to anomaly


# ──────────────────────────────────────────────
# STATISTICS HELPERS
# ──────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    variance = sum((v - mu) ** 2 for v in values) / (len(values) - 1)  # sample std
    return math.sqrt(variance)


def _z_score(value: float, mu: float, sigma: float) -> float:
    if sigma == 0:
        return 0.0
    return abs(value - mu) / sigma


# ──────────────────────────────────────────────
# ANOMALY DETECTION
# ──────────────────────────────────────────────

def detect_anomalies(
    scores:    list[JudgeScoreInput],
    threshold: float = 2.0,
) -> list[AnomalyFlag]:
    """
    Checks each judge's score per dimension against the panel distribution.

    Strategy by panel size:
      - 2 judges  : flag if absolute difference > 3.0 points (hard gap rule)
      - 3 judges  : flag if a score is the outlier AND deviates > 2.5 pts from the other two's mean
      - 4+ judges : standard z-score >= threshold

    Returns a list of AnomalyFlag objects for every flagged (judge, dimension) pair.
    """
    if len(scores) < 2:
        return []

    flags: list[AnomalyFlag] = []
    n = len(scores)

    for dim in RUBRIC_DIMENSIONS:
        panel_values = [getattr(s, dim) for s in scores]
        mu    = _mean(panel_values)
        sigma = _std(panel_values)

        for s in scores:
            judge_val = getattr(s, dim)
            is_anomalous = False
            z = 0.0

            if n == 2:
                # Hard rule: absolute gap > 3 points
                gap = abs(panel_values[0] - panel_values[1])
                z = gap  # use gap as pseudo z-score for reporting
                is_anomalous = gap > 3.0

            elif n == 3:
                # Leave-one-out: compare this judge to mean of the other two
                others = [v for v in panel_values if v != judge_val]
                other_mean = _mean(others)
                deviation = abs(judge_val - other_mean)
                z = deviation
                # Flag if deviation > 2.5 pts AND this judge is clearly the outlier
                is_anomalous = deviation > 2.5

            else:
                # 4+ judges: standard z-score
                z = _z_score(judge_val, mu, sigma)
                is_anomalous = z >= threshold

            if is_anomalous:
                severity = "HIGH" if z > threshold * 1.5 else "MEDIUM"
                flags.append(AnomalyFlag(
                    judge_id   = s.judge_id,
                    judge_name = s.judge_name,
                    dimension  = dim,
                    score      = judge_val,
                    panel_mean = round(mu, 2),
                    z_score    = round(z, 3),
                    severity   = severity,
                ))

    return flags


# ──────────────────────────────────────────────
# WEIGHTED SCORE CALCULATOR
# ──────────────────────────────────────────────

def calculate_weighted_total(score: JudgeScoreInput, weights: dict[str, float]) -> float:
    """
    Computes a single judge's weighted total score.
    Weights should sum to 1.0; validated here.
    """
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.01:
        # Normalize if weights don't sum to 1
        weights = {k: v / total_weight for k, v in weights.items()}

    score_map = score.as_dict()
    return round(
        sum(score_map[dim] * weights.get(dim, 0.0) for dim in RUBRIC_DIMENSIONS),
        4,
    )


# ──────────────────────────────────────────────
# CONSOLIDATION ENGINE
# ──────────────────────────────────────────────

def consolidate_scores(
    team_id:            int,
    scores:             list[JudgeScoreInput],
    weights:            dict[str, float],
    anomaly_threshold:  float = 2.0,
) -> TeamScoreResult:
    """
    Full pipeline: detect anomalies → exclude flagged judges → consolidate.

    Args:
        team_id:            DB id of the team.
        scores:             All judge scores for this team.
        weights:            Rubric dimension weights (must sum to 1.0).
        anomaly_threshold:  Std deviation threshold for flagging.

    Returns:
        TeamScoreResult — if anomalies exist, final_score=None and is_held=True.
    """
    if not scores:
        return TeamScoreResult(
            team_id=team_id,
            final_score=None,
            dimension_averages={},
            judge_totals={},
            anomalies=[],
            is_held=True,
            participating_judges=0,
            excluded_judges=[],
        )

    # ── Step 1: Detect anomalies ──────────────
    anomalies = detect_anomalies(scores, threshold=anomaly_threshold)
    flagged_judge_ids = {f.judge_id for f in anomalies}

    # ── Step 2: Split clean vs flagged scores ─
    clean_scores  = [s for s in scores if s.judge_id not in flagged_judge_ids]
    excluded_ids  = list(flagged_judge_ids)

    # Use clean scores only for consolidation
    working_scores = clean_scores if clean_scores else scores  # fallback if all flagged

    # ── Step 3: Compute dimension averages ────
    dim_averages: dict[str, float] = {}
    for dim in RUBRIC_DIMENSIONS:
        vals = [getattr(s, dim) for s in working_scores]
        dim_averages[dim] = round(_mean(vals), 4)

    # ── Step 4: Weighted totals per judge ─────
    judge_totals: dict[int, float] = {
        s.judge_id: calculate_weighted_total(s, weights)
        for s in working_scores
    }

    # ── Step 5: Final team score = mean of clean judge totals ─
    is_held = len(anomalies) > 0
    final_score: Optional[float] = None

    if not is_held:
        all_totals = list(judge_totals.values())
        final_score = round(_mean(all_totals), 4)

    return TeamScoreResult(
        team_id              = team_id,
        final_score          = final_score,
        dimension_averages   = dim_averages,
        judge_totals         = judge_totals,
        anomalies            = anomalies,
        is_held              = is_held,
        participating_judges = len(working_scores),
        excluded_judges      = excluded_ids,
    )


# ──────────────────────────────────────────────
# LEADERBOARD BUILDER
# ──────────────────────────────────────────────

@dataclass
class LeaderboardEntry:
    rank:                 int
    team_id:              int
    team_name:            str
    final_score:          Optional[float]
    dimension_averages:   dict[str, float]
    is_held:              bool
    anomaly_count:        int


def build_leaderboard(
    team_results: list[tuple[int, str, TeamScoreResult]],  # (team_id, team_name, result)
) -> list[LeaderboardEntry]:
    """
    Ranks teams by final_score descending.
    Teams with is_held=True are listed at the bottom with rank=None shown as "HELD".
    """
    scored  = [(tid, name, r) for tid, name, r in team_results if not r.is_held and r.final_score is not None]
    held    = [(tid, name, r) for tid, name, r in team_results if r.is_held or r.final_score is None]

    scored.sort(key=lambda x: -x[2].final_score)

    board: list[LeaderboardEntry] = []

    for rank, (tid, name, result) in enumerate(scored, start=1):
        board.append(LeaderboardEntry(
            rank               = rank,
            team_id            = tid,
            team_name          = name,
            final_score        = result.final_score,
            dimension_averages = result.dimension_averages,
            is_held            = False,
            anomaly_count      = 0,
        ))

    for tid, name, result in held:
        board.append(LeaderboardEntry(
            rank               = 999,   # sentinel for "unranked / held"
            team_id            = tid,
            team_name          = name,
            final_score        = None,
            dimension_averages = result.dimension_averages,
            is_held            = True,
            anomaly_count      = len(result.anomalies),
        ))

    return board


# ──────────────────────────────────────────────
# QUICK LOCAL TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    weights = {
        "innovation":       0.25,
        "technical_depth":  0.30,
        "presentation":     0.15,
        "feasibility":      0.15,
        "impact":           0.15,
    }

    # Simulate 3 judges — Judge 3 is anomalous (gives 9.5 while others give ~4)
    test_scores = [
        JudgeScoreInput(1, "Alice Judge", 1, innovation=7.0, technical_depth=8.0, presentation=6.5, feasibility=7.0, impact=6.5),
        JudgeScoreInput(2, "Bob Judge",   1, innovation=6.5, technical_depth=7.5, presentation=7.0, feasibility=6.5, impact=7.0),
        JudgeScoreInput(3, "Eve Rogue",   1, innovation=9.5, technical_depth=9.8, presentation=9.2, feasibility=9.7, impact=9.5),  # anomalous
    ]

    result = consolidate_scores(team_id=1, scores=test_scores, weights=weights, anomaly_threshold=1.5)

    print(f"\n{'='*55}")
    print(f"Team 1 Score Result")
    print(f"  Final score  : {result.final_score} {'(HELD)' if result.is_held else ''}")
    print(f"  Is held      : {result.is_held}")
    print(f"  Anomalies    : {len(result.anomalies)}")
    for flag in result.anomalies:
        print(f"    ⚠  Judge '{flag.judge_name}' | dim='{flag.dimension}' "
              f"score={flag.score} vs panel mean={flag.panel_mean} z={flag.z_score} [{flag.severity}]")
    print(f"  Clean judge totals: {result.judge_totals}")
    print(f"  Excluded judges   : {result.excluded_judges}")

    # Leaderboard test
    print(f"\n{'='*55}")
    mock_results = [
        (1, "Team Orion",   result),
        (2, "Team Nebula",  consolidate_scores(2, [
            JudgeScoreInput(1, "Alice Judge", 2, 8.0, 8.5, 7.5, 8.0, 7.5),
            JudgeScoreInput(2, "Bob Judge",   2, 7.5, 8.0, 8.0, 7.5, 8.0),
        ], weights)),
    ]
    board = build_leaderboard(mock_results)
    print("Leaderboard:")
    for entry in board:
        status = "HELD ⚠" if entry.is_held else f"#{entry.rank}"
        print(f"  {status:8} | {entry.team_name:15} | Score: {entry.final_score}")