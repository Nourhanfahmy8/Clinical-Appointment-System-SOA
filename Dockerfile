# syntax=docker/dockerfile:1
# One image for all five Flask services.
# docker-compose passes SERVICE_DIR, e.g. --build-arg SERVICE_DIR=doctor
FROM python:3.12-slim

ARG SERVICE_DIR
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# pip's download cache is kept between builds, so the five services do not
# each re-download the same wheels.
COPY services/${SERVICE_DIR}/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 -r requirements.txt

COPY services/${SERVICE_DIR}/ ./

CMD ["python", "app.py"]
