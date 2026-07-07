# ─────────────────────────────────────────────────
# Hotel GM Intelligence Agent 3.0 — Docker Setup
# LangGraph + Groq (open-weight models), SQLite memory
# ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create memory directory for the SQLite db
RUN mkdir -p memory

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true"]
