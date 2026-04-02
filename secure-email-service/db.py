from typing import Annotated
from fastapi import HTTPException, Header, status
from model import *
from redis.asyncio import Redis
from datetime import datetime

import email
import secrets

r = Redis(host='redis')

async def request_user(token: Annotated[str, Header()]) -> User:
	username = await r.hget('tokens', token)
	if username is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='invalid token'
		)
	assert (user := await r.hget('users', username)) is not None
	return User.model_validate_json(user)

async def get_user(username: str) -> User:
	user = await r.hget('users', username)
	if user is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail='user not found'
		)
	return User.model_validate_json(user)

async def set_user(username: str, user: User):
	await r.hset('users', username, user.model_dump_json())

async def make_token(username: str) -> str:
	token = secrets.token_hex(32)
	await r.hset('tokens', token, username)
	return token

async def get_emails(user: User) -> dict[str, Email]:
	emails: dict[str, Email] = {}
	async for key, value in r.hscan_iter(f'emails-{user.username}'):
		email = Email.model_validate_json(value)
		emails[key.decode()] = email
	return emails

async def get_email(user: User, email_id: str) -> Email:
	if (email := await r.hget(f'emails-{user.username}', email_id)) is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail='email not found'
		)
	return Email.model_validate_json(email.decode())

async def mark_read(user: User, email_id: str) -> bool:
	if (msg := await r.hget(f'emails-{user.username}', email_id)) is not None:
		email = Email.model_validate_json(msg)
		email.read = True
		await r.hset(f'emails-{user.username}', email_id, email.model_dump_json())
		return True
	return False

async def send_email(user: User, email_id: str, raw: str):
	await r.hset(
		f'emails-{user.username}',
		email_id,
		Email(
			uuid=email_id,
			read=False,
			data=raw,
			time=datetime.now().timestamp()
		).model_dump_json()
	)

async def set_root_cert(cert: str):
	await r.set('root_cert', cert)

async def get_root_cert():
	assert (cert := await r.get('root_cert')) is not None
	return cert.decode()

async def get_user_password():
	if await r.get('seen_password') is not None:
		return 'already seen'
	await r.set('seen_password', 1)
	return (await get_user('user@ses')).password