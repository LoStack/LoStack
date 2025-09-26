import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from flask_sqlalchemy import SQLAlchemy

import logging

def wait_for_db(uri, timeout=60, interval=0.5) -> None:
    """Wait for db to become available"""
    engine = create_engine(uri)
    start_time = time.time()
    
    while True:
        try:
            conn = engine.connect()
            conn.close()
            logging.info("Database is ready.")
            return
        except OperationalError:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Database not available after {timeout} seconds.")
            logging.warning(f"Database not ready yet, waiting {interval}s...")
            time.sleep(interval)

def setup_db(app) -> SQLAlchemy:
    db_name = app.config.get("DB_NAME")
    db_host = app.config.get("DB_HOST")
    db_port = app.config.get("DB_PORT")
    db_user = app.config.get("DB_USER")
    db_pass = app.config.get("DB_PASSWORD")
    # Wait for then connect to db
    redacted_connection_string = f"mysql+pymysql://{db_user}:****@{db_host}:{db_port}/{db_name}"
    logging.info("DB Config: " + redacted_connection_string)
    connection_string = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config["SQLALCHEMY_BINDS"] = {"lostack-db" : connection_string} 
    wait_for_db(app.config["SQLALCHEMY_BINDS"]["lostack-db"])
    return SQLAlchemy(app)