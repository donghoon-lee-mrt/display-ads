# Multi-stage build for optimized image size
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies including ffmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs outputs media/samples media/templates media/archive data tmp tests

# Expose port 3000 (as per user requirement)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/_stcore/health || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=3000
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Kill any existing process on port 3000 and run Streamlit
CMD sh -c 'lsof -ti:3000 | xargs kill -9 2>/dev/null || true && \
    streamlit run app.py \
    --server.port=3000 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false'
