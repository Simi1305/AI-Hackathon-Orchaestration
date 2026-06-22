"""
setup_demo.py  -  one-command demo state for EventFlow.

Run this (with the backend already running on http://localhost:8000) to load a
clean, presentation-ready state:
  - 20 participants across 5 institutions (4 each)
  - 5 balanced teams of 4 (one member per institution)
  - all teams scored, with ONE team held by the anomaly engine
  - a welcome message delivered to participants

Usage:
    # make sure users exist first (only needed once):  python seed.py
    # start the API:                                    python -m uvicorn main:app
    # then in another terminal:                         python setup_demo.py
"""
import json, urllib.request, urllib.error

BASE = "http://localhost:8000"

def call(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        return e.code, None

def login(u):
    _, j = call("POST", "/auth/login", body={"username": u, "password": "password123"})
    return j["access_token"] if j else None

ROSTER = [
 ("Aarav Sharma","aarav@mit.edu","MIT","ML,Python,TensorFlow","senior"),
 ("Ananya Reddy","ananya@mit.edu","MIT","ML,PyTorch,Computer Vision","senior"),
 ("Rohan Gupta","rohang@mit.edu","MIT","Mobile,Flutter,Dart","mid"),
 ("Chloe Martinez","chloe@mit.edu","MIT","Design,UI/UX,Adobe","mid"),
 ("Priya Patel","priya@stanford.edu","Stanford University","Backend,Java,Spring","mid"),
 ("Noah Johnson","noah@stanford.edu","Stanford University","Backend,Python,FastAPI","mid"),
 ("Emma Davis","emma@stanford.edu","Stanford University","ML,NLP,Python","senior"),
 ("Lucas Anderson","lucas@stanford.edu","Stanford University","Data,Python,Spark","mid"),
 ("Liam Chen","liam@iitdelhi.edu","IIT Delhi","Frontend,React,TypeScript","mid"),
 ("Isabella Kim","isabella@iitdelhi.edu","IIT Delhi","Frontend,Vue,JavaScript","mid"),
 ("Oliver Wilson","oliver@iitdelhi.edu","IIT Delhi","Backend,Go,PostgreSQL","mid"),
 ("Aisha Khan","aisha@iitdelhi.edu","IIT Delhi","Security,Cryptography,Python","senior"),
 ("Sofia Garcia","sofia@ucberkeley.edu","UC Berkeley","DevOps,Docker,Kubernetes","senior"),
 ("Mason Brown","mason@ucberkeley.edu","UC Berkeley","Data,SQL,Pandas","junior"),
 ("Mia Tanaka","mia@ucberkeley.edu","UC Berkeley","Frontend,React,Tailwind","junior"),
 ("James Taylor","james@ucberkeley.edu","UC Berkeley","Mobile,React Native,JavaScript","junior"),
 ("Ethan Williams","ethan@cmu.edu","Carnegie Mellon","Design,Figma,CSS","junior"),
 ("Zara Ahmed","zara@cmu.edu","Carnegie Mellon","Security,Networking,Linux","senior"),
 ("Arjun Nair","arjun@cmu.edu","Carnegie Mellon","DevOps,AWS,Terraform","senior"),
 ("Neha Verma","neha@cmu.edu","Carnegie Mellon","ML,Deep Learning,Python","senior"),
]

def mk(i,t,p,f,im):
    return {"innovation":i,"technical_depth":t,"presentation":p,"feasibility":f,"impact":im}

def main():
    admin = login("admin")
    if not admin:
        print("ERROR: could not log in as admin. Run 'python seed.py' first, and make sure the API is running.")
        return
    print("Logged in as admin.")
    call("POST", "/api/v1/organizer/reset-event", admin)
    call("PUT", "/api/v1/organizer/event-config", admin, {"team_size":4,"max_same_institution":1})
    parts = [{"name":n,"email":e,"institution":inst,"skill_tags":sk,"experience":x} for (n,e,inst,sk,x) in ROSTER]
    call("POST", "/upload-roster/", admin, {"participants":parts})
    print("Uploaded 20 participants.")
    call("POST", "/api/v1/trigger-team-formation", admin, {})
    call("POST", "/api/v1/organizer/approvals/approve-team-formations", admin)
    print("Formed and approved 5 teams of 4.")

    _, teams = call("GET", "/api/v1/teams/", admin)
    m, p, rb = login("judge_michael"), login("judge_priyanka"), login("judge_robert")
    panels = [
      [mk(6.0,6.5,6.0,6.5,6.0), mk(6.5,7.0,6.5,6.0,6.5), mk(9.5,9.8,9.0,9.5,9.5)],  # team0 = anomaly
      [mk(8.0,8.4,7.9,8.1,7.8), mk(8.2,8.6,8.1,8.3,8.0), mk(7.9,8.5,8.0,8.2,7.9)],
      [mk(7.4,7.6,7.3,7.5,7.2), mk(7.6,7.4,7.5,7.3,7.4), mk(7.5,7.5,7.4,7.6,7.3)],
      [mk(6.9,7.1,6.8,7.0,6.9), mk(7.1,6.9,7.0,6.8,7.1), mk(7.0,7.0,7.1,7.2,7.0)],
      [mk(6.4,6.6,6.3,6.5,6.4), mk(6.6,6.4,6.5,6.3,6.6), mk(6.5,6.5,6.4,6.6,6.5)],
    ]
    for i, team in enumerate(teams):
        pl = panels[i % len(panels)]
        for tok, vec in zip((m,p,rb), pl):
            call("POST", f"/api/v1/judge/teams/{team['id']}/score", tok, vec)
    print("Scored all teams (one anomaly baked in).")

    call("POST", "/api/v1/organizer/communications/send", admin,
         {"communication_type":"team_welcome","subject":"Welcome to the Hackathon!",
          "body":"Your team is set. Check your dashboard for your teammates and mentor. Good luck!"})
    print("Sent welcome message to participants.")

    # NOTE: certificates are intentionally NOT generated/published here.
    # Generate + Publish them live during the demo (organizer Certificates tab),
    # then the participant can download theirs.

    _, lb = call("GET", "/api/v1/leaderboard", admin)
    print("\nLeaderboard:")
    for e in (lb or {}).get("entries", []):
        status = "HELD (anomaly)" if e["is_held"] else f"#{e['rank']}  {e['final_score']}"
        print(f"  {e['team_name']:16} {status}")
    print("\nDemo state ready. Log in as admin / aarav / judge_michael (password123).")

if __name__ == "__main__":
    main()
