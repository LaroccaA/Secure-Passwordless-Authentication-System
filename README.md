
# Secure Passwordless Authentication System

Questo progetto è un **Proof of Concept (PoC)** di un sistema di autenticazione moderno.
L'obiettivo principale è simulare un ambiente in cui le password statiche sono sostituite da protocolli crittografici dinamici (TOTP) e dove la protezione dei dati sensibili è garantita nativamente tramite cifratura.


## Obiettivi della Simulazione

Il progetto mira a dimostrare come mitigare tre delle vulnerabilità più critiche nelle web application moderne:
1.  **Eliminazione delle Password:** Rimozione dei rischi legati a password deboli.
2.  **Protezione dei Dati a Riposo:** Impedire la lettura dei dati sensibili (email e segreti 2FA) anche in caso di furto fisico del database.
3.  **Resilienza agli Attacchi:** Implementazione di difese attive contro tentativi di Brute Force.



## Scelte Progettuali e Tecnologie

Le seguenti decisioni architettoniche confermano gli obiettivi di sicurezza:

* **Autenticazione TOTP:**
    Utilizzo di `pyotp` per generare token a tempo (6 cifre, 30s). Il sistema non salva password, ma condivide un segreto crittografico (Seed) con il dispositivo dell'utente.
* **Database Cifrato:**
    Il file `database.json` è interamente cifrato con algoritmo simmetrico **Fernet (AES)**. Senza la chiave di decifratura, il file appare come una stringa casuale incomprensibile.
* **Gestione Segreti (.env):**
    La chiave di cifratura non è mai presente nel codice sorgente, ma caricata da variabili d'ambiente tramite `python-dotenv`. Questo protegge il sistema anche se il codice finisce su repository pubblici.
* **Hashing dei Codici di Recupero:**
    I codici di emergenza sono salvati solo sotto forma di **Hash sicuri**. Non è possibile risalire al codice originale partendo dal database.
* **Rate Limiting:**
    Il sistema blocca l'account dopo 5 tentativi falliti, prevenendo attacchi di forza bruta.



## Struttura del Progetto

```text
/progetto_sicurezza
│
├── app.py                  # Core dell'applicazione
├── database.json           # Database cifrato
├── .env                    # Variabili d'ambiente(file presente nel .gitignore)
├── requirements.txt        # Dipendenze Python
│
├── utility/                
│   ├── hash_function.py    # Logica di hashing per i codici di recupero
│   └── data_function.py    # Gestione lettura/scrittura cifrata del DB
│
├── brute-force.py          # Script multithread per testare la resistenza del login
└── session-hijacking.py    # Script di ricerca per testare la validità dei cookie (Approfondimento dello studio, il sistema non è protetto da questo attacco)
```

## Istruzioni per l'Avvio

### Installazione

Assicurati di avere Python installato, poi esegui:

```bash
python3 -m venv venv
source venv/bin/activate # Windows: venv\\Scripts\\activate   
pip install -r requirements.txt
```

### Configurazione Sicurezza

Crea un file `.env` nella cartella principale e inserisci la chiave di cifratura (AES):

```text
DB_SECRET_KEY=u0X_v0X8L1pY9uR5v6_z8v9B6B6n8B6v7C8D9E0F1G2=
```
### Esecuzione Server

```bash
python app.py
```

Il server sarà attivo su `http://127.0.0.1:5000`.
* Al primo avvio, registra un utente e scansiona il QR Code con un'app come **Google Authenticator**.

## Come Testare la Sicurezza
Il progetto include due script di attacchi per verificare le difese.
**Per testare il blocco Brute-Force:**
1. Mantieni il server `app.py` attivo.
2. Apri un nuovo terminale ed esegui:
```bash
python brute-force.py
```
3. Lo script lancerà attacchi paralleli. Osserva come il server risponde bloccando le richieste (Status 403) dopo il 5° tentativo fallito.

**Per verificare la cifratura:**
1. Prova ad aprire il file `database.json` con un editor di testo.
2. Noterai che il contenuto è una stringa incomprensibile (`gAAAAAB...`), confermando che i dati sono illeggibili senza l'applicazione.

In caso in cui ci sia bisogno di contattare l'assistenza oppure si voglia effettuare di nuovo la registrazione bisogna cancellare il file : **database.json**
