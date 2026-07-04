#!/usr/bin/env bash
echo "=== Hermes Setup Verification ==="

# Redis
echo -n "[Redis] "
if redis-cli -p 6379 ping 2>/dev/null | grep -q PONG; then
  echo "✓ Running on :6379"
else
  echo "✗ Not running — start with: docker run -d -p 6379:6379 redis:7-alpine"
fi

# Ollama instances
for port in 11434 11435 11436; do
  echo -n "[Ollama :$port] "
  if curl -sf http://localhost:$port/api/ps > /dev/null 2>&1; then
    echo "✓ Running"
  else
    echo "✗ Not running"
  fi
done

# Hermes gateway
echo -n "[Hermes :8000] "
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "✓ Running"
else
  echo "✗ Not running — start with: uvicorn gateway.main:app --reload"
fi

echo ""
echo "Endpoints when running:"
echo "  Dashboard : http://localhost:8000/ui"
echo "  API docs  : http://localhost:8000/docs"
echo "  Metrics   : http://localhost:8000/metrics"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana   : http://localhost:3000 (admin/hermes)"
