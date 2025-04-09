FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# Update this to point to your actual app structure
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]