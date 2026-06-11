FROM python:3.12-slim

WORKDIR /app

COPY pbix_diff/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pbix_diff/ ./pbix_diff/

ENTRYPOINT ["python", "pbix_diff/run.py"]