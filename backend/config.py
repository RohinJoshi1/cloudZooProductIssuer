import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ISSUER_ID = os.getenv('ISSUER_ID')
    ISSUER_SECRET = os.getenv('ISSUER_SECRET')
    BASE_URL = os.getenv('BASE_URL', 'https://cloudzoo.rhino3d.com/v1')
    PORT = int(os.getenv('PORT', 3001))
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')


