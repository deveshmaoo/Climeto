#!/usr/bin/env python3
"""
AWS Elastic Beanstalk entry point
"""

from app import create_app
import os

# Create the Flask application
application = create_app()

if __name__ == '__main__':
    # For local development
    application.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 