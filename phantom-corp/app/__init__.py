"""
Phantom Corp — Application Factory
"""
from flask import Flask, render_template
from app.config import Config, ensure_rsa_keys
from app.models import db


def create_app(config_class=Config):
    """Crea y configura la aplicación Flask."""
    ensure_rsa_keys()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar base de datos
    db.init_app(app)

    # Registrar blueprints
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # Contexto para templates
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Phantom Corp',
            'app_version': '3.2.1',
            'year': 2026
        }

    return app
