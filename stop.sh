#!/bin/bash
# Script para detener servidor gRPC y la app Flask

echo "Deteniendo servidor gRPC y aplicación Flask..."

pkill -f "python3 Comunication.py"
pkill -f "flask run"