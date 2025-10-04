#!/bin/bash
# Script para iniciar el servidor gRPC y la app Flask

echo "Iniciando servidor gRPC..."
python3 Comunication.py &

echo "Iniciando aplicación Flask en http://localhost:8080 ..."
export FLASK_APP=pybotnet.py
flask run --host=0.0.0.0 --port=8080 &