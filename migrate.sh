#!/bin/bash
echo "Iniciando migração do banco de dados..."
python migrations/migrate_postgres.py
echo "Migração concluída."
