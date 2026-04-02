FROM node:22.0.0-slim AS builder

WORKDIR /opt/frontend
COPY frontend/package.json package.json
COPY frontend/package-lock.json package-lock.json
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM python:3.11.8-bullseye
WORKDIR /opt/web

COPY requirements.txt .
RUN pip install -r requirements.txt && \
	playwright install chromium && \
	playwright install-deps && \
	rm -rf /var/lib/apt/lists/*

COPY *.py template.jinja2 ./
COPY --from=builder ./opt/frontend/dist static

CMD python init.py && python main.py