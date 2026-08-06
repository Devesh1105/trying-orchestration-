#!/usr/bin/env bash
# Pull required Ollama models for local LLM inference
set -euo pipefail

echo "Pulling LLaVA (vision-language tagger)…"
ollama pull llava:13b

echo "Pulling Llama 3 8B (scene director)…"
ollama pull llama3:8b

echo "All Ollama models ready."
