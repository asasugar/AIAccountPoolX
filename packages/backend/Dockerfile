FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/packages/backend

COPY packages/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/backend ./

EXPOSE 1455

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "1455"]
