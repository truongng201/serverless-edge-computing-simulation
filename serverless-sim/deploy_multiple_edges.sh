#!/bin/bash

# Usage: ./deploy_multiple_edges.sh <num_edges> [central_url] [start_port]
# Example: ./deploy_multiple_edges.sh 4 http://100.93.2.1:8000 8001

NUM_EDGES=${1:-4}
CENTRAL_URL=${2:-http://100.93.2.1:8000}
START_PORT=${3:-8001}

echo "🚀 Deploying $NUM_EDGES edge nodes..."
echo "Central URL: $CENTRAL_URL"
echo "Starting port: $START_PORT"
echo

PIDS=()

cleanup() {
  echo
  echo "🛑 Stopping all edge nodes..."
  for pid in "${PIDS[@]}"; do
    # Kill the whole process group (using negative PID)
    kill -TERM -"$pid" 2>/dev/null
  done
  wait
  echo "✅ All edge nodes stopped."
  exit 0
}

trap cleanup SIGINT

for ((i=1; i<=NUM_EDGES; i++)); do
  NODE_ID=$(printf "edge_%03d" "$i")
  PORT=$((START_PORT + i - 1))
  echo "➡️  Starting $NODE_ID on port $PORT"
  # Start each edge in a new process group
  setsid ./deploy_edge.sh --node-id "$NODE_ID" --central-url "$CENTRAL_URL" --port "$PORT" &
  PIDS+=($!)
done

wait
echo
echo "✅ All $NUM_EDGES edge nodes finished."
