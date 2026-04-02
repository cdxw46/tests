from pydantic import BaseModel

class User(BaseModel):
	username: str
	password: str
	public_key: str = ''
	private_key: str = ''

class Email(BaseModel):
	uuid: str
	time: float
	read: bool
	data: str