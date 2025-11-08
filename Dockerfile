FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose MCP port
EXPOSE 3000

# Use -u flag to disable Python buffering for better logging
CMD ["python", "-u", "src/server.py"]
