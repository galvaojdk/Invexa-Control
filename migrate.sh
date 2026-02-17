#!/bin/bash
echo "Iniciando migração do banco de dados..."
python migrations/migrate_postgres.py
echo "Garantindo que tabelas existam..."
python init_db.py
echo "Migração concluída."
