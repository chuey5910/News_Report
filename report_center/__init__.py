import os

import click
from flask import Flask

from .config import Config
from .extensions import db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (ensure models are registered before create_all)

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    from .auth import bp as auth_bp
    from .reports import bp as reports_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            target = "reports.dashboard" if current_user.is_admin else "reports.advance"
            return redirect(url_for(target))
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("full_name")
    @click.password_option()
    def create_admin(username, full_name, password):
        """Create (or promote) an approved admin user, e.g.:
        flask --app report_center create-admin admin "ผู้ดูแลระบบ"
        """
        from .models import User

        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username, full_name=full_name, role="admin", is_approved=True)
        else:
            user.full_name = full_name
            user.role = "admin"
            user.is_approved = True
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created/updated and approved.")
