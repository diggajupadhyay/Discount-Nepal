# Discount Nepal
# ==============

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISCOUNT_NEPAL_HOST=0.0.0.0 \
    DISCOUNT_NEPAL_PORT=8000

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["discount-nepal", "--host", "0.0.0.0", "--port", "8000"]
