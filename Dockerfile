# ---------------------------------------------------------
# INDMoney Pulse Generator - Hugging Face Spaces Deployment
# ---------------------------------------------------------

FROM python:3.10-slim

# Install system dependencies 
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install Node.js (Required if your MCP server uses `npx`)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs

# Create a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python requirements
COPY --chown=user phase1_scaffold/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY --chown=user . .

# Hugging Face Spaces strictly requires apps to run on port 7860
EXPOSE 7860

# We set environment variables generally used by Flask
ENV FLASK_RUN_PORT=7860
ENV FLASK_APP=phase6_approval/approval_ui.py
ENV FLASK_RUN_HOST=0.0.0.0

# Start the Flask Approval UI
CMD ["flask", "run"]
