import hashlib
import secrets

#Crea un hash sicuro SHA-256 con un Salt.
def hash_code(code):
    # Generiamo un salt casuale di 16 byte
    salt = secrets.token_hex(16)
    # Uniamo salt e codice
    salted_code = salt + code
    # Facciamo l'hash
    hash_obj = hashlib.sha256(salted_code.encode())
    # Salviamo sia il salt che l'hash nel formato: salt$hash.
    return f"{salt}${hash_obj.hexdigest()}"

#Verifica se il codice fornito corrisponde all'hash salvato.
def verify_code(provided_code, stored_hash):
    try:
        salt, expected_hash = stored_hash.split('$')
        #Rifacciamo l'hash con lo stesso salt
        salted_code = salt + provided_code
        calculated_hash = hashlib.sha256(salted_code.encode()).hexdigest()
        #Confronto
        return secrets.compare_digest(calculated_hash, expected_hash)
    except ValueError:
        return False