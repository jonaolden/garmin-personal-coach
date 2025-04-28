# Use a Python base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . /app

# Install dependencies using Poetry
# Install Poetry first
RUN pip install poetry

# Configure Poetry not to create a virtual environment inside the container
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --no-root

# Expose any necessary ports (if applicable, e.g., for a web server)
# EXPOSE 8000

# Command to run the Prefect agent or flows
CMD ["prefect", "agent", "start", "--pool", "default-agent-pool"]

# Create necessary directories
RUN mkdir -p /data /app/plans

# Set environment variables (example)
# ENV DATA_PATH="/data/garmin.duckdb"
