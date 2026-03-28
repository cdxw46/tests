"""
Phantom Corp — Configuración de la aplicación
"""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_DIR = BASE_DIR / 'keys'
INSTANCE_DIR = BASE_DIR / 'instance'


def ensure_rsa_keys():
    """Genera par de claves RSA 2048-bit si no existen."""
    KEYS_DIR.mkdir(exist_ok=True)
    priv_path = KEYS_DIR / 'private.pem'
    pub_path = KEYS_DIR / 'public.pem'

    if priv_path.exists() and pub_path.exists():
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Guardar clave privada (sin cifrado — es un reto CTF)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    priv_path.write_bytes(priv_pem)

    # Guardar clave pública
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pub_path.write_bytes(pub_pem)


def load_private_key():
    """Carga la clave privada RSA desde disco."""
    priv_path = KEYS_DIR / 'private.pem'
    return serialization.load_pem_private_key(
        priv_path.read_bytes(),
        password=None,
        backend=default_backend()
    )


def load_public_key():
    """Carga la clave pública RSA desde disco."""
    pub_path = KEYS_DIR / 'public.pem'
    return serialization.load_pem_public_key(
        pub_path.read_bytes(),
        backend=default_backend()
    )


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ph4nt0m-c0rp-s3cr3t-k3y-2026-x9f2')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{INSTANCE_DIR / "phantom.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RSA_PRIVATE_KEY_PATH = str(KEYS_DIR / 'private.pem')
    RSA_PUBLIC_KEY_PATH = str(KEYS_DIR / 'public.pem')
