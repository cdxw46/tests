from cryptography.hazmat.primitives import serialization
from model import *
from jinja2 import Template

import asyncio
import db
import secrets
import uuid
import util

template = Template(open('./template.jinja2', 'r').read(), autoescape=True)

async def init():
	if await db.r.get('initialized') is not None:
		return await db.r.aclose() # type: ignore
	
	await db.r.set('initialized', 1)

	ca_pub, ca_priv = util.generate_root_cert()
	await db.set_root_cert(ca_pub.public_bytes(serialization.Encoding.PEM).decode())

	admin_pub, admin_priv = util.export(util.generate_sign_cert('admin@ses', ca_pub, ca_priv))
	admin = User(
		username='admin@ses',
		password=secrets.token_hex(16),
		public_key=admin_pub,
		private_key=admin_priv
	)
	await db.set_user('admin@ses', admin)

	user = User(
		username='user@ses',
		password=secrets.token_hex(16)
	)
	await db.set_user('user@ses', user)

	msg = util.generate_email(
		sender=admin.username,
		recipient=user.username,
		subject='Welcome to Secure Email Service!',
		content=template.render(title='Welcome!', content='\n\n'.join([
			'Welcome to Secure Email Service (SES)!',
			'We\'re excited to have you on board and look forward to helping you manage your email needs with ease and reliability.',
			'If you have any questions or need assistance, feel free to reach out to us at admin@ses. Our team is here to support you every step of the way.',
			'Thank you for choosing SES!',
			'Best regards,',
			'The Secure Email Service Team'
		])),
		html=True,
		sign=True,
		cert=admin_pub,
		key=admin_priv
	)
	await db.send_email(user, str(uuid.uuid4()), msg)

	print('username:', user.username)
	print('password:', user.password)

	print('admin username:', admin.username)
	print('admin password:', admin.password)

	await db.r.aclose() # type: ignore

asyncio.run(init())