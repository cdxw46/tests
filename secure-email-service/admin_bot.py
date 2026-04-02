from os import environ
from playwright.async_api import async_playwright, expect

import asyncio
import re

flag = environ.get('FLAG', 'picoCTF{flag}')
password = environ.get('PASSWORD', 'admin@ses')

async def bot():
	async with asyncio.timeout(12):
		async with async_playwright() as p:
			browser = await p.chromium.launch()
			page = await browser.new_page()
			await page.goto('http://127.0.0.1:8000')

			await page.evaluate('flag => localStorage.setItem("flag", flag)', flag)
			
			# login
			await page.type('[name=username]', 'admin@ses')
			await page.type('[name=password]', password)
			await page.click('button')

			# click on first email
			await page.wait_for_url('http://127.0.0.1:8000/inbox.html', wait_until='networkidle')
			try:
				await page.click('tbody tr', timeout=1000)
			except:
				await browser.close()
				return

			# click reply button
			await page.wait_for_url('http://127.0.0.1:8000/email.html?id=*', wait_until='networkidle')
			await expect(page.locator('#reply')).to_have_attribute('href', re.compile('.*'))
			await page.click('#reply button')

			# reply to email
			await page.wait_for_url('http://127.0.0.1:8000/reply.html?id=*', wait_until='networkidle')
			await page.type('textarea', '\n\n'.join([
				'We\'ve gotten your message and will respond soon.',
				'Thank you for choosing SES!',
				'Best regards,',
				'The Secure Email Service Team'
			]))
			await page.click('#reply button')
			await browser.close()

asyncio.run(bot())