import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_skills_and_experience(raw_bio: str) -> dict:
    """
    Takes messy user input and returns clean JSON tags.
    """
    prompt = f"""
    You are a data extraction assistant for a hackathon registration system.
    Read the participant's raw bio and extract their technical skills and experience level.

    CRITICAL RULES:
    1. skill_tags: Extract core technical skills as a single, comma-separated string (e.g., "Python, React, AWS"). Limit to 5 skills.
    2. experience: Classify the user as exactly one of these: "junior", "mid", or "senior".

    Return ONLY a valid JSON object in this exact format:
    {{
      "skill_tags": "Skill1, Skill2",
      "experience": "junior"
    }}

    User Input: {raw_bio}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    
    return json.loads(response.text)


def generate_team_rationale(prepared_prompt: str) -> str:
    """
    Executes the prompt already written in team_formation.py.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prepared_prompt
    )
    return response.text.strip()


def allocate_mentor_and_draft_intro(team_data: dict, mentor_data: dict) -> dict:
    """
    Matches a team to a mentor and drafts the introduction email.
    """
    prompt = f"""
    You are an AI assistant helping a hackathon committee connect student teams with industry mentors.
    
    Team Information: {json.dumps(team_data)}
    Mentor Information: {json.dumps(mentor_data)}

    CRITICAL RULES:
    1. rationale: Write a 1-sentence explanation of why this mentor's expertise is a perfect fit for the team's tech stack or project goal.
    2. email_draft: Write a warm, professional introductory email from the organizing committee to the mentor, introducing them to the team. Keep it under 4 sentences.

    Return ONLY a valid JSON object in this exact format:
    {{
      "rationale": "...",
      "email_draft": "..."
    }}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    
    return json.loads(response.text)


def generate_event_summary_report(team_submissions: list) -> str:
    """
    Analyzes the final submissions, including project descriptions/READMEs, 
    and writes a 1-page executive summary.
    """
    prompt = f"""
    You are the lead technical writer for a major hackathon. The event has just concluded.
    
    Here is the detailed submission data from the teams, including their project descriptions, GitHub README snippets, and final scores:
    {json.dumps(team_submissions, indent=2)}
    
    Write a comprehensive 1-page executive summary of the hackathon's performance. Structure the report exactly as follows:
    
    # Hackathon Executive Summary
    
    ## 🌟 Event Overview
    Write an energetic summary of the event's overall success, the ambition of the projects, and the general quality of the submissions.
    
    ## 🏆 Top Innovations & Winners
    Highlight the top-scoring teams. Explain what they built, the technical complexity of their solutions (based on their READMEs/descriptions), and why they stood out.
    
    ## 🚀 Technical Trends & Insights
    Analyze the tech stacks and project domains across all submissions. Identify emerging trends (e.g., "Many teams utilized generative AI," "Heavy reliance on modern frontend frameworks," or "Strong focus on healthcare solutions").
    
    CRITICAL RULES:
    - Do not use generic placeholders.
    - Ground all facts, team names, tech stacks, and technical claims ONLY in the provided JSON data.
    - Use clean, professional Markdown formatting.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text.strip()

# --- Quick Local Test ---
if __name__ == "__main__":
    print(" Starting comprehensive AI Engine test...\n")

    # --- Test 1: Skill Extraction ---
    print("--- Testing 1: Skill Extraction ---")
    sample_bio = "I am a sophomore studying CS. I know how to build websites with React and Node.js, and I've deployed some stuff on AWS. I'm pretty new to hackathons though."
    skills_result = extract_skills_and_experience(sample_bio)
    print(json.dumps(skills_result, indent=2))

    # --- Test 2: Team Rationale ---
    print("\n--- Testing 2: Team Rationale ---")
    sample_prompt = """You are the lead organizer of a competitive hackathon. You have just algorithmically formed a team and need to explain to the approval committee WHY this specific group of students was put together.
    Team Name: Team Alpha
    Members:
    - Alice (MIT) | Skills: React, Tailwind | Level: junior
    - Bob (Stanford) | Skills: Node.js, PostgreSQL | Level: mid
    - Charlie (IIT) | Skills: AWS, Docker | Level: senior
    Write a professional, concise 2 to 3 sentence rationale for this team. DO NOT use bullet points. Specifically mention how their skills complement each other. Highlight their institutional diversity and how their mix of experience levels creates a balanced dynamic. Ground your entire response ONLY in the data provided above."""
    rationale_result = generate_team_rationale(sample_prompt)
    print(rationale_result)

    # --- Test 3: Mentor Allocation ---
    print("\n--- Testing 3: Mentor Allocation ---")
    sample_team = {
        "team_name": "Code Crusaders",
        "skills": ["React", "FastAPI", "PostgreSQL"],
        "challenge": "Build a scalable scheduling app"
    }
    sample_mentor = {
        "name": "Dr. Alan Grant",
        "expertise": "Backend Architecture, Database Scaling, Python"
    }
    mentor_result = allocate_mentor_and_draft_intro(sample_team, sample_mentor)
    print(json.dumps(mentor_result, indent=2))

# --- Test 4: Event Summary Report ---
    print("\n--- Testing 4: Event Summary Report ---")
    sample_submissions = [
        {
            "rank": 1, 
            "team_name": "HealthSync", 
            "score": 9.5, 
            "tech_stack": "React, Python, Gemini API", 
            "readme_snippet": "HealthSync is an AI-powered hospital triaging system. We utilized the Gemini API to parse patient intake forms and prioritize them based on urgency. The backend is powered by FastAPI, ensuring sub-second response times during high-load ER situations."
        },
        {
            "rank": 2, 
            "team_name": "FinFlex", 
            "score": 8.8, 
            "tech_stack": "Vue, Node.js, PostgreSQL", 
            "readme_snippet": "A micro-lending platform designed for college students. We implemented a custom risk-assessment algorithm in Node.js that looks at university standing and major rather than traditional credit scores. All transactional data is secured in PostgreSQL."
        },
        {
            "rank": 3, 
            "team_name": "EcoTrack", 
            "score": 8.2, 
            "tech_stack": "React, Django, Gemini API", 
            "readme_snippet": "EcoTrack scans grocery receipts using OCR and the Gemini AI to calculate the carbon footprint of your shopping trip. We built a smooth React frontend for users to track their weekly emissions and get AI-suggested sustainable alternatives."
        }
    ]
    summary_result = generate_event_summary_report(sample_submissions)
    print(summary_result)
    
    print("\n All tests completed successfully!")