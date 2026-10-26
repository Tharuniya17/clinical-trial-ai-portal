import os
from urllib.parse import urlparse

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clinical-trial-risk-screening-secret-key-2026')
    
    # TiDB Cloud MySQL Database URL
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'mysql://KYnTXyVT1wwZNWG.root:DjAptK9JM4ITuOVR@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/clinical_trial_risk_db'
    )
    
    # Parse URL
    _parsed_url = urlparse(DATABASE_URL)
    
    MYSQL_HOST = _parsed_url.hostname or os.environ.get('MYSQL_HOST', 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com')
    MYSQL_USER = _parsed_url.username or os.environ.get('MYSQL_USER', 'KYnTXyVT1wwZNWG.root')
    MYSQL_PASSWORD = _parsed_url.password or os.environ.get('MYSQL_PASSWORD', 'DjAptK9JM4ITuOVR')
    MYSQL_DB = _parsed_url.path.lstrip('/') or os.environ.get('MYSQL_DB', 'clinical_trial_risk_db')
    MYSQL_PORT = _parsed_url.port or int(os.environ.get('MYSQL_PORT', 4000))
    
    # SSL required for TiDB Cloud
    MYSQL_SSL_REQUIRED = os.environ.get('MYSQL_SSL_REQUIRED', 'true').lower() in ('1', 'true', 'yes')
    
    # SQLite Fallback DB Path
    SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'clinical_risk.db')
    
    # Default Fusion Weights for Risk Calculation
    WEIGHT_PILLAR_A = 0.40  # Physiology / Eligibility Risk
    WEIGHT_PILLAR_B = 0.35  # Drug Class Similarity Risk
    WEIGHT_PILLAR_C = 0.25  # Digital Twin PK Simulation Risk
    
    # Risk Thresholds
    LOW_RISK_THRESHOLD = 0.35
    MEDIUM_RISK_THRESHOLD = 0.65
    
    # Confidence Warning Threshold
    LOW_CONFIDENCE_THRESHOLD = 0.60
