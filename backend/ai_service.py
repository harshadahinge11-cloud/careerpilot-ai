"""
Free AI integration (Google Gemini) for CareerPilot AI.
Uses only the Python standard library -> no extra packages needed.
Get a free key: https://aistudio.google.com/apikey
"""
import os
import json
import time
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from backend.database import get_connection

LAST_ERROR = ""

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


_WORKING_MODEL = None
_BAD_MODELS = set()    # models that returned 404 once - skipped afterwards
_DISCOVERED = []       # models your key can really use (asked from Google)
_DISCOVERY_DONE = False


def _discover_models(api_key):
    """Ask Google which models this key can use. Done once, errors ignored."""
    global _DISCOVERY_DONE, _DISCOVERED
    if _DISCOVERY_DONE:
        return
    _DISCOVERY_DONE = True
    try:
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100",
            headers={"x-goog-api-key": api_key},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = []
        for m in data.get("models", []):
            name = m.get("name", "").replace("models/", "")
            methods = m.get("supportedGenerationMethods", [])
            if (name.startswith("gemini") and "generateContent" in methods
                    and not any(x in name for x in
                                ("embedding", "tts", "image", "live", "audio",
                                 "robotics", "computer", "customtools"))):
                names.append(name)
        # prefer fast "flash" models, then the rest
        flash = [n for n in names if "flash" in n and "lite" not in n]
        lite = [n for n in names if "lite" in n]
        other = [n for n in names if n not in flash and n not in lite]
        _DISCOVERED = (flash + lite + other)[:8]
        print("[AI] Models available for your key:", _DISCOVERED)
    except Exception as e:
        print("[AI] Could not list models:", e)


def _model_candidates():
    env_model = (os.getenv("GEMINI_MODEL") or "").strip()
    models = [_WORKING_MODEL] + _DISCOVERED + [env_model, "gemini-flash-latest",
              "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    seen, result = set(), []
    for m in models:
        if m and m not in seen and m not in _BAD_MODELS:
            seen.add(m)
            result.append(m)
    return result or ["gemini-flash-latest"]


def _google_message(body):
    try:
        return json.loads(body)["error"]["message"][:160]
    except Exception:
        return body[:160]


def _call_gemini(system_prompt, contents, max_tokens=1500):
    """Returns reply text, or None if anything goes wrong (caller falls back)."""
    global LAST_ERROR, _WORKING_MODEL
    LAST_ERROR = ""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key:
        LAST_ERROR = "GEMINI_API_KEY not set (check .env file)"
        print("[AI]", LAST_ERROR)
        return None

    _discover_models(api_key)

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    # Up to 3 rounds. In each round every model is tried once.
    # 404 = model name not found, 429/500/503 = Google busy -> try next model / wait.
    for attempt in range(3):
        for model in _model_candidates():
            req = urllib.request.Request(
                GEMINI_URL.format(model=model),
                data=body_bytes,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=40) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if not text:
                    LAST_ERROR = "AI returned an empty answer"
                    return None
                _WORKING_MODEL = model
                LAST_ERROR = ""
                return text
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "ignore")
                LAST_ERROR = (f"Gemini HTTP error {e.code} (model: {model}): "
                              f"{_google_message(body)}")
                print("[AI] HTTP error:", e.code, "model:", model, body[:300])
                if e.code == 400 and "thinking" in body.lower():
                    payload["generationConfig"].pop("thinkingConfig", None)
                    body_bytes = json.dumps(payload).encode("utf-8")
                    continue
                if e.code == 404:
                    _BAD_MODELS.add(model)   # do not try this model again
                    continue
                if e.code in (429, 500, 502, 503, 504):
                    continue          # busy -> try the next model
                return None           # 400/401/403 etc: retrying will not help
            except Exception as e:
                LAST_ERROR = f"{type(e).__name__}: {e}"
                print("[AI] Error:", e)
                continue
        if attempt < 2:
            time.sleep(2 + attempt * 2)   # wait a little, then try again
    if "503" in LAST_ERROR or "429" in LAST_ERROR:
        LAST_ERROR += " - Google AI is busy right now. Please click Analyze again in a minute."
    return None


# ---------------------------------------------------------
# COACH
# ---------------------------------------------------------
def _coach_config():
    """Reads settings saved from the admin 'Coach' page."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT configuration FROM coach_configuration WHERE id = 1"
        ).fetchone()
        conn.close()
        return json.loads(row["configuration"]) if row else {}
    except Exception:
        return {}


def _build_system_prompt():
    cfg = _coach_config()
    name = cfg.get("coachName") or "CareerPilot AI"
    prompt = (
        f"You are {name}, an AI career coach inside the CareerPilot AI web app. "
        "Help students and job seekers with career planning, job roles, skills, "
        "learning roadmaps, projects, resumes, interviews and certifications. "
        "Be practical and specific. If a question is unrelated to careers, "
        "politely steer back to career topics. "
        f"Tone: {cfg.get('personality') or 'Friendly and professional'}. "
        f"Answer length: {cfg.get('responseLength') or 'Detailed'}. "
        "IMPORTANT: Always reply in English only, using simple clear English. "
        "Even if the student writes in Hindi, Marathi or Hinglish, or earlier "
        "replies in this chat were in another language, answer in English. "
        "Use plain text with short paragraphs and simple '•' bullets; "
        "do not use markdown symbols like ** or #."
    )
    if cfg.get("topics"):
        prompt += f" Focus topics: {cfg['topics']}."
    if cfg.get("beginnerMode", True):
        prompt += " Explain things simply for beginners."
    if cfg.get("roadmapMode", True):
        prompt += " When useful, give step-by-step learning roadmaps."
    if cfg.get("followUpMode", True):
        prompt += " End with one short follow-up question."
    if cfg.get("systemPrompt"):
        prompt += " Extra instructions from admin: " + cfg["systemPrompt"]
    return prompt


def _recent_history(user_id, limit=6):
    if not user_id:
        return []
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT message, response FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
    except Exception:
        return []
    contents = []
    for r in reversed(rows):
        # Gemini rejects empty text, so skip incomplete rows
        if not (r["message"] or "").strip() or not (r["response"] or "").strip():
            continue
        contents.append({"role": "user", "parts": [{"text": r["message"][:2000]}]})
        contents.append({"role": "model", "parts": [{"text": r["response"][:2000]}]})
    return contents


TOPICS = {
    "career": "career choices and career paths",
    "skills": "the skills to learn and how to learn them",
    "jobs": "jobs, job search and becoming job ready",
    "interview": "interview preparation and common interview questions",
    "mca": "MCA students: specializations, projects, internships and placements",
}


def ai_coach_reply(message, user_id=None, topic=None):
    system = _build_system_prompt()
    if topic and topic.lower() in TOPICS:
        system += (
            f" The student selected the topic '{topic.lower()}'. "
            f"Focus your answer on {TOPICS[topic.lower()]}."
        )
    question = {"role": "user", "parts": [{"text": message}]}

    # 1st try: with chat memory
    history = _recent_history(user_id)
    text = _call_gemini(system, history + [question])
    if text:
        return text

    # 2nd try: without memory (in case old history caused the error)
    if history:
        print("[AI] Retrying without chat history...")
        return _call_gemini(system, [question])
    return None


# ---------------------------------------------------------
# RESUME
# ---------------------------------------------------------
def ai_resume_feedback(resume_text):
    system = (
        "You are an expert resume reviewer and ATS specialist. Always write in English. "
        "Read the resume text and give exactly 5 specific, actionable improvement "
        "suggestions. Output exactly 5 lines, one suggestion per line, each under "
        "200 characters, no numbering, no markdown, no extra text."
    )
    contents = [{"role": "user", "parts": [{"text": resume_text[:6000]}]}]
    text = _call_gemini(system, contents, max_tokens=800)
    if not text:
        return []
    lines = [l.strip().lstrip("-*•0123456789. ").strip() for l in text.splitlines()]
    return ["AI: " + l for l in lines if l][:5]


# ---------------------------------------------------------
# SKILL GAP
# ---------------------------------------------------------
def ai_skill_gap_advice(role_name, current_skills, missing_skills):
    """Returns a list of up to 5 short advice lines (empty list if AI fails)."""
    if not missing_skills:
        return []
    system = (
        "You are a career coach. Always write in English. A student wants to become a given job role. "
        "Based on their current skills and missing skills, give exactly 5 short, "
        "practical tips: what to learn first, a mini project idea, and a free "
        "resource type. Output exactly 5 lines, one tip per line, each under "
        "200 characters, no numbering, no markdown, no extra text."
    )
    prompt = (
        f"Target role: {role_name}\n"
        f"Current skills: {', '.join(current_skills) or 'none detected'}\n"
        f"Missing skills: {', '.join(missing_skills)}"
    )
    text = _call_gemini(
        system, [{"role": "user", "parts": [{"text": prompt}]}], max_tokens=800
    )
    if not text:
        return []
    lines = [l.strip().lstrip("-*•0123456789. ").strip() for l in text.splitlines()]
    return [l for l in lines if l][:5]


# ---------------------------------------------------------
# JOB MATCHING
# ---------------------------------------------------------
def ai_job_insight(current_skills, top_roles):
    """top_roles: list of {title, score, missing:[...]}. Returns up to 4 lines."""
    if not top_roles:
        return []
    system = (
        "You are a career coach. Always write in English. Given a student's skills and their best matching "
        "job roles with match percentages and missing skills, give exactly 4 short "
        "lines of advice: (1) which role to target first and why, (2) the most "
        "valuable skill to learn next, (3) a project idea that proves it, "
        "(4) one tip for applying to jobs. Each line under 220 characters, no "
        "numbering, no markdown, no extra text."
    )
    role_text = "\n".join(
        f"- {r.get('title')}: {r.get('score')}% match, missing: "
        f"{', '.join(r.get('missing', [])[:8]) or 'nothing'}"
        for r in top_roles[:3]
    )
    prompt = (
        f"Student skills: {', '.join(current_skills[:40]) or 'none detected'}\n"
        f"Top matching roles:\n{role_text}"
    )
    text = _call_gemini(
        system, [{"role": "user", "parts": [{"text": prompt}]}], max_tokens=800
    )
    if not text:
        return []
    lines = [l.strip().lstrip("-*•0123456789. ").strip() for l in text.splitlines()]
    return [l for l in lines if l][:4]
