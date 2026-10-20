import pyotp
import qrcode
import io
import base64
import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import timedelta
from cryptography.fernet import Fernet
import utility.hash_function as hash
import utility.data_function as data
from dotenv import load_dotenv




app = Flask(__name__)

app.secret_key = os.urandom(24) # Genera 24 byte casuali ogni volta che il server parte

# Mitiga il furto di sessione: il cookie non è leggibile da JavaScript
# e non viene inviato nelle richieste cross-site.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)
app.permanent_session_lifetime = timedelta(minutes=5) #Durata massima della sessione

DB = "database.json"
MAX_FAILED_ATTEMPTS = 5

load_dotenv()                                                           #   In questa parte sono andato a caricare da un file .env la chiave che Fernet
env_key = os.getenv('DB_SECRET_KEY')                                    #   andrà ad utilizzare per crittografare le informazioni che vengono salvate
if not env_key:                                                         #   sul database.
    raise RuntimeError("ERRORE :'DB_SECRET_KEY' non è stata trovata")   #
STATIC_KEY = env_key.encode()                                           #
cipher_suite = Fernet(STATIC_KEY)                                       #


db = data.load_db(DB,cipher_suite)



# API dell'app

# Usiamo come primo controllo al collegamento se l'utente ha già effettuato la registrazione e quindi è
# in possesso di un autenticatore sul cellulare, in tal caso gli chiederà direttamente di entrare tramite login.
# Se invece è il primo accesso passerà alla registrazione. 
@app.route('/')
def index():                                        
    if not db["is_setup"]:                          
        return redirect(url_for('register'))        
    return redirect(url_for('login'))               
 

# La registrazione 
@app.route('/register', methods=['GET', 'POST'])
def register():
    global db
    if db["is_setup"]:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return "Email obbligatoria", 400
            
        db["user_email"] = email
        
        db["secret"] = pyotp.random_base32()    # In questo momento viene generato il segreto condiviso che verrà usato da app e server,
                                                # permettendo a entrambi di calcolare lo stesso codice a 6 cifre nello stesso momento.
        
        # Salvataggio cifrato con AES (salva solo email e secret TOTP per ora)
        data.save_db(DB,db,cipher_suite) 
        
        # Mostriamo il QRcode
        return redirect(url_for('setup'))
        
    return render_template('register_email.html')

@app.route('/setup')
def setup():
    global db
    if db["is_setup"]:
        return redirect(url_for('login'))
    
    # Generazione del Segreto
    if not db["secret"]:
        db["secret"] = pyotp.random_base32()
        data.save_db(DB,db,cipher_suite)
    
    # Creazione URI per il QR Code
    totp = pyotp.TOTP(db["secret"])
    provisioning_uri = totp.provisioning_uri(name=db["user_email"], issuer_name="EsameSicurezza")
    
    # Generazione immagine QR Code
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf)
    qr_b64 = base64.b64encode(buf.getvalue()).decode() # Creazione di unica stringa da passare all'HTML
    
    # Passiamo solo il QR Code
    return render_template('register.html', qr_code=qr_b64)

@app.route('/verify-setup', methods=['POST'])
def verify_setup():
    global db
    if db["is_setup"]:
        return redirect(url_for('login'))
    if not db.get("secret"):
        return redirect(url_for('register'))

    token = request.form.get('token')
    totp = pyotp.TOTP(db["secret"])
    
    # Validazione del primo token
    if totp.verify(token):
        db["is_setup"] = True
        
        plain_codes = [] # Questi li mostriamo all'utente ORA
        hashed_codes = [] # Questi li salviamo nel DB
        
        for _ in range(5):
            code = secrets.token_hex(4) 
            plain_codes.append(code)
            hashed_codes.append(hash.hash_code(code))
            
        db["recovery_hashes"] = hashed_codes

        data.save_db(DB,db,cipher_suite) # Ora salviamo che il setup è completato con anche i codici hash

        # Login automatico subito dopo il setup
        session['user'] = db["user_email"]
        
        # Prima di andare alla dashboard visualizza i codici.
        return render_template('show_codes.html', codes=plain_codes)
    else:
        return f"""
    <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
        <h1>Accesso non consentito</h1>
        <a href='/logout' style='color:red;'>Riprova</a>
    </div>
    """, 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    global db
    if not db["is_setup"]:
        return redirect(url_for('register'))
    

    ##################################################################################
    # Protezione Brute Force
    if db.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS:
        return render_template('locked.html'), 403
    #################################################################################

    if request.method == 'POST':
        token = request.form.get('token')
        totp = pyotp.TOTP(db["secret"])
        
        # Logica Anti-Replay
        if token == db.get("last_used_token"):
            return f"""
    <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
        <h1>Token già utilizzato aspetta un nuovo token</h1>
        <a href='/logout' style='color:red;'>Riprova</a>
    </div>
    """, 400

        # Validazione SOLO TOTP
        if totp.verify(token):
            db["failed_attempts"] = 0
            db["last_used_token"] = token
            data.save_db(DB,db,cipher_suite)
            session['user'] = db["user_email"]
            session['user_agent'] = request.headers.get('User-Agent')
            return redirect(url_for('dashboard'))
        else:
            db["failed_attempts"] = db.get("failed_attempts", 0) + 1
            data.save_db(DB,db,cipher_suite)
            return f"""
            <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
            <h1>Codice Authenticator errato. Tentativi rimasti: {MAX_FAILED_ATTEMPTS - db['failed_attempts']}</h1>
            <a href='/logout' style ='color:red;'>Riprova</a>
            </div>
            """, 401
            
    return render_template('login.html')

@app.route('/recovery', methods=['GET', 'POST'])
def recovery():
    global db
    if not db["is_setup"]:
        return redirect(url_for('register'))
    
    # Protezione Brute Force
    if db.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS:
        return render_template('locked.html'), 403

    if request.method == 'POST':
        token = request.form.get('token')
        
        # Validazione con codici di recupero
        is_valid_recovery = False
        recovery_hashes = db.get("recovery_hashes", [])
        
        for index, stored_hash in enumerate(recovery_hashes):
            if hash.verify_code(token, stored_hash): 
                is_valid_recovery = True
                # Lo cancelliamo subito perché è monouso
                del db["recovery_hashes"][index]
                break 

        if is_valid_recovery:
            db["failed_attempts"] = 0
            data.save_db(DB,db,cipher_suite)
            session['user'] = db["user_email"]
            session['user_agent'] = request.headers.get('User-Agent')
            return redirect(url_for('dashboard'))
        else:
            db["failed_attempts"] = db.get("failed_attempts", 0) + 1
            data.save_db(DB,db,cipher_suite)
            return f"""
            <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
            <h1>Codice di Sicurezza errato. Tentativi rimasti: {MAX_FAILED_ATTEMPTS - db['failed_attempts']}</h1>
            <a href='/logout' style ='color:red;'>Riprova</a>
            </div>
            """, 401
            
    return render_template('recovery.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.before_request
def make_session_permanent():
    session.permanent = True

if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug)
