# HRMSV3_optimized/app/utils/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from flask import has_request_context, request

class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            record.method = request.method
            record.path = request.path
        else:
            record.url = None
            record.remote_addr = None
            record.method = None
            record.path = None
        return super().format(record)

def setup_logger(app):
    """Configure application logging."""
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    # File handler for errors
    error_file_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10240,
        backupCount=10
    )
    error_file_handler.setFormatter(RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
        '%(levelname)s in %(module)s: %(message)s'
    ))
    error_file_handler.setLevel(logging.ERROR)
    
    # File handler for info
    info_file_handler = RotatingFileHandler(
        'logs/info.log',
        maxBytes=10240,
        backupCount=10
    )
    info_file_handler.setFormatter(RequestFormatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    info_file_handler.setLevel(logging.INFO)
    
    # Configure app logger
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(error_file_handler)
    app.logger.addHandler(info_file_handler)
    
    app.logger.info('Application startup')