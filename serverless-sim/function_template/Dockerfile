# Start from a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy function code
COPY handler.py .

# Set environment variables
ENV FUNCTION_ID="my_function"
ENV EXECUTION_TIME="2.0"

# Command to run the function
CMD ["python", "-c", "import handler; handler.handler({}, {})"]