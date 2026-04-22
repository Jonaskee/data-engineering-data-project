FROM python:3.11-slim

# Zet de werkmap in de container
WORKDIR /app

# Kopieer eerst de requirements (dit is sneller voor de Docker cache)
COPY requirements.txt .

# Installeer de benodigde packages
RUN pip install --no-cache-dir -r requirements.txt

# De rest van de code wordt erin gezet via de 'volumes' in docker-compose, 
# dus we hoeven hier verder niets te kopiëren!

CMD [ "python", "-u", "main.py" ]