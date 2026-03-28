#!/usr/bin/env python3
"""
Phantom Corp — Inicialización de la base de datos
Crea las tablas y pobla con datos realistas para el reto CTF.
"""
import hashlib
import random
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, AccessLog, SecretNote


def init_database():
    app = create_app()

    with app.app_context():
        # Crear tablas
        db.create_all()
        print('[+] Tablas creadas')

        # ─── Usuarios ───
        # Empleado normal (credenciales que el jugador puede usar)
        employee = User(
            username='employee',
            password_hash=hashlib.sha256('corp2026!'.encode()).hexdigest(),
            role='user',
            email='employee@phantomcorp.local',
            display_name='John Employee'
        )

        # Admin con contraseña ultra-fuerte (no crackeable por fuerza bruta)
        admin = User(
            username='phantom_admin',
            password_hash=hashlib.sha256(
                'X#9kL$mN2!pQ7@rT4^vW8&yZ0_bD3fG5hJ6'.encode()
            ).hexdigest(),
            role='admin',
            email='admin@phantomcorp.local',
            display_name='System Administrator'
        )

        # Usuarios ficticios adicionales para hacer la DB más realista
        users_data = [
            ('j.martinez', 'user', 'Julia Martinez', 'j.martinez@phantomcorp.local'),
            ('r.chen', 'user', 'Robert Chen', 'r.chen@phantomcorp.local'),
            ('s.kowalski', 'user', 'Sarah Kowalski', 's.kowalski@phantomcorp.local'),
            ('m.tanaka', 'user', 'Michiko Tanaka', 'm.tanaka@phantomcorp.local'),
            ('d.okonkwo', 'user', 'David Okonkwo', 'd.okonkwo@phantomcorp.local'),
            ('a.petrov', 'user', 'Anna Petrov', 'a.petrov@phantomcorp.local'),
        ]

        extra_users = []
        for uname, role, dname, email in users_data:
            u = User(
                username=uname,
                password_hash=hashlib.sha256(f'random-pass-{uname}-2026!'.encode()).hexdigest(),
                role=role,
                email=email,
                display_name=dname
            )
            extra_users.append(u)

        db.session.add(employee)
        db.session.add(admin)
        for u in extra_users:
            db.session.add(u)
        db.session.commit()
        print(f'[+] {2 + len(extra_users)} usuarios creados')

        # ─── Access Logs ───
        actions = [
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'PAGE_VIEW:/admin/dashboard',
            'PAGE_VIEW:/admin/stats', 'PAGE_VIEW:/admin/notes',
            'API_CALL:/admin/api/stats', 'LOGOUT', 'PASSWORD_CHANGE',
            'SETTINGS_UPDATE', 'FILE_DOWNLOAD', 'REPORT_GENERATED',
            'SESSION_REFRESH', 'MFA_VERIFIED', 'ACCESS_DENIED',
        ]

        ips = [
            '10.0.1.15', '10.0.1.22', '10.0.2.7', '10.0.2.44',
            '192.168.1.100', '192.168.1.105', '172.16.0.3', '172.16.0.88',
            '10.10.10.1', '10.10.10.55',
        ]

        base_date = datetime(2026, 1, 1)
        logs = []
        for i in range(200):
            log = AccessLog(
                user_id=random.choice([1, 2, 3, 4, 5, 6, 7, 8]),
                action=random.choice(actions),
                ip_address=random.choice(ips),
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                timestamp=base_date + timedelta(
                    days=random.randint(0, 85),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            )
            logs.append(log)

        db.session.add_all(logs)
        db.session.commit()
        print(f'[+] {len(logs)} access logs creados')

        # ─── Secret Notes ───
        # Notas visibles (contenido normal)
        visible_notes = [
            SecretNote(
                title='Q1 2026 Security Audit Summary',
                content='The quarterly security audit has been completed. All systems passed compliance checks. '
                        'JWT authentication system has been reviewed and approved. RSA-OAEP-256 encryption '
                        'provides adequate confidentiality for session tokens. Signature verification with '
                        'RS256 ensures token integrity.',
                author='phantom_admin',
                is_hidden=False,
                created_at=datetime(2026, 1, 15)
            ),
            SecretNote(
                title='New Employee Onboarding Checklist',
                content='1. Create corporate email account\n'
                        '2. Generate employee credentials\n'
                        '3. Assign role-based access (default: user)\n'
                        '4. Provide VPN configuration\n'
                        '5. Complete security awareness training\n'
                        '6. Review acceptable use policy',
                author='phantom_admin',
                is_hidden=False,
                created_at=datetime(2026, 2, 1)
            ),
            SecretNote(
                title='Infrastructure Migration Status',
                content='Migration to new cloud infrastructure is 85% complete. Database migration finished '
                        'on 2026-02-20. Authentication service migration pending. The statistics API endpoint '
                        'is still running on legacy code and will be updated in Q2.',
                author='j.martinez',
                is_hidden=False,
                created_at=datetime(2026, 2, 22)
            ),
            SecretNote(
                title='Incident Response Playbook v3.1',
                content='Updated IR playbook with new procedures for JWT token compromise scenarios. '
                        'If a token is suspected to be forged, immediately rotate RSA keypair and '
                        'invalidate all active sessions. Contact CISO for further instructions.',
                author='phantom_admin',
                is_hidden=False,
                created_at=datetime(2026, 3, 1)
            ),
        ]

        # ╔══════════════════════════════════════════════════════════════╗
        # ║  NOTA OCULTA — La pista clave para el Stage 3 del CTF     ║
        # ║  Solo accesible mediante SQLi (Stage 2)                    ║
        # ╚══════════════════════════════════════════════════════════════╝
        hidden_note = SecretNote(
            title='INTERNAL: Markdown Renderer Configuration',
            content='CONFIDENTIAL — Internal Development Notes\n\n'
                    'The notes preview endpoint at /admin/notes/preview supports remote and local '
                    'content fetching via the source_url parameter.\n\n'
                    'Supported URI schemes:\n'
                    '- http:// and https:// for remote resources\n'
                    '- file:// for local filesystem access (used for internal template inclusion)\n\n'
                    'SECURITY NOTE: The file:// handler has no path restrictions. This is intentional '
                    'for internal use but must NOT be exposed to untrusted users.\n\n'
                    'Critical system files:\n'
                    '- Application config: /opt/phantom/flag.txt\n'
                    '- Server keys: /workspace/phantom-corp/keys/\n\n'
                    'TODO: Add path whitelist before production deployment.',
            author='phantom_admin',
            is_hidden=True,
            created_at=datetime(2026, 3, 10)
        )

        for note in visible_notes:
            db.session.add(note)
        db.session.add(hidden_note)
        db.session.commit()
        print(f'[+] {len(visible_notes)} notas visibles + 1 nota oculta creadas')

        print('\n[✓] Base de datos inicializada correctamente')
        print(f'    DB: {app.config["SQLALCHEMY_DATABASE_URI"]}')
        print(f'    Usuarios: employee/corp2026! (user), phantom_admin (admin — password NO crackeable)')
        print(f'    Nota oculta contiene pista sobre file:// en /admin/notes/preview')


if __name__ == '__main__':
    init_database()
