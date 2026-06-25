#!/bin/bash

pkill -f "uvicorn webapp:app"

nohup .venv/bin/uvicorn webapp:app \
  --host 0.0.0.0 \
  --port 8000 \
  > log.txt 2>&1 &