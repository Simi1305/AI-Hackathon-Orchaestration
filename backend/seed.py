"""
seed.py
───────
Comprehensive seed script for the EventFlow Hackathon Orchestration Platform.
Creates realistic demo data: 1 organizer, 20 participants, 5 mentors, 3 judges.
"""

import os
import sys
from datetime import datetime, timedelta

# Remove old database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eventflow.db")
for ext in ["", "-shm", "-wal"]:
    p = db_path + ext
    if os.path.exists(p):
        os.remove(p)
        print(f"Removed: {p}")

from database import SessionLocal, init_db, engine, Base
from models import (
    User, UserRole, Participant, Team, Judge, Score, Approval,
    MentorProfile, JudgeProfile, MentorAssignment, EventConfig,
    ApprovalType, ApprovalStatus, EventStage,
)
import bcrypt

DEFAULT_PASSWORD = "password123"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()

    try:
        hashed_pw = hash_password(DEFAULT_PASSWORD)

        # ══════════════════════════════════════════════
        # 1. ADMIN USER (Organizer)
        # ══════════════════════════════════════════════
        admin = User(
            username="admin",
            password_hash=hashed_pw,
            role=UserRole.ORGANIZER,
            is_active=True,
            event_id="default",
        )
        db.add(admin)
        db.flush()
        print(f"Created admin user: admin (id={admin.id})")

        # ══════════════════════════════════════════════
        # 2. PARTICIPANT USERS + PARTICIPANT RECORDS (20)
        # ══════════════════════════════════════════════
        institutions = [
            "MIT", "Stanford University", "IIT Delhi",
            "UC Berkeley", "Carnegie Mellon",
        ]

        participant_data = [
            # (name, username, institution_idx, skills, experience)
            ("Aarav Sharma",     "aarav",     0, "ML,Python,TensorFlow",            "senior"),
            ("Priya Patel",     "priya",     1, "Backend,Java,Spring",             "mid"),
            ("Liam Chen",       "liam",      2, "Frontend,React,TypeScript",       "mid"),
            ("Sofia Garcia",    "sofia",     3, "DevOps,Docker,Kubernetes",         "senior"),
            ("Ethan Williams",  "ethan",     4, "Design,Figma,CSS",                "junior"),
            ("Ananya Reddy",    "ananya",    0, "ML,PyTorch,Computer Vision",      "senior"),
            ("Noah Johnson",    "noah",      1, "Backend,Python,FastAPI",           "mid"),
            ("Isabella Kim",    "isabella",  2, "Frontend,Vue,JavaScript",         "mid"),
            ("Mason Brown",     "mason",     3, "Data,SQL,Pandas",                 "junior"),
            ("Zara Ahmed",      "zara",      4, "Security,Networking,Linux",       "senior"),
            ("Rohan Gupta",     "rohan",     0, "Mobile,Flutter,Dart",             "mid"),
            ("Emma Davis",      "emma",      1, "ML,NLP,Python",                   "senior"),
            ("Oliver Wilson",   "oliver",    2, "Backend,Go,PostgreSQL",           "mid"),
            ("Mia Tanaka",      "mia",       3, "Frontend,React,Tailwind",         "junior"),
            ("Arjun Nair",      "arjun",     4, "DevOps,AWS,Terraform",            "senior"),
            ("Chloe Martinez",  "chloe",     0, "Design,UI/UX,Adobe",              "mid"),
            ("Lucas Anderson",  "lucas",     1, "Data,Python,Spark",               "mid"),
            ("Aisha Khan",      "aisha",     2, "Security,Cryptography,Python",    "senior"),
            ("James Taylor",    "james",     3, "Mobile,React Native,JavaScript",  "junior"),
            ("Neha Verma",      "neha",      4, "ML,Deep Learning,Python",         "senior"),
        ]

        participant_users = []
        participant_records = []

        for name, username, inst_idx, skills, experience in participant_data:
            user = User(
                username=username,
                password_hash=hashed_pw,
                role=UserRole.PARTICIPANT,
                is_active=True,
                event_id="default",
            )
            db.add(user)
            db.flush()
            participant_users.append(user)

            participant = Participant(
                name=name,
                email=f"{username}@{institutions[inst_idx].lower().replace(' ', '')}.edu",
                institution=institutions[inst_idx],
                skill_tags=skills,
                experience=experience,
            )
            db.add(participant)
            db.flush()
            participant_records.append(participant)

        print(f"Created {len(participant_records)} participants with user accounts")

        # ══════════════════════════════════════════════
        # 3. TEAMS (6 full teams of 3 + 1 partial of 2 = 20 participants)
        # ══════════════════════════════════════════════
        team_configs = [
            ("Neural Nexus",     "AI-Powered Healthcare Diagnostics",    True),
            ("Quantum Forge",    "Decentralized Supply Chain",           True),
            ("Cyber Sentinels",  "Real-Time Threat Detection",           True),
            ("Data Alchemists",  "Predictive Climate Modeling",          True),
            ("Code Crusaders",   "Smart City Traffic Optimization",      True),
            ("Pixel Pioneers",   "AR-Enhanced Education Platform",       True),
            ("Cloud Catalysts",  "Serverless ML Pipeline",               True),
        ]

        # 6 teams of 3 + 1 team of 2
        member_assignments = [
            [0, 1, 2],          # Neural Nexus: Aarav, Priya, Liam
            [3, 4, 5],          # Quantum Forge: Sofia, Ethan, Ananya
            [6, 7, 8],          # Cyber Sentinels: Noah, Isabella, Mason
            [9, 10, 11],        # Data Alchemists: Zara, Rohan, Emma
            [12, 13, 14],       # Code Crusaders: Oliver, Mia, Arjun
            [15, 16, 17],       # Pixel Pioneers: Chloe, Lucas, Aisha
            [18, 19],           # Cloud Catalysts: James, Neha (partial)
        ]

        teams = []
        for idx, (team_name, challenge, approved) in enumerate(team_configs):
            team = Team(
                name=team_name,
                challenge=challenge,
                rationale=f"Team {team_name} was formed with complementary skills spanning multiple domains. "
                          f"The diversity of backgrounds ensures robust problem-solving for: {challenge}.",
                compatibility_score=round(0.75 + (idx * 0.02), 2),
                is_approved=approved,
                is_qualified=idx < 4,
                created_at=datetime.utcnow() - timedelta(days=14 - idx),
            )
            db.add(team)
            db.flush()
            teams.append(team)

            for member_idx in member_assignments[idx]:
                participant_records[member_idx].team_id = team.id

        db.flush()
        print(f"Created {len(teams)} teams with member assignments")

        # ══════════════════════════════════════════════
        # 3.5 PROJECT SUBMISSIONS
        # ══════════════════════════════════════════════
        from models import ProjectSubmission, AIEvaluationBrief
        project_details = [
            # 0. Neural Nexus (AI Healthcare Diagnostics)
            {"name": "NeuroScan AI", "problem": "Delayed detection of neurological anomalies from MRI scans.", "solution": "An automated AI diagnostic tool utilizing 3D CNNs to identify early-stage anomalies.", "tech": "Python, PyTorch, React, PostgreSQL", "arch": "Microservices backend with a scalable GPU inference node.", "inno": "Novel use of sparse attention for 3D volumetric data."},
            # 1. Quantum Forge (Decentralized Supply Chain)
            {"name": "ChainTrust", "problem": "Lack of transparency and tampering in supply chain tracking.", "solution": "A blockchain-backed ledge providing real-time, immutable tracking of goods from origin to destination.", "tech": "Solidity, Node.js, Next.js, Ethereum", "arch": "Smart contracts integrated with a traditional caching layer for speed.", "inno": "Hybrid off-chain indexing for rapid search capabilities."},
            # 2. Cyber Sentinels (Real-Time Threat Detection)
            {"name": "SentinelNet", "problem": "Traditional firewalls struggle against zero-day network intrusions.", "solution": "A machine-learning packet inspector that identifies behavioral anomalies indicative of attacks.", "tech": "Go, TensorFlow, Kafka, React", "arch": "Stream processing architecture using Kafka for high-throughput packet ingestion.", "inno": "Implementation of unsupervised clustering for zero-day threat detection."},
            # 3. Data Alchemists (Predictive Climate Modeling)
            {"name": "AtmoCast", "problem": "Micro-climate predictions are computationally expensive and slow.", "solution": "A deep learning model trained on satellite and IoT sensor data for hyper-local, fast weather forecasts.", "tech": "Python, JAX, FastAPI, Svelte", "arch": "Serverless inference endpoints coupled with a heavy batch training pipeline.", "inno": "Utilization of JAX for highly optimized tensor operations."},
            # 4. Code Crusaders (Smart City Traffic Optimization)
            {"name": "FlowCity", "problem": "Inefficient traffic light timing causing severe urban congestion.", "solution": "An adaptive traffic light control system using computer vision to monitor intersection density in real-time.", "tech": "C++, OpenCV, Node.js, Express", "arch": "Edge AI processing on camera nodes with centralized orchestration.", "inno": "Lightweight YOLOv8 deployment on low-power edge devices."},
            # 5. Pixel Pioneers (AR-Enhanced Education Platform)
            {"name": "HoloLearn", "problem": "Abstract scientific concepts are difficult for students to visualize.", "solution": "An AR application that overlays interactive 3D models onto physical textbooks.", "tech": "Unity, C#, ARCore, Firebase", "arch": "Client-heavy AR application with cloud-synced user progression and analytics.", "inno": "Markerless tracking combined with real-time physics interactions."},
            # 6. Cloud Catalysts (Serverless ML Pipeline)
            {"name": "ServerlessML", "problem": "Deploying machine learning models requires complex DevOps knowledge.", "solution": "A drag-and-drop platform for deploying ML models entirely on serverless infrastructure.", "tech": "Python, AWS Lambda, React, Terraform", "arch": "Fully event-driven architecture using AWS Lambda and S3 triggers.", "inno": "Automated Docker container optimization for Lambda cold-start reduction."},
        ]

        for idx, team in enumerate(teams):
            details = project_details[idx]
            sub = ProjectSubmission(
                team_id=team.id,
                project_name=details["name"],
                problem_statement=details["problem"],
                solution_description=details["solution"],
                tech_stack=details["tech"],
                github_url=f"https://github.com/hackathon/{details['name'].lower().replace(' ', '-')}",
                readme_content=f"# {details['name']}\n\n## Problem\n{details['problem']}\n\n## Solution\n{details['solution']}\n\n## Setup\n`npm install && npm start`",
                architecture_summary=details["arch"],
                innovation_notes=details["inno"],
            )
            db.add(sub)
        db.flush()
        print(f"Created {len(teams)} project submissions")

        # ══════════════════════════════════════════════
        # 4. MENTOR USERS + PROFILES + ASSIGNMENTS (5 mentors)
        # ══════════════════════════════════════════════
        mentor_data = [
            ("mentor_sarah",   "Sarah Richardson",  "AI/ML, Computer Vision, NLP"),
            ("mentor_david",   "David Nakamura",    "Cloud Architecture, DevOps, Microservices"),
            ("mentor_elena",   "Elena Volkov",      "Cybersecurity, Blockchain, Distributed Systems"),
            ("mentor_raj",     "Raj Krishnan",      "Data Engineering, Big Data, Analytics"),
            ("mentor_lisa",    "Lisa Hayward",      "Mobile Development, UI/UX, Product Design"),
        ]

        mentor_profiles = []
        for username, name, expertise in mentor_data:
            mentor_user = User(
                username=username,
                password_hash=hashed_pw,
                role=UserRole.MENTOR,
                is_active=True,
                event_id="default",
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

        # Assign mentors to teams
        mentor_team_assignments = [
            (0, [0, 1]),        # Sarah -> Neural Nexus, Quantum Forge
            (1, [2, 4]),        # David -> Cyber Sentinels, Code Crusaders
            (2, [3]),           # Elena -> Data Alchemists
            (3, [5]),           # Raj   -> Pixel Pioneers
            (4, [6]),           # Lisa  -> Cloud Catalysts
        ]

        import random
        for mentor_idx, team_indices in mentor_team_assignments:
            for team_idx in team_indices:
                expertise = mentor_data[mentor_idx][2]
                score = round(random.uniform(85.0, 98.0), 1)
                assignment = MentorAssignment(
                    mentor_id=mentor_profiles[mentor_idx].id,
                    team_id=teams[team_idx].id,
                    match_score=score,
                    rationale=f"Mentor expertise in {expertise[:30]}... aligns perfectly with team challenge.",
                )
                db.add(assignment)
                
        db.flush()
        print(f"Created {len(mentor_data)} mentors with team assignments")

        # ══════════════════════════════════════════════
        # 5. JUDGE USERS + PROFILES + JUDGE RECORDS (3 judges)
        # ══════════════════════════════════════════════
        judge_data = [
            ("judge_michael",  "Dr. Michael Torres",   "michael.torres@ieee.org",          "ML Systems, Scalability"),
            ("judge_priyanka", "Prof. Priyanka Desai",  "priyanka.desai@acm.org",           "HCI, Design Thinking"),
            ("judge_robert",   "Robert Chang",          "robert.chang@techventures.com",    "Product Strategy, Architecture"),
        ]

        judge_profiles_list = []
        judge_records = []

        for username, name, email, expertise in judge_data:
            judge_user = User(
                username=username,
                password_hash=hashed_pw,
                role=UserRole.JUDGE,
                is_active=True,
                event_id="default",
            )
            db.add(judge_user)
            db.flush()

            j_profile = JudgeProfile(
                user_id=judge_user.id,
                expertise=expertise,
            )
            db.add(j_profile)
            db.flush()
            judge_profiles_list.append(j_profile)

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
        # 6. SCORE RECORDS
        # ══════════════════════════════════════════════
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
            # Judge 2 (Robert Chang) scores teams 4-6
            (2, 4, 8.0, 8.5, 7.0, 8.5, 9.0),
            (2, 5, 7.5, 7.0, 8.0, 7.0, 7.5),
            (2, 6, 9.0, 8.0, 7.5, 8.0, 8.5),
        ]

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
                is_anomalous=(scores_created == 2), # Make the third score anomalous
                submitted_at=datetime.utcnow() - timedelta(days=7 - team_idx),
                notes=f"Solid work on {teams[team_idx].challenge}. "
                      f"{'Impressive innovation.' if inno > 8.0 else 'Room for improvement in novelty.'}",
            )
            db.add(score)
            scores_created += 1

        db.flush()

        # Seed some dummy certificates for the first team
        from models import Certificate
        for member in teams[0].members:
            username = member.email.split('@')[0]
            user = db.query(User).filter(User.username == username).first()
            if user:
                cert = Certificate(
                    user_id=user.id,
                    certificate_type="PARTICIPATION",
                    is_published=True,
                    download_url=f"https://dummy-ipfs-hash.io/cert_{user.id}.pdf"
                )
                db.add(cert)
        db.flush()

        # Update team final scores
        for team in teams:
            team_scores = db.query(Score).filter(Score.team_id == team.id).all()
            if team_scores:
                avg_score = sum(s.weighted_total for s in team_scores) / len(team_scores)
                team.final_score = round(avg_score, 2)

        # Assign ranks
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
            (ApprovalType.TEAM_REVIEW,                teams[0].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.TEAM_REVIEW,                teams[1].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.MENTOR_ASSIGNMENT_REVIEW,   teams[2].id, ApprovalStatus.APPROVED, "admin"),
            (ApprovalType.ANOMALY_REVIEW,             teams[3].id, ApprovalStatus.PENDING,  None),
            (ApprovalType.RESULT_PUBLICATION_REVIEW,   teams[4].id, ApprovalStatus.PENDING,  None),
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
        print(f"  Users:           {db.query(User).count()}")
        print(f"  Participants:    {db.query(Participant).count()}")
        print(f"  Teams:           {db.query(Team).count()}")
        print(f"  Mentor Profiles: {db.query(MentorProfile).count()}")
        print(f"  Judge Profiles:  {db.query(JudgeProfile).count()}")
        print(f"  Judges:          {db.query(Judge).count()}")
        print(f"  Scores:          {db.query(Score).count()}")
        print(f"  Approvals:       {db.query(Approval).count()}")
        print(f"  Mentor Assigns:  {db.query(MentorAssignment).count()}")
        print("=" * 50)
        print("\nDefault credentials (all accounts):")
        print(f"  Password:    {DEFAULT_PASSWORD}")
        print(f"  Admin:       admin / {DEFAULT_PASSWORD}")
        print(f"  Participant: aarav / {DEFAULT_PASSWORD}")
        print(f"  Mentor:      mentor_sarah / {DEFAULT_PASSWORD}")
        print(f"  Judge:       judge_michael / {DEFAULT_PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"ERROR during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
