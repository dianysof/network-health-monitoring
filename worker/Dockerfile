FROM python:3.12-slim

WORKDIR /app

# requirements.txt debe estar dentro de la carpeta worker
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# El archivo worker.py también está en la carpeta worker
COPY worker.py .

# Make Python output unbuffered so print() shows immediately
ENV PYTHONUNBUFFERED=1

CMD ["python", "worker.py"]
