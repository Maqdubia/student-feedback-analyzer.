import json
import os
import smtplib
from email.message import EmailMessage
from html import escape

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# Groq provides an OpenAI-compatible API.
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

TRAINER_EMAIL = os.getenv("TRAINER_EMAIL", "").strip()


def analyse_feedback(feedback):
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = f"""Analyse the following student's feedback.

Feedback: {feedback}

Return JSON with exactly these fields:
- sentiment
- key_points (array of strings)
- suggestion

Example:
{{
  "sentiment": "Positive",
  "key_points": ["Good teaching"],
  "suggestion": "Include more real-world projects"
}}"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        messages=[
            {
                "role": "system",
                "content": "You are a student feedback analyser. Return only valid JSON with sentiment, key_points (array), and suggestion.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    key_points = data.get("key_points", [])
    if isinstance(key_points, str):
        key_points = [key_points]
    return {
        "sentiment": str(data.get("sentiment", "Unknown")),
        "key_points": [str(point) for point in key_points],
        "suggestion": str(data.get("suggestion", "")),
    }


def send_to_trainer(student, result):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    if not user or not password:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD are not configured")
    if not TRAINER_EMAIL:
        raise RuntimeError("TRAINER_EMAIL is not configured")

    points_text = "\n".join(f"  - {point}" for point in result["key_points"])
    text = f"""New student feedback

Student : {student['name']} ({student['email']})
Course  : {student['course']}
Rating  : {student['rating']}/5

Feedback:
{student['feedback']}

--- Analysis ---
Sentiment : {result['sentiment']}

Key points:
{points_text}

Suggestion:
{result['suggestion']}
"""

    points_html = "".join(f"<li>{escape(point)}</li>" for point in result["key_points"])
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;color:#302442">
      <h2 style="margin:0 0 4px">New student feedback</h2>
      <p style="margin:0 0 16px;color:#766987">
        {escape(student['name'])} ({escape(student['email'])}) &middot;
        {escape(student['course'])} &middot; {escape(str(student['rating']))}/5
      </p>
      <blockquote style="margin:0 0 20px;padding:10px 14px;background:#f5f0ff;border-left:3px solid #9875c9">
        {escape(student['feedback'])}
      </blockquote>
      <p><strong>Sentiment:</strong> {escape(result['sentiment'])}</p>
      <p style="margin-bottom:4px"><strong>Key points</strong></p>
      <ul style="margin-top:0">{points_html}</ul>
      <p><strong>Suggestion:</strong> {escape(result['suggestion'])}</p>
    </div>
    """

    msg = EmailMessage()
    msg["Subject"] = f"Student feedback: {student['name']} ({result['sentiment']})"
    msg["From"] = user
    msg["To"] = TRAINER_EMAIL
    msg["Reply-To"] = student["email"]
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    student = {
        "name": str(data.get("name", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "course": str(data.get("course", "")).strip(),
        "rating": str(data.get("rating", "")).strip(),
        "feedback": str(data.get("feedback", "")).strip(),
    }

    missing = [key for key in ("name", "email", "course", "rating", "feedback") if not student[key]]
    if missing:
        return jsonify(error=f"Please fill in: {', '.join(missing)}."), 400

    try:
        result = analyse_feedback(student["feedback"])
    except Exception:
        app.logger.exception("Groq analysis failed")
        return jsonify(error="Could not analyse the feedback. Check GROQ_API_KEY and GROQ_MODEL in Render Environment."), 502

    email_sent, email_error = False, None
    try:
        send_to_trainer(student, result)
        email_sent = True
    except Exception as exc:
        app.logger.exception("Email delivery failed")
        email_error = str(exc)

    return jsonify(
        result=result,
        email_sent=email_sent,
        email_error=email_error,
        trainer=TRAINER_EMAIL,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)
