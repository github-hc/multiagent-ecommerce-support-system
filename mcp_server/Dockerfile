FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for SSE transport
EXPOSE 8001

# Command to run standard FastAPI / ASGI app
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8001"]
