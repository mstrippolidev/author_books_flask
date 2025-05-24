# Stage 1: Build Dependencies
FROM python:3.12-slim as builder

# Environment variables to optimize Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /dependencies

# Copy dependency file(s) first to leverage Docker cache # Should be one folder behind i think
COPY ./requirements.txt .

# Install dependencies into an isolated directory
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/dependencies -r requirements.txt

# Stage 2: Production Image
FROM python:3.12-slim

# Again, set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /dependencies /usr/local

# Copy the rest of your application code
COPY ./ .

# Copy the entrypoint script and ensure it's executable inside our working directory
RUN chmod +x /app/entrypoint.sh

# Expose the port your application will run on (e.g., 8000)
EXPOSE 8000

# Use an entrypoint script to run migrations and start your app
ENTRYPOINT ["/app/entrypoint.sh"]