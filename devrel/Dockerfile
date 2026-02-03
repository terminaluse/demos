# syntax=docker/dockerfile:1.3
#
# RUNTIME REQUIREMENTS for bubblewrap sandboxing:
#   - When running in gVisor (GKE Sandbox / minikube with gVisor addon):
#       No special capabilities needed - gVisor handles syscall isolation
#   - When running in standard Docker/containerd:
#       docker run --cap-add=SYS_ADMIN ...
#
# bubblewrap is used instead of nsjail because nsjail requires prctl(PR_SET_SECUREBITS)
# which gVisor hasn't implemented. bubblewrap provides equivalent filesystem isolation.
#
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.4 /uv /uvx /bin/

# Install system dependencies (cached via BuildKit)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tar \
    netcat-openbsd \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --upgrade pip setuptools wheel

ENV UV_HTTP_TIMEOUT=1000

# Copy just the pyproject.toml file to optimize caching
COPY devrel/pyproject.toml /app/devrel/pyproject.toml

WORKDIR /app/devrel

# Install local SDK with observability extras, then install the agent
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "/app[observability]" && uv pip install --system .

# Copy the source code and config
COPY devrel/src /app/devrel_1/src
COPY devrel/config.yaml /app/devrel/config.yaml

# Copy skills folder for baked mount
COPY devrel/skills /app/devrel/skills

# Set environment variables
ENV PYTHONPATH=/app

# Run the agent using uvicorn
ENTRYPOINT ["uvicorn", "src.agent:server", "--host", "0.0.0.0"]
