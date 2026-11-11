# CareerPilot AI

An AI-powered career guidance platform that helps students and job seekers
analyse their resume, find skill gaps, get personalised roadmaps and chat
with an AI career coach.

## Features
- Resume analysis with ATS score
- Skill gap analysis for target job roles
- Personalised learning roadmaps
- Job matching
- AI career coach (Google Gemini)
- Admin dashboard to manage users, roles, skills and reports

## Tech Stack
- **Backend:** Python, FastAPI
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **AI:** Google Gemini API

## Run Locally

1. Clone the repository
-git clone https://github.com/YOUR-USERNAME/careerpilot-ai.git
cd careerpilot-ai
2. Create and activate a virtual environment
-python -m venv venv
venv\Scripts\activate
3. Install dependencies
-pip install -r requirements.txt
4. Create a `.env` file (copy `.env.example`) and add your own Gemini key
5. Start the server
-uvicorn backend.main:app --reload
6. Open http://127.0.0.1:8000

## Project Status
Minor project (v1.0). Major project upgrades are in progress.