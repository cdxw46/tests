from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import datetime
import smail

def generate_email(
	sender: str,
	recipient: str,
	subject: str,
	content: str,
	html: bool = False,
	sign: bool = False,
	cert: str = '',
	key: str = '',
) -> str:
	msg = MIMEMultipart()
	msg['From'] = sender
	msg['To'] = recipient
	msg['Subject'] = subject
	msg.attach(MIMEText(content))

	if html:
		msg.attach(MIMEText(content, 'html'))		

	if sign:
		return smail.sign_message(msg, key.encode(), cert.encode()).as_string()

	return msg.as_string()

def generate_root_cert() -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
	priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	pub = priv.public_key()

	name = x509.Name([
		x509.NameAttribute(x509.NameOID.COMMON_NAME, 'secure-mail-service'),
	])

	b = x509.CertificateBuilder()
	b = b.subject_name(name)
	b = b.issuer_name(name)
	b = b.public_key(pub)
	b = b.serial_number(x509.random_serial_number())
	b = b.not_valid_before(datetime.datetime.now())
	b = b.not_valid_after(datetime.datetime.now() + datetime.timedelta(days=365))
	b = b.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
	b = b.add_extension(x509.SubjectKeyIdentifier.from_public_key(pub), critical=False)
	b = b.add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(pub), critical=False)
	b = b.add_extension(x509.KeyUsage(
		digital_signature=False,
		content_commitment=False,
		key_encipherment=False,
		data_encipherment=False,
		key_agreement=False,
		key_cert_sign=True,
		crl_sign=True,
		encipher_only=False,
		decipher_only=False,
	), critical=True)

	return b.sign(priv, hashes.SHA256()), priv

def generate_sign_cert(
	username: str,
	root_cert: x509.Certificate,
	root_key: rsa.RSAPrivateKey
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
	priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	pub = priv.public_key()

	b = x509.CertificateBuilder()
	b = b.subject_name(x509.Name([
		x509.NameAttribute(x509.NameOID.COMMON_NAME, username),
		x509.NameAttribute(x509.NameOID.EMAIL_ADDRESS, username)
	]))
	b = b.issuer_name(root_cert.issuer)
	b = b.public_key(pub)
	b = b.serial_number(x509.random_serial_number())
	b = b.not_valid_before(datetime.datetime.now())
	b = b.not_valid_after(datetime.datetime.now() + datetime.timedelta(days=365))
	b = b.add_extension(x509.SubjectAlternativeName([x509.RFC822Name(username)]), critical=False)
	b = b.add_extension(x509.KeyUsage(
		digital_signature=True,
		content_commitment=False,
		key_encipherment=True,
		data_encipherment=False,
		key_agreement=False,
		key_cert_sign=False,
		crl_sign=False,
		encipher_only=False,
		decipher_only=False,
	), critical=True)
	b = b.add_extension(x509.ExtendedKeyUsage([
		ExtendedKeyUsageOID.CLIENT_AUTH,
		ExtendedKeyUsageOID.EMAIL_PROTECTION,
	]), critical=False)

	return b.sign(root_key, hashes.SHA256()), priv

def export(pair: tuple[x509.Certificate, rsa.RSAPrivateKey]) -> tuple[str, str]:
	pub = pair[0].public_bytes(serialization.Encoding.PEM).decode()
	priv = pair[1].private_bytes(
		serialization.Encoding.PEM,
		serialization.PrivateFormat.PKCS8,
		serialization.NoEncryption()
	).decode()
	return pub, priv