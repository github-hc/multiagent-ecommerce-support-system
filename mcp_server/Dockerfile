FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for SSE transport
EXPOSE 8001

# Command to run FastMCP with SSE transport on host 0.0.0.0
CMD ["fastmcp", "run", "app/server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8001"]
