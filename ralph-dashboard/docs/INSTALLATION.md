# Ralph Dashboard - Guida all'Installazione

## Prerequisiti

- **Python 3.10+** (Ubuntu 24.04 include Python 3.12)
- **python3-venv** (per creare virtual environment)
- **Ralph-TUI** installato e configurato (per le funzionalit complete)
- **Ollama** con un modello Qwen scaricato (per l'esecuzione degli agenti AI)

## Installazione Rapida (Ubuntu 24.04)

### Passo 1: Clona il repository

```bash
git clone https://github.com/Mavqo/Projects.git
cd Projects/ralph-dashboard
```

Se hai gi clonato il repo (ad esempio in `~/Documenti/ralph-dashboard`):

```bash
# Vai direttamente nella cartella del progetto
# ATTENZIONE: NON fare "cd ralph-dashboard" se sei gi dentro la cartella!
cd ~/Documenti/ralph-dashboard
```

### Passo 2: Installa python3-venv (se non presente)

```bash
sudo apt install python3-venv
```

### Passo 3: Installazione automatica

```bash
chmod +x setup.sh
./setup.sh
```

Lo script `setup.sh` fa tutto automaticamente:
- Crea un virtual environment in `.venv/`
- Installa tutte le dipendenze
- Installa GPUtil se hai una GPU NVIDIA

### Passo 4: Avvia il dashboard

```bash
# Opzione A: Script rapido (consigliato)
./run.sh --projects-dir ~/Projects

# Opzione B: Manuale
source .venv/bin/activate
ralph-dashboard --projects-dir ~/Projects
```

### Passo 5: Apri il browser

Vai su: **http://127.0.0.1:8420**

## Installazione Manuale (passo per passo)

Se preferisci fare tutto manualmente senza gli script:

```bash
# 1. Vai nella cartella del progetto
cd ~/percorso/verso/ralph-dashboard

# 2. Crea virtual environment (OBBLIGATORIO su Ubuntu 24.04)
python3 -m venv .venv

# 3. Attiva il virtual environment
source .venv/bin/activate

# 4. Installa il pacchetto
pip install -e .

# 5. (Opzionale) Supporto GPU NVIDIA
pip install GPUtil

# 6. Avvia
ralph-dashboard --projects-dir ~/Projects
```

**IMPORTANTE:** Ogni volta che apri un nuovo terminale, devi riattivare il venv:
```bash
cd ~/percorso/verso/ralph-dashboard
source .venv/bin/activate
ralph-dashboard --projects-dir ~/Projects
```

Oppure usa semplicemente `./run.sh` che attiva il venv automaticamente.

## Configurazione

### Setup Iniziale

Al primo avvio, Ralph Dashboard crea la configurazione in `~/.ralph-dashboard/config.json`:

```json
{
  "ralph_tui_command": "ralph-tui",
  "projects_dir": "~/Projects",
  "refresh_interval_ms": 1000,
  "theme": "dark",
  "log_max_lines": 10000,
  "host": "127.0.0.1",
  "port": 8420,
  "alert_cpu_threshold": 90.0,
  "alert_memory_threshold": 85.0,
  "alert_gpu_threshold": 95.0,
  "alert_disk_threshold": 90.0
}
```

### Connessione a Ralph-TUI

1. Verifica che `ralph-tui` sia nel PATH:
   ```bash
   which ralph-tui
   ralph-tui --help
   ```

2. Imposta `projects_dir` sulla cartella dei tuoi progetti Ralph-TUI:
   ```bash
   ralph-dashboard --projects-dir ~/Projects
   ```

3. Ogni progetto deve avere una cartella `.ralph-tui/` per essere rilevato.

## Avvio

```bash
# Con lo script rapido (consigliato)
./run.sh --projects-dir ~/Projects

# Avvio manuale
source .venv/bin/activate
ralph-dashboard

# Con opzioni personalizzate
ralph-dashboard --host 0.0.0.0 --port 8420 --projects-dir ~/Projects

# Modalit sviluppo (auto-reload)
ralph-dashboard --reload --log-level debug
```

Apri il browser su: **http://127.0.0.1:8420**

## Verifica Installazione

```bash
source .venv/bin/activate

# Test suite
python -m pytest tests/ -v

# Controlla metriche di sistema
curl http://127.0.0.1:8420/api/system/metrics | python3 -m json.tool

# Controlla progetti rilevati
curl http://127.0.0.1:8420/api/projects | python3 -m json.tool
```

## Risoluzione Problemi

### Errore: `externally-managed-environment` (PEP 668)

Ubuntu 24.04 non permette `pip install` globale. **Devi usare un virtual environment.**

```bash
# Soluzione: usa sempre il venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**NON usare** `--break-system-packages` - rischi di rompere il sistema.

### Errore: `cd ralph-dashboard: File o directory non esistente`

Sei probabilmente gi dentro la cartella del progetto. Verifica:
```bash
# Controlla dove sei
pwd
ls

# Se vedi setup.sh, pyproject.toml, ralph_dashboard/ -> sei gi nel posto giusto!
# NON fare cd ralph-dashboard di nuovo
```

### Errore: `ralph-dashboard: comando non trovato`

Il virtual environment non  attivo:
```bash
source .venv/bin/activate
ralph-dashboard --projects-dir ~/Projects

# Oppure usa lo script che attiva il venv automaticamente:
./run.sh --projects-dir ~/Projects
```

### Errore: `No module named venv`

```bash
sudo apt install python3-venv
```

### Dashboard non si avvia

- **Porta in uso**: Prova `--port 8421`
- **Modulo non trovato**: Verifica che il venv sia attivo (`which python` deve mostrare `.venv/bin/python`)
- **Versione Python**: Verifica `python3 --version` (serve 3.10+)

### Nessun progetto visibile

- Verifica che `projects_dir` punti alla cartella corretta
- Ogni progetto deve avere una sotto-cartella `.ralph-tui/`
- Controlla i permessi dei file

### ralph-tui non trovato

- La dashboard funziona anche senza ralph-tui per monitoraggio e gestione task
- Le funzioni Launch/Run richiedono ralph-tui installato nel PATH
- Installa ralph-tui: `bun install -g ralph-tui`

### GPU mostra N/A

```bash
source .venv/bin/activate
pip install GPUtil
```
Verifica che i driver NVIDIA siano installati: `nvidia-smi`

### Disconnessioni WebSocket

- Controlla firewall/proxy che possano bloccare le connessioni WebSocket
- Prova ad accedere direttamente (senza reverse proxy)
- Controlla la console del browser per messaggi di errore
