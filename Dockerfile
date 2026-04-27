# Use official Python image
FROM python:3.13

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Expose Django port
EXPOSE 8000

# Run migrations + start server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]