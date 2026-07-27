FROM python:3.12-slim

WORKDIR /app

# Install dependencies first, using only the requirements file, so that
# changing application code later does not invalidate this layer and
# force a full reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the source. No .env file, no secrets, nothing environment-specific
# is copied into the image — see .env.example for what must be supplied
# at run time instead.
COPY app.py seed_data.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 5000

ENV DB_PATH=/data/register.db
ENV PORT=5000

CMD ["./entrypoint.sh"]
