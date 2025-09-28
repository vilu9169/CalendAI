from itsdangerous import URLSafeTimedSerializer
import os
import configparser
from dotenv import load_dotenv

load_dotenv()
def generate_token(username):
    secret = os.getenv("TOKEN_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "TOKEN_SECRET_KEY is not set. Set it in your environment or .env file."
        )
    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps({"username": username})

def validate_token(token):
    serializer = URLSafeTimedSerializer(os.getenv("TOKEN_SECRET_KEY"))
    try:
        username = serializer.loads(token, max_age=3600 * 24 * 364)  # Token valid for 7 days
        return username
    except Exception as e:
        print(f"Token validation failed: {e}")
        return None
    
def save_token_to_file(token):
        config = configparser.ConfigParser()
        config['Token'] = {
            'token': token,
        }
        with open('token.ini', 'w') as configfile:
            config.write(configfile)

def load_token_from_file():
    config = configparser.ConfigParser()
    try:
        config.read('token.ini')
        if 'Token' in config:
            return config['Token']['token']
    except Exception as e:
        print(f"Error loading token: {e}")
