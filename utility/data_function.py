import json
import os 

def save_db(DB,data,cipher_suite):
    #Dizionario -> Stringa JSON -> Bytes
    json_bytes = json.dumps(data).encode('utf-8')
    
    # Bytes in chiaro -> Bytes cifrati
    encrypted_data = cipher_suite.encrypt(json_bytes)
    
    with open(DB, 'wb') as f:
        f.write(encrypted_data)

def load_db(DB,cipher_suite):
    if os.path.exists(DB):
        try:
            with open(DB, 'rb') as f:
                encrypted_data = f.read()
            
            #Bytes cifrati -> Bytes in chiaro
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            
            #Bytes -> Dizionario
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            print(f"Errore decifratura (chiave errata o file corrotto): {e}")
            
    return {
        "user_email": None, 
        "secret": None, 
        "is_setup": False,
        "failed_attempts": 0,      
        "last_used_token": None    
    }
