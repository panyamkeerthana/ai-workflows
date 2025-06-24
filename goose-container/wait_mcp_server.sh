#!/bin/bash
set -e

host="mcp-atlassian"
port="9000"
timeout=60
count=0

echo "Waiting for MCP server at $host:$port..."

while ! curl -f "http://$host:$port/healthz" >/dev/null 2>&1; do
  if [ $count -ge $timeout ]; then
    echo "Timeout waiting for MCP server"
    exit 1
  fi
  echo "MCP server is unavailable - waiting... ($count/$timeout)"
  sleep 2
  count=$((count + 2))
done

sleep 2 # give it some more time

echo "MCP server is ready!"
