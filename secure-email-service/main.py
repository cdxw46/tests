from typing import Annotated
from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from model import *

import asyncio
import db
import util
import uuid
import uvicorn
import sys
import os

app = FastAPI()

template = Template(open('./template.jinja2', 'r').read(), autoescape=True)
browser = asyncio.Lock()

@app.post('/api/login')
async def login(
	username: Annotated[str, Body()],
	password: Annotated[str, Body()]
) -> str:
	user = await db.get_user(username)
	if password != user.password:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='incorrect password'
		)
	return await db.make_token(user.username)

@app.get('/api/me')
async def ok(user: Annotated[User, Depends(db.request_user)]):
	return user.username

@app.get('/api/emails')
async def emails(
	user: Annotated[User, Depends(db.request_user)],
) -> dict[str, Email]:
	return await db.get_emails(user)

@app.get('/api/email/{email_id}')
async def email(
	user: Annotated[User, Depends(db.request_user)],
	email_id: str
):
	return await db.get_email(user, email_id)

@app.post('/api/mark_read/{email_id}')
async def mark_read(
	user: Annotated[User, Depends(db.request_user)], 
	email_id: str
) -> bool:
	return await db.mark_read(user, str(email_id))

@app.post('/api/send')
async def send(
	user: Annotated[User, Depends(db.request_user)],
	to: Annotated[str, Body()],
	subject: Annotated[str, Body()],
	body: Annotated[str, Body()]
):
	# make sure the email we're sending to is valid
	recipient = await db.get_user(to)

	if len(user.public_key) == 0:
		msg = util.generate_email(
			sender=user.username,
			recipient=recipient.username,
			subject=subject,
			content=body,
		)
	else:
		msg = util.generate_email(
			sender=user.username,
			recipient=recipient.username,
			subject=subject,
			content=template.render(
				title=subject,
				content=body
			),
			html=True,
			sign=True,
			cert=user.public_key,
			key=user.private_key
		)

	email_id = str(uuid.uuid4())
	await db.send_email(recipient, email_id, msg)

	return email_id

@app.get('/api/root_cert')
async def root_cert():
	return await db.get_root_cert()

@app.post('/api/admin_bot')
async def admin_bot(_: Annotated[User, Depends(db.request_user)],):
	admin = await db.get_user('admin@ses')
	
	async with browser:
		async with asyncio.timeout(15):
			proc = await asyncio.create_subprocess_exec(sys.executable, 'admin_bot.py', env={
				'FLAG': os.environ.get('FLAG', 'picoCTF{flag}'),
				'PASSWORD': admin.password,
			})
			await proc.wait()

	return 'success'

@app.get('/api/password')
async def password():
	return await db.get_user_password()

app.mount('/', StaticFiles(directory='static', html=True), name='static')

uvicorn.run(app, port=8000, host='0.0.0.0')