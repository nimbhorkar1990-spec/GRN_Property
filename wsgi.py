"""
WSGI entry point for production servers.
Used by gunicorn, uWSGI, Render, Railway, PythonAnywhere, etc.
"""
from app import app

if __name__ == '__main__':
    app.run()

