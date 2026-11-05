FROM python:3.12.9-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml .
COPY src src
RUN pip install --no-deps .
COPY dashboard dashboard
COPY tests tests
COPY schemas schemas
COPY sql sql
COPY scripts scripts
CMD ["python", "-m", "industrialdata.run"]
