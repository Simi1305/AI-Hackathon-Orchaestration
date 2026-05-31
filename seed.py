"""
seed.py
───────
Comprehensive seed script for the EventFlow Hackathon Orchestration Platform.
Creates realistic demo data across all tables.
"""

import os
import sys
from datetime import datetime, timedelta

# Remove old database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eventflow.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Removed old database: {db_path}")

from database import SessionLocal, init_db, engine, Base
from models import (
    User, UserRole, Participant, Team, Judge, Score, Approval,
    MentorProfile, JudgeProfile, MentorAssignment, EventConfig,
    ApprovalType, ApprovalStatus, Communication, CommunicationStatus,
    EventStage,
)
import bcrypt

DEFAULT_PASSWORD = "password123"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


    db = SessionLocal()

    try:
        # ══════════════════════════════════════════════
        # 1. ADMIN USER (Organizer)
        # ══════════════════════════════════════════════
        hashed_pw = hash_password(DEFAULT_PASSWORD)

        admin = User(
            username="admin",
            password_hash=hashed_pw,
            role=UserRole.ORGANIZER,
            is_active=True,
        )
        db.add(admin)
        db.flush()
        print(f"Created admin user: admin (id={admin.id})")

        # ══════════════════════════════════════════════
        # 2. PARTICIPANT USERS + PARTICIPANT RECORDS
        # ══════════════════════════════════════════════
        institutions = [
            "MIT", "Stanford University", "IIT Delhi",
            "UC Berkeley", "Carnegie Mellon",
        ]

        participant_data = [
            # (name, email_prefix, institution_idx, skills, experience)
            ("Aarav Sharma", "aarav", 0, "ML,Python,TensorFlow", "senior"),
            ("Priya Patel", "priya", 1, "Backend,Java,Spring", "mid"),
            ("Liam Chen", "liam", 2, "Frontend,React,TypeScript", "mid"),
            ("Sofia Garcia", "sofia", 3, "DevOps,Docker,Kubernetes", "senior"),
            ("Ethan Williams", "ethan", 4, "Design,Figma,CSS", "junior"),
            ("Ananya Reddy", "ananya", 0, "ML,PyTorch,Computer Vision", "senior"),
            ("Noah Johnson", "noah", 1, "Backend,Python,FastAPI", "mid"),
            ("Isabella Kim", "isabella", 2, "Frontend,Vue,JavaScript", "mid"),
            ("Mason Brown", "mason", 3, "Data,SQL,Pandas", "junior"),
            ("Zara Ahmed", "zara", 4, "Security,Networking,Linux", "senior"),
            ("Rohan Gupta", "rohan", 0, "Mobile,Flutter,Dart", "mid"),
            ("Emma Davis", "emma", 1, "ML,NLP,Python", "senior"),
            ("Oliver Wilson", "oliver", 2, "Backend,Go,PostgreSQL", "mid"),
            ("Mia Tanaka", "mia", 3, "Frontend,React,Tailwind", "junior"),
            ("Arjun Nair", "arjun", 4, "DevOps,AWS,Terraform", "senior"),
            ("Chloe Martinez", "chloe", 0, "Design,UI/UX,Adobe", "mid"),
            ("Lucas Anderson", "lucas", 1, "Data,Python,Spark", "mid"),
            ("Aisha Khan", "aisha", 2, "Security,Cryptography,Python", "senior"),
            ("James Taylor", "james", 3, "Mobile,React Native,JavaScript", "junior"),
            ("Neha Verma", "neha", 4, "ML,Deep Learning,Python", "senior"),
            ("Alexander Lee", "alexander", 0, "Backend,Node.js,MongoDB", "mid"),
            ("Sara Thompson", "sara", 1, "Frontend,Angular,SCSS", "mid"),
            ("Ryan Clark", "ryan", 2, "DevOps,CI/CD,Jenkins", "junior"),
            ("Divya Iyer", "divya", 3, "Data,R,Tableau", "mid"),
            ("Daniel White", "daniel", 4, "ML,Reinforcement Learning,Python", "senior"),
        ]

        participant_users = []
        participant_records = []

        for name, email_prefix, inst_idx, skills, experience in participant_data:
            # Create User account
            user = User(
                username=email_prefix,
                password_hash=hashed_pw,
                role=UserRole.PARTICIPANT,
                is_active=True,
            )
            db.add(user)
            db.flush()
            participant_users.append(user)

            # Create Participant record
            participant = Participant(
                name=name,
                email=f"{email_prefix}@{institutions[inst_idx].lower().replace(' ', '')}.edu",
                institution=institutions[inst_idx],
                skill_tags=skills,
                experience=experience,
            )
            db.add(participant)
            db.flush()
            participant_records.append(participant)

        print(f"Created {len(participant_records)} participants with user accounts")

        # ══════════════════════════════════════════════
        # 3. TEAMS (8 teams, 3-4 members each)
        # ══════════════════════════════════════════════
        team_configs = [
            ("Neural Nexus", "AI-Powered Healthcare Diagnostics", True),
            ("Quantum Forge", "Decentralized Supply Chain", True),
            ("Cyber Sentinels", "Real-Time Threat Detection", True),
            ("Data Alchemists", "Predictive Climate Modeling", True),
            ("Code Crusaders", "Smart City Traffic Optimization", True),
            ("Pixel Pioneers", "AR-Enhanced Education Platform", True),
            ("Cloud Catalysts", "Serverless ML Pipeline", True),
            ("Algo Architects", "Autonomous Drone Navigation", True),
        ]

        teams = []
        # Assign 3 members to each team (25 participants / 8 teams ~ 3 each, 1 leftover)
        member_assignments = [
            [0, 1, 2],        # Neural Nexus: Aarav, Priya, Liam
            [3, 4, 5],        # Quantum Forge: Sofia, Ethan, Ananya
            [6, 7, 8],        # Cyber Sentinels: Noah, Isabella, Mason
            [9, 10, 11],      # Data Alchemists: Zara, Rohan, Emma
            [12, 13, 14],     # Code Crusaders: Oliver, Mia, Arjun
            [15, 16, 17],     # Pixel Pioneers: Chloe, Lucas, Aisha
            [18, 19, 20],     # Cloud Catalysts: James, Neha, Alexander
            [21, 22, 23, 24], # Algo Architects: Sara, Ryan, Divya, Daniel
        ]

        for idx, (team_name, challenge, approved) in enumerate(team_configs):
            team = Team(
                name=team_name,
                challenge=challenge,
                rationale=f"Team {team_name} was formed with complementary skills spanning multiple domains. "
                          f"The diversity of backgrounds ensures robust problem-solving for: {challenge}.",
                compatibility_score=round(0.75 + (idx * 0.02), 2),
                is_approved=approved,
                is_qualified=idx < 5,  # Top 5 teams qualified
                created_at=datetime.utcnow() - timedelta(days=14 - idx),
            )
            db.add(team)
            db.flush()
            teams.append(team)

            # Assign members
            for member_idx in member_assignments[idx]:
                participant_records[member_idx].team_id = team.id

        db.flush()
        print(f"Created {len(teams)} teams with member assignments")

        # ══════════════════════════════════════════════
        # 4. MENTOR USERS + PROFILES + ASSIGNMENTS
        # ══════════════════════════════════════════════
        mentor_data = [
            ("mentor_sarah", "Sarah Richardson", "AI/ML, Computer Vision, NLP"),
            ("mentor_david", "David Nakamura", "Cloud Architecture, DevOps, Microservices"),
            ("mentor_elena", "Elena Volkov", "Cybersecurity, Blockchain, Distributed Systems"),
        ]

        mentor_profiles = []
        for username, name, expertise in mentor_data:
            mentor_user = User(
                username=username,
                password_hash=hashed_pw,
                role=UserRole.MENTOR,
                is_active=True,
            )
            db.add(mentor_user)
            db.flush()

            profile = MentorProfile(
                user_id=mentor_user.id,
                expertise=expertise,
                capacity=3,
            )
            db.add(profile)
            db.flush()
            mentor_profiles.append(profile)

        # Assign mentors to teams (each mentor gets 2-3 teams)
        mentor_team_assignments = [
            (0, [0, 1, 3]),     # Sarah -> Neural Nexus, Quantum Forge, Data Alchemists
            (1, [2, 4, 6]),     # David -> Cyber Sentinels, Code Crusaders, Cloud Catalysts
            (2, [5, 7]),        # Elena -> Pixel Pioneers, Algo Architects
        ]

        for mentor_idx, team_indices in mentor_team_assignments:
            for team_idx in team_indices:
                assignment = MentorAssignment(
                    mentor_id=mentor_profiles[mentor_idx].id,
                    team_id=teams[team_idx].id,
                )
                db.add(assignment)

        db.flush()
        print(f"Created {len(mentor_data)} mentors with team assignments")

        # ══════════════════════════════════════════════
        # 5. JUDGE USERS + PROFILES + JUDGE RECORDS
        # ══════════════════════════════════════════════
        judge_data = [
            ("judge_michael", "Dr. Michael Torres", "michael.torres@ieee.org", "ML Systems, Scalability"),
            ("judge_priyanka", "Prof. Priyanka Desai", "priyanka.desai@acm.org", "HCI, Design Thinking"),
            ("judge_robert", "Robert Chang", "robert.chang@techventures.com", "Product Strategy, Architecture"),
        ]

        judge_profiles_list = []
        judge_records = []

        for username, name, email, expertise in judge_data:
            # User account
            judge_user = User(
                username=username,
                password_hash=hashed_pw,
                role=UserRole.JUDGE,
                is_active=True,
            )
            db.add(judge_user)
            db.flush()

            # JudgeProfile
            j_profile = JudgeProfile(
                user_id=judge_user.id,
                expertise=expertise,
            )
            db.add(j_profile)
            db.flush()
            judge_profiles_list.append(j_profile)

            # Judge record (for scoring engine compatibility)
            judge_record = Judge(
                name=name,
                email=email,
                expertise=expertise,
            )
            db.add(judge_record)
            db.flush()
            judge_records.append(judge_record)

        print(f"Created {len(judge_data)} judges (users + profiles + judge records)")

        # ══════════════════════════════════════════════
        # 6. SCORE RECORDS (each judge scores 4 teams)
        # ══════════════════════════════════════════════
        # Realistic rubric scores varying by judge and team
        score_matrix = [
            # Judge 0 (Dr. Torres) scores teams 0-3
            (0, 0, 8.5, 9.0, 7.5, 8.0, 9.0),
            (0, 1, 7.0, 8.5, 8.0, 7.5, 7.0),
            (0, 2, 9.0, 7.5, 6.5, 8.5, 8.0),
            (0, 3, 6.5, 7.0, 8.5, 7.0, 7.5),
            # Judge 1 (Prof. Desai) scores teams 0-3
            (1, 0, 8.0, 8.5, 8.5, 7.5, 8.5),
            (1, 1, 7.5, 8.0, 7.0, 8.0, 7.5),
            (1, 2, 8.5, 7.0, 7.5, 8.0, 7.5),
            (1, 3, 7.0, 7.5, 9.0, 7.5, 8.0),
            # Judge 2 (Robert Chang) scores teams 4-7
            (2, 4, 8.0, 8.5, 7.0, 8.5, 9.0),
            (2, 5, 7.5, 7.0, 8.0, 7.0, 7.5),
            (2, 6, 9.0, 8.0, 7.5, 8.0, 8.5),
            (2, 7, 7.0, 7.5, 8.5, 7.5, 8.0),
        ]

        # Default weights for weighted_total calculation
        weights = {
            "innovation": 0.25,
            "technical_depth": 0.30,
            "presentation": 0.15,
            "feasibility": 0.15,
            "impact": 0.15,
        }

        scores_created = 0
        for judge_idx, team_idx, inno, tech, pres, feas, imp in score_matrix:
            weighted = (
                inno * weights["innovation"]
                + tech * weights["technical_depth"]
                + pres * weights["presentation"]
                + feas * weights["feasibility"]
                + imp * weights["impact"]
            )
            score = Score(
                team_id=teams[team_idx].id,
                judge_id=judge_records[judge_idx].id,
                innovation=inno,
                technical_depth=tech,
                presentation=pres,
                feasibility=feas,
                impact=imp,
                weighted_total=round(weighted, 2),
                is_anomalous=False,
                submitted_at=datetime.utcnow() - timedelta(days=7 - team_idx),
                notes=f"Solid work on {teams[team_idx].challenge}. {'Impressive innovation.' if inno > 8.0 else 'Room for improvement in novelty.'}",
            )
            db.add(score)
            scores_created += 1

        db.flush()

        # Update team final scores (average of weighted totals per team)
        for team in teams:
            team_scores = [s for s in db.query(Score).filter(Score.team_id == team.id).all()]
            if team_scores:
                avg_score = sum(s.weighted_total for s in team_scores) / len(team_scores)
                team.final_score = round(avg_score, 2)

        # Assign ranks based on final_score
        scored_teams = sorted(
            [t for t in teams if t.final_score is not None],
            key=lambda t: t.final_score,
            reverse=True,
        )
        for rank_idx, team in enumerate(scored_teams, 1):
            team.rank = rank_idx

        db.flush()
        print(f"Created {scores_created} score records with team rankings")

        # ══════════════════════════════════════════════
        # 7. APPROVAL RECORDS
        # ══════════════════════════════════════════════
        approval_configs = [
            (ApprovalType.TEAM_REVIEW, teams[0].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.TEAM_REVIEW, teams[1].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.MENTOR_ASSIGNMENT_REVIEW, teams[2].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.ANOMALY_REVIEW, teams[3].id, ApprovalStatus.PENDING, None),
            (ApprovalType.RESULT_PUBLICATION_REVIEW, teams[4].id, ApprovalStatus.PENDING, None),
        ]

        for atype, team_id, a_status, resolved_by in approval_configs:
            approval = Approval(
                approval_type=atype,
                status=a_status,
                team_id=team_id,
                requested_at=datetime.utcnow() - timedelta(days=5),
                resolved_at=datetime.utcnow() - timedelta(days=3) if a_status != ApprovalStatus.PENDING else None,
                resolved_by=resolved_by,
            )
            db.add(approval)

        db.flush()
        print(f"Created {len(approval_configs)} approval records")

        # ══════════════════════════════════════════════
        # 8. EVENT CONFIG SINGLETON
        # ══════════════════════════════════════════════
        config = EventConfig(
            id=1,
            event_name="EventFlow Hackathon 2026",
            current_stage=EventStage.EVALUATION,
            team_size=3,
            max_same_institution=2,
            required_skills="Python,ML",
            weight_innovation=0.25,
            weight_technical_depth=0.30,
            weight_presentation=0.15,
            weight_feasibility=0.15,
            weight_impact=0.15,
            anomaly_threshold=2.0,
            updated_at=datetime.utcnow(),
        )
        db.add(config)
        db.flush()
        print("Created EventConfig singleton")

        # ══════════════════════════════════════════════
        # COMMIT ALL
        # ══════════════════════════════════════════════
        db.commit()
        print("\n" + "=" * 50)
        print("DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 50)
        print(f"  Users:          {db.query(User).count()}")
        print(f"  Participants:   {db.query(Participant).count()}")
        print(f"  Teams:          {db.query(Team).count()}")
        print(f"  Mentor Profiles:{db.query(MentorProfile).count()}")
        print(f"  Judge Profiles: {db.query(JudgeProfile).count()}")
        print(f"  Judges:         {db.query(Judge).count()}")
        print(f"  Scores:         {db.query(Score).count()}")
        print(f"  Approvals:      {db.query(Approval).count()}")
        print(f"  Mentor Assigns: {db.query(MentorAssignment).count()}")
        print("=" * 50)
        print("\nDefault credentials (all accounts):")
        print(f"  Password: {DEFAULT_PASSWORD}")
        print(f"  Admin:    admin / {DEFAULT_PASSWORD}")
        print(f"  Mentor:   mentor_sarah / {DEFAULT_PASSWORD}")
        print(f"  Judge:    judge_michael / {DEFAULT_PASSWORD}")
        print(f"  Student:  aarav / {DEFAULT_PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"ERROR during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
