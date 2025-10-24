# Multi-stage build following security best practices
FROM python:3.13-slim AS build

WORKDIR /src

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./

# Install uv and create virtual environment (production only)
RUN pip install uv && \
    uv sync --frozen --no-dev

# Pre-download embedding model to cache
RUN .venv/bin/python -c "from transformers import AutoTokenizer, AutoModel; AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2'); AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')"

# Copy source and docs
COPY src/ src/
COPY docs/ docs/

# Build embeddings database
ENV PYTHONPATH=/src/src
RUN .venv/bin/python -m sdlc_mcp.build_index

# Runtime stage - minimal image
FROM python:3.13-slim AS runtime

# Create non-root user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Copy only runtime artifacts with correct ownership
COPY --from=build --chown=appuser:appgroup /src/.venv /app/.venv
COPY --from=build --chown=appuser:appgroup /src/src /app/src
COPY --from=build --chown=appuser:appgroup /src/sdlc_docs.db /app/sdlc_docs.db
COPY --from=build --chown=appuser:appgroup /root/.cache/huggingface /home/appuser/.cache/huggingface

# Switch to non-root user
USER appuser

# Environment setup
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run MCP server
CMD ["python", "-m", "sdlc_mcp.server"]
