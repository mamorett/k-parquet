#!/bin/bash

# Ottieni la cartella dove si trova questo script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Nome della cartella del virtual environment
VENV_DIR=".venv"

# 1. Controlla se il venv esiste, altrimenti crealo
if [ ! -d "$VENV_DIR" ]; then
    echo "--- Primo avvio rilevato: Configurazione in corso... ---"
    echo "Creazione virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    echo "Attivazione e installazione dipendenze..."
    source "$VENV_DIR/bin/activate"
    
    # Aggiorna pip per sicurezza
    pip install --upgrade pip
    
    # Installa le librerie dal requirements.txt
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "ERRORE: requirements.txt non trovato!"
        exit 1
    fi
    
    echo "--- Installazione completata! Avvio applicazione... ---"
else
    # Se esiste già, attivale solo
    source "$VENV_DIR/bin/activate"
fi

# 2. Lancia l'applicazione Python (il nome del file deve corrispondere al tuo)
python kparquet.py

# Disattiva alla chiusura (opzionale, lo script termina comunque)
deactivate