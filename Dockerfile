FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .

RUN python -m pip install --upgrade pip
RUN pip install uv

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
