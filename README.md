# CareerHub – Student Career Platform

A beginner-friendly college project built with **Python Flask, SQLite, HTML, and CSS**.

## Features
- Student sign up, login, and profile
- SkillSwap: list skills to teach/learn and connect with other students
- Project portfolio plus team-finding board: publish a project in progress, list required skills/roles, receive connection requests, accept/decline requests, and chat with accepted collaborators
- Mock interview: broad role catalogue plus custom role entry, with predefined questions and basic answer-writing feedback; unfamiliar roles fall back to general questions
- Career recommendations: saves student skills/interests and ranks official company career pages using simple keyword matching
- Basic opportunity list and saved/application tracking for demo purposes

## Project collaboration workflow
1. Publish a collaboration post with the project description and required skills.
2. Other students send a connection request with a short message.
3. The project owner accepts or declines requests under Project Chats.
4. Accepted participants can exchange messages in the project chat.

## Important limitations
- The mock interview feedback is rule-based and does not assess technical correctness.
- Career recommendations are keyword-based, not AI-generated.
- Company links lead to official career pages. A career page does **not** mean a specific internship is currently open; students must check the company page for current openings and eligibility.
- Any preloaded opportunity entries are demo/sample content. Do not present them as verified live jobs.
- The built-in demo admin flow is for classroom demonstration only, not production security.

## Run locally
1. Install Python 3.10 or newer.
2. Extract the ZIP and open a terminal in the `CareerHub` folder.
3. Create a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Run: `python app.py`
6. Open `http://127.0.0.1:5000`

## Deploy on Render
- Push the contents of this folder to your own GitHub repository.
- In Render, create a **Web Service** from that repository.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add environment variable `SECRET_KEY` with a long random value.
- SQLite data can be lost on ephemeral hosting/redeploy unless a persistent disk is configured. For a durable production app, use a managed database.

## Suggested demo flow
1. Create two student accounts.
2. Add different SkillSwap listings and send a connection request.
3. Add a project and show the portfolio.
4. Open Mock Interview and submit a practice answer.
5. Add skills/interests in Career Recommendations and open a company career page.

## Environment
See `.env.example`. Never commit real passwords or API keys.
