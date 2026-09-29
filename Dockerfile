FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY packages ./packages
COPY apps/api ./apps/api
RUN pip install --upgrade pip && pip install -c requirements.lock . && useradd --create-home --uid 10001 consignai && mkdir -p /app/var && chown consignai:consignai /app/var
USER consignai
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
