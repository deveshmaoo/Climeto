# HRMSV3_optimized/run.py
from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=True)