FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV PORT=8000
EXPOSE 8000
# Use shell form so environment variables (like $PORT) are expanded at runtime
CMD ["sh", "-lc", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
