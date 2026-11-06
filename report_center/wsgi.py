"""WSGI entry point for production hosts (PythonAnywhere, Gunicorn, etc.).

PythonAnywhere: point the WSGI config file's `application` at this, e.g.
    from report_center.wsgi import application
"""

from report_center import create_app

application = create_app()
