import sqlite3
import pymysql
import os
import json
import ssl
from config import Config

def get_ssl_config():
    """Returns SSL context or configuration for TiDB Cloud / Remote MySQL."""
    if Config.MYSQL_SSL_REQUIRED or 'tidb' in Config.MYSQL_HOST.lower() or Config.MYSQL_HOST != 'localhost':
        try:
            import certifi
            return {'ca': certifi.where()}
        except Exception:
            try:
                ctx = ssl.create_default_context()
                return ctx
            except Exception:
                return {'ssl_mode': 'REQUIRED'}
    return None

def get_db_connection():
    """
    Attempts to connect to MySQL / TiDB Cloud.
    If MySQL/TiDB fails (e.g. invalid credentials or network issue), logs reason and falls back to SQLite.
    Returns (connection_object, db_type_str).
    """
    try:
        connect_args = {
            'host': Config.MYSQL_HOST,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DB,
            'port': Config.MYSQL_PORT,
            'cursorclass': pymysql.cursors.DictCursor,
            'connect_timeout': 15,
            'charset': 'utf8mb4'
        }
        ssl_ctx = get_ssl_config()
        if ssl_ctx:
            connect_args['ssl'] = ssl_ctx

        conn = pymysql.connect(**connect_args)
        return conn, 'mysql'
    except Exception as e:
        print(f"[DB Warning] Could not connect to MySQL/TiDB at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} (DB: {Config.MYSQL_DB}) -> {e}")
        # Fallback to SQLite
        os.makedirs(os.path.dirname(Config.SQLITE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Executes a SQL query handling differences between MySQL and SQLite syntax seamlessly.
    """
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Replace %s with ? for SQLite compatibility
        if db_type == 'sqlite':
            query = query.replace('%s', '?')
            query = query.replace('AUTO_INCREMENT', 'AUTOINCREMENT')
            query = query.replace('INT PRIMARY KEY AUTOINCREMENT', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            query = query.replace('INT AUTO_INCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        
        cursor.execute(query, params)
        
        result = None
        if fetchone:
            row = cursor.fetchone()
            if row:
                result = dict(row) if db_type == 'sqlite' else row
        elif fetchall:
            rows = cursor.fetchall()
            if rows:
                result = [dict(r) if db_type == 'sqlite' else r for r in rows]
            else:
                result = []
                
        if commit:
            conn.commit()
            if db_type == 'sqlite' and 'INSERT' in query.upper():
                result = cursor.lastrowid
            elif db_type == 'mysql' and 'INSERT' in query.upper():
                result = cursor.lastrowid
                
        return result
    finally:
        conn.close()

def init_db_schema():
    """
    Initializes database tables in MySQL / TiDB or SQLite.
    """
    conn, db_type = get_db_connection()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'reviewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS clinical_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_code VARCHAR(50) UNIQUE NOT NULL,
            trial_name VARCHAR(255) NOT NULL,
            phase VARCHAR(20) NOT NULL,
            target_indication VARCHAR(255) NOT NULL,
            sponsor VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS investigational_drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_code VARCHAR(50) UNIQUE NOT NULL,
            drug_name VARCHAR(100) NOT NULL,
            chemical_class VARCHAR(100),
            mechanism_of_action VARCHAR(255),
            metabolic_pathway VARCHAR(100),
            molecular_weight FLOAT,
            logP FLOAT,
            protein_binding FLOAT,
            target_half_life FLOAT,
            toxicity_alerts TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS drug_analogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investigational_drug_id INTEGER NOT NULL,
            analog_name VARCHAR(100) NOT NULL,
            similarity_score FLOAT NOT NULL,
            known_adverse_events TEXT,
            withdrawn_status BOOLEAN DEFAULT 0,
            black_box_warning BOOLEAN DEFAULT 0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volunteer_code VARCHAR(50) UNIQUE NOT NULL,
            age INTEGER NOT NULL,
            gender VARCHAR(10) NOT NULL,
            weight_kg FLOAT NOT NULL,
            height_cm FLOAT NOT NULL,
            bmi FLOAT NOT NULL,
            egfr FLOAT NOT NULL,
            alt_u_l FLOAT NOT NULL,
            ast_u_l FLOAT NOT NULL,
            bilirubin_mg_dl FLOAT NOT NULL,
            qtc_ms FLOAT NOT NULL,
            systolic_bp INTEGER NOT NULL,
            diastolic_bp INTEGER NOT NULL,
            heart_rate INTEGER NOT NULL,
            comorbidities TEXT,
            current_medications TEXT,
            previous_adverse_reactions TEXT,
            cyp2d6_genotype VARCHAR(20) DEFAULT 'Normal',
            cyp2c19_genotype VARCHAR(20) DEFAULT 'Normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS risk_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id INTEGER NOT NULL,
            volunteer_id INTEGER NOT NULL,
            investigational_drug_id INTEGER NOT NULL,
            overall_risk_score FLOAT NOT NULL,
            risk_category VARCHAR(20) NOT NULL,
            confidence_score FLOAT NOT NULL,
            confidence_flag VARCHAR(50) NOT NULL,
            pillar_a_score FLOAT NOT NULL,
            pillar_b_score FLOAT NOT NULL,
            pillar_c_score FLOAT NOT NULL,
            suggested_monitoring VARCHAR(100) NOT NULL,
            shap_json TEXT,
            pk_sim_json TEXT,
            reviewer_decision VARCHAR(50) DEFAULT 'Pending Review',
            reviewer_notes TEXT,
            reviewed_by INTEGER,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL,
            user_id INTEGER,
            action VARCHAR(100) NOT NULL,
            previous_status VARCHAR(50),
            new_status VARCHAR(50),
            comments TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]

    try:
        cursor = conn.cursor()
        for table_sql in tables:
            if db_type == 'mysql':
                table_sql = table_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'INT AUTO_INCREMENT PRIMARY KEY')
                table_sql = table_sql.replace('BOOLEAN', 'TINYINT(1)')
            cursor.execute(table_sql)
            
        conn.commit()
        print(f"[DB Init] Database initialized successfully using {db_type.upper()}.")
    finally:
        conn.close()
