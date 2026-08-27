# LegalClear backend — deterministic build (2026-08-27)
#
# Replaces reliance on nixpacks phase semantics. The prod PDF 500
# (libgobject bare-soname load failure) persisted across four nixpacks
# config changes because the apt layer never landed in the served image.
# Container-verified in the exact Railway base (ghcr.io/railwayapp/
# nixpacks:ubuntu-1745885067): the clean base reproduces the prod error
# verbatim; base + this apt list renders OK. A Dockerfile makes the build
# self-describing and immune to builder-config drift.
FROM ghcr.io/railwayapp/nixpacks:ubuntu-1745885067

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update -q && apt-get install -y -q \
    python3 python3-pip python3-venv \
    tesseract-ocr tesseract-ocr-eng \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libglib2.0-0t64 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2t64 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Mirror the nixpacks Python layout so the existing Railway start command
# (uvicorn from /app with /opt/venv/bin on PATH) keeps working unchanged.
COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/python -m playwright install chromium

COPY . .

ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

# Railway appends the dashboard Start Command as CMD args. Under the
# nixpacks builder that command was shell-expanded (its $PORT resolved to
# 8080); under this Dockerfile build it reached uvicorn as the literal
# string "$PORT" and killed the deploy (observed: "Invalid value for
# '--port': '$PORT' is not a valid integer"). This entrypoint guarantees
# shell expansion regardless of how Railway passes the command.
ENTRYPOINT ["/bin/bash", "-c"]
