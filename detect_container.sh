#!/bin/bash

# Detect and export container runtime
if command -v docker &> /dev/null; then
    export CONTAINER_CMD="docker"
    export COMPOSE_CMD="docker-compose"
elif command -v podman &> /dev/null; then
    export CONTAINER_CMD="podman"
    if command -v podman-compose &> /dev/null; then
        export COMPOSE_CMD="podman-compose"
    else
        export COMPOSE_CMD="podman compose"
    fi
else
    echo "Error: Neither docker nor podman found"
    exit 1
fi

echo "Using: $CONTAINER_CMD"
echo "Compose: $COMPOSE_CMD"
