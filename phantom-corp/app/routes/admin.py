"""
Phantom Corp — Rutas del panel de administración

Incluye:
- Dashboard con métricas
- Estadísticas con endpoint vulnerable a SQLi (CVE-2026-30881)
- Editor de notas con preview markdown vulnerable a SSRF/LFI (CVE-2026-23850)
"""
import re
import sqlite3
import requests as http_requests
from flask import Blueprint, render_template, request, jsonify, g, current_app
from app.auth import require_admin
from app.models import db, User, AccessLog, SecretNote

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@require_admin
def dashboard():
    """Dashboard principal del admin."""
    total_users = User.query.count()
    total_logs = AccessLog.query.count()
    total_notes = SecretNote.query.filter_by(is_hidden=False).count()
    recent_logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_logs=total_logs,
                           total_notes=total_notes,
                           recent_logs=recent_logs,
                           user=g.current_user)


@admin_bp.route('/stats')
@require_admin
def stats_page():
    """Página de estadísticas con filtros de fecha."""
    return render_template('admin/stats.html', user=g.current_user)


@admin_bp.route('/api/stats')
@require_admin
def get_stats():
    """
    API de estadísticas — VULNERABLE a SQL Injection (CVE-2026-30881)

    Replica el patrón exacto de Chamilo LMS:
    1. Recibe date_start y date_end
    2. Aplica "sanitización" con escape de comillas
    3. Luego str_replace() DESHACE el escape (el bug real)
    4. Inyecta directamente en query SQL sin parámetros
    """
    date_start = request.args.get('date_start', '2026-01-01')
    date_end = request.args.get('date_end', '2026-12-31')

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  CVE-2026-30881: Sanitización rota de Chamilo LMS          ║
    # ║  Paso 1: Escapa comillas simples (añade backslash)         ║
    # ║  Paso 2: str_replace DESHACE el escape → SQLi              ║
    # ╚══════════════════════════════════════════════════════════════╝

    # Paso 1: "Escape" — añade backslash antes de comillas simples
    date_start = date_start.replace("'", "\\'")
    date_end = date_end.replace("'", "\\'")

    # Paso 2: EL BUG — deshace el escape inmediatamente
    date_start = date_start.replace("\\'", "'")
    date_end = date_end.replace("\\'", "'")

    # Query SQL directa con los valores "sanitizados" (inyectables)
    try:
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = f"""
            SELECT COUNT(*) as total, action
            FROM access_logs
            WHERE timestamp >= '{date_start}'
            AND timestamp <= '{date_end}'
            GROUP BY action
            ORDER BY total DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        conn.close()

        return jsonify({
            'status': 'success',
            'date_range': {'start': date_start, 'end': date_end},
            'data': results,
            'total_entries': sum(r['total'] for r in results) if results else 0
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Query execution failed',
            'debug': str(e) if current_app.debug else 'Internal error'
        }), 500


@admin_bp.route('/notes')
@require_admin
def notes_list():
    """Lista de notas (solo las visibles, las ocultas no se muestran)."""
    notes = SecretNote.query.filter_by(is_hidden=False).order_by(SecretNote.created_at.desc()).all()
    return render_template('admin/notes.html', notes=notes, user=g.current_user)


@admin_bp.route('/notes/preview', methods=['GET', 'POST'])
@require_admin
def notes_preview():
    """
    Preview de notas markdown — VULNERABLE a SSRF/LFI (CVE-2026-23850)

    Acepta:
    - content: texto markdown para renderizar directamente
    - source_url: URL de donde obtener el contenido (soporta http://, https://, file://)

    El bug: no restringe el esquema file:// → lectura arbitraria de archivos del servidor.
    Replica el comportamiento de SiYuan (CVE-2026-23850) donde el renderizador de markdown
    permite acceso sin restricciones a rutas locales del filesystem.
    """
    if request.method == 'GET':
        return render_template('admin/notes_preview.html', user=g.current_user)

    content = request.form.get('content', '')
    source_url = request.form.get('source_url', '')
    rendered = ''
    error = None
    raw_content = content

    if source_url:
        # ╔══════════════════════════════════════════════════════════════╗
        # ║  CVE-2026-23850: SSRF/LFI via markdown source URL          ║
        # ║  No restringe file:// → lectura arbitraria de archivos     ║
        # ╚══════════════════════════════════════════════════════════════╝
        try:
            if source_url.startswith('file://'):
                # LFI: lectura directa de archivos locales
                file_path = source_url[7:]  # Elimina file://
                with open(file_path, 'r') as f:
                    raw_content = f.read()
            elif source_url.startswith(('http://', 'https://')):
                # SSRF: fetch remoto
                resp = http_requests.get(source_url, timeout=5)
                raw_content = resp.text
            else:
                error = 'Invalid URL scheme. Supported: http://, https://, file://'
        except FileNotFoundError:
            error = f'Source not found: {source_url}'
        except Exception as e:
            error = f'Failed to fetch source: {str(e)}'

    if not error and raw_content:
        rendered = _render_markdown(raw_content)

    return render_template('admin/notes_preview.html',
                           user=g.current_user,
                           rendered=rendered,
                           raw_content=raw_content,
                           error=error)


def _render_markdown(text):
    """
    Renderizador de markdown simple.
    Convierte patrones básicos de markdown a HTML.
    """
    import html as html_module

    # Escapar HTML primero (seguridad... parcial)
    text = html_module.escape(text)

    # Headers
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Bold y italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Code blocks
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # Line breaks
    text = text.replace('\n\n', '</p><p>')
    text = text.replace('\n', '<br>')
    text = f'<p>{text}</p>'

    return text
