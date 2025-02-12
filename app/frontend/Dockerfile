FROM python:3.10-slim

EXPOSE 8090

WORKDIR /frontend

COPY . /frontend
RUN pip install --no-cache-dir -r requirements.txt

CMD ["streamlit", "run", "chat.py", "--server.port=8501", "--server.address=0.0.0.0"]