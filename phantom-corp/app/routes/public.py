"""
Phantom Corp — Rutas públicas
"""
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
from app.models import db, User
from app.auth import create_token, get_jwks_json

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    """Landing page corporativa de Phantom Corp."""
    return render_template('index.html')


@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Formulario y procesamiento de login."""
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password:
        flash('Please provide both username and password.', 'error')
        return render_template('login.html'), 401

    # Buscar usuario en DB
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid credentials. Access denied.', 'error')
        return render_template('login.html'), 401

    # Verificar contraseña (SHA-256 — intencionalmente débil para el reto)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user.password_hash != password_hash:
        flash('Invalid credentials. Access denied.', 'error')
        return render_template('login.html'), 401

    # Crear token JWT (JWE-wrapped JWS)
    token = create_token(user.username, user.role)

    # Redirect según rol
    if user.role == 'admin':
        resp = make_response(redirect(url_for('admin.dashboard')))
    else:
        resp = make_response(redirect(url_for('public.user_home')))

    resp.set_cookie('session_token', token, httponly=True, samesite='Lax', max_age=86400)
    return resp


@public_bp.route('/logout')
def logout():
    """Cerrar sesión."""
    resp = make_response(redirect(url_for('public.index')))
    resp.delete_cookie('session_token')
    flash('Session terminated.', 'info')
    return resp


@public_bp.route('/home')
def user_home():
    """Página home para usuarios normales (no admin)."""
    from app.auth import verify_token
    token = request.cookies.get('session_token')
    if not token:
        return redirect(url_for('public.login'))
    claims = verify_token(token)
    if not claims:
        return redirect(url_for('public.login'))
    return render_template('user_home.html', user=claims)


@public_bp.route('/.well-known/jwks.json')
def jwks_endpoint():
    """
    Endpoint JWKS — Expone la clave pública RSA.
    Esto es estándar en aplicaciones que usan JWT con RSA,
    pero es la pieza clave para explotar CVE-2026-29000.
    """
    return jsonify(get_jwks_json())


@public_bp.route('/robots.txt')
def robots_txt():
    """
    robots.txt — Contiene pistas sutiles para el jugador:
    - Revela la existencia de /.well-known/
    - Revela /admin/notes/preview
    """
    content = """# Phantom Corp — Web Crawler Policy
# Last updated: 2026-01-15

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /.well-known/
Disallow: /admin/notes/preview
Disallow: /admin/api/

# Internal: Auth tokens use JWE + JWS (RSA-OAEP-256)
# See /.well-known/jwks.json for public key distribution
"""
    return content, 200, {'Content-Type': 'text/plain'}
