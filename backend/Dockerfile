FROM python:3.12-slim

WORKDIR /app

# Copy requirements (el archivo está en la raíz del contexto ./backend)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code (la carpeta app está dentro de ./backend)
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
