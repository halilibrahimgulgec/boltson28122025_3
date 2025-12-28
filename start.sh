#!/bin/bash
# Railway startup script

echo "🚀 Starting Kargo Takip application..."
echo "PORT: $PORT"
echo "Python version: $(python --version)"

# Start gunicorn
exec gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --log-level info
