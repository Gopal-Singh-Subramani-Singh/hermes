#!/usr/bin/env bash
set -euo pipefail

echo "Starting Ollama instances for Hermes..."

# Instance 1: llama3.2:3b on default port 11434
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
PID1=$!
echo "  [1] llama3.2:3b  → port 11434 (PID $PID1)"
sleep 3

# Instance 2: phi3:mini on port 11435
OLLAMA_HOST=0.0.0.0:11435 ollama serve &
PID2=$!
echo "  [2] phi3:mini    → port 11435 (PID $PID2)"
sleep 3

# Instance 3: qwen2.5:7b on port 11436
OLLAMA_HOST=0.0.0.0:11436 ollama serve &
PID3=$!
echo "  [3] qwen2.5:7b   → port 11436 (PID $PID3)"
sleep 3

echo ""
echo "Pulling models (first time only)..."
OLLAMA_HOST=0.0.0.0:11434 ollama pull llama3.2:3b
OLLAMA_HOST=0.0.0.0:11435 ollama pull phi3:mini
OLLAMA_HOST=0.0.0.0:11436 ollama pull qwen2.5:7b-q4

echo ""
echo "All instances ready."
echo "PIDs: $PID1 $PID2 $PID3"
echo "Stop with: kill $PID1 $PID2 $PID3"
echo ""
echo "Start gateway: uvicorn gateway.main:app --reload --port 8000"

wait
