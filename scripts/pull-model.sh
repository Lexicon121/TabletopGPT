#!/usr/bin/env sh
set -eu

MODEL="${1:-qwen3:8b}"
docker exec -it tabletop-gpt-ollama ollama pull "$MODEL"
