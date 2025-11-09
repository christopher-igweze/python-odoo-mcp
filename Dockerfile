FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose MCP port
EXPOSE 3000

# Use uvicorn directly - handles relative imports properly
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "3000"]
