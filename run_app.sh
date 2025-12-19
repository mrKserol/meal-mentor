#!/bin/bash

# Start Streamlit app
echo "Starting Streamlit application..."
streamlit run ui.py &

# Wait a few seconds to ensure Streamlit app has started
sleep 3

# Start FastAPI service using uvicorn
echo "Starting FastAPI service..."
uvicorn service:app &

wait