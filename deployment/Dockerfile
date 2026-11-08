FROM gcc:14-bookworm AS kernel-build
COPY kernel /src/kernel
RUN g++ -std=c++17 -Wall -Wextra -Werror -static-libstdc++ -static-libgcc /src/kernel/main.cpp /src/kernel/payment_kernel.cpp -o /payment_kernel
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY web/requirements.txt web/requirements-postgres.txt /app/web/
RUN pip install --no-cache-dir -r web/requirements-postgres.txt \
    && useradd --uid 10001 --create-home app
COPY web /app/web
COPY tools /app/tools
COPY payment_simulator /app/payment_simulator
COPY --from=kernel-build /payment_kernel /usr/local/bin/payment_kernel
RUN mkdir -p /logs /event-index /payment-state /app/web/runtime \
    && GROCERY_SECRET_KEY=build-only-static-assets python web/manage.py collectstatic --noinput \
    && chown -R app:app /app /logs /event-index /payment-state
USER 10001:10001
WORKDIR /app/web
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "--threads=4", "config.wsgi:application"]
