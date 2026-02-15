#!/bin/bash
# Start backend and frontend for testing

# Kill existing processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "Starting Backend..."
source venv/bin/activate
uvicorn backend.app.main:app --port 8000 &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "App running at http://localhost:5173"
echo "Press Ctrl+C to stop"

wait
