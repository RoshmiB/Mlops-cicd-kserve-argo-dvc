FROM docker.io/kserve/sklearnserver:v0.16.0

# Install xgboost directly into the KServe production virtual environment library folder
RUN pip install --no-cache-dir xgboost==2.0.0 --target=/prod_venv/lib/python3.11/site-packages
