# Student Feedback Analyzer — Lavender + Groq

## Render settings
- Environment: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- If the project files are inside a repository subfolder, set that folder as Render's Root Directory. Otherwise leave Root Directory blank.

## Render Environment Variables
Required for AI analysis:
- `GROQ_API_KEY`: your Groq API key
- `GROQ_MODEL`: `openai/gpt-oss-20b` (or another model enabled for your Groq account)

Email variables:
- `TRAINER_EMAIL`: destination address
- `SMTP_USER`: your Gmail address
- `SMTP_PASSWORD`: Gmail App Password (not your normal Gmail password)
- `SMTP_HOST`: `smtp.gmail.com`
- `SMTP_PORT`: `587`

Important: Render Free web services block outbound SMTP ports 25, 465, and 587. On Render Free, AI analysis can work but Gmail SMTP delivery will fail. Use an HTTPS email provider/API or a Gmail Apps Script web app for email delivery, or use a hosting plan that permits SMTP.

Never commit `.env` or publish API keys. Add secrets only in Render Dashboard > your service > Environment.
