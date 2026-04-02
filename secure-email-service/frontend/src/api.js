const checkError = res => {
	if (res.detail) {
		throw new Error(res.detail);
	}
	return res;
}

export const login = async ({ username, password }) => {
	return checkError(await (await fetch('/api/login', {
		method: 'POST',
		body: JSON.stringify({ username, password }),
		headers: {
			'Content-Type': 'application/json'
		}
	})).json());
}

export const requireLogin = async (redirect = true) => {
	try {
		checkError(await (await fetch('/api/me', {
			headers: {
				'token': localStorage.getItem('token')
			}
		})).json());
	} catch(e) {
		if (redirect) location.href = '/';
		else throw e;
	}
}

export const emails = async () => {
	return checkError(await (await fetch(`/api/emails`, {
		headers: {
			'token': localStorage.getItem('token')
		}
	})).json());
}

export const email = async id => {
	return checkError(await (await fetch(`/api/email/${id}`, {
		headers: {
			'token': localStorage.getItem('token')
		}
	})).json());
}

export const rootCert = async () => {
	return checkError(await (await fetch('/api/root_cert')).json());
}

export const markRead = async id => {
	return checkError(await (await fetch(`/api/mark_read/${id}`, {
		method: 'POST',
		headers: {
			'token': localStorage.getItem('token')
		},
	})).json());
}

export const send = async (to, subject, body) => {
	return checkError(await (await fetch('/api/send', {
		method: 'POST',
		body: JSON.stringify({ to, subject, body }),
		headers: {
			'Content-Type': 'application/json',
			'token': localStorage.getItem('token')
		}
	})).json());
}

export const getPassword = async () => {
	return checkError(await (await fetch('/api/password')).json());
}