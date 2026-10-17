"""Password-gated hackathon demo with signed session cookies and CSRF origin checks.
For real multi-user production, replace this with per-user identity and record ownership.
"""
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlparse
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE = 'orbit_session'
TTL = 8 * 60 * 60
router = APIRouter(tags=['ORBIT access'])

def _secret():
    value = os.getenv('ORBIT_ACCESS_TOKEN', '').strip()
    if len(value) < 24:
        raise RuntimeError('Set ORBIT_ACCESS_TOKEN to a random secret of at least 24 characters in .env')
    return value

def _sign(value):
    return hmac.new(_secret().encode(), value.encode(), hashlib.sha256).hexdigest()

def _valid_session(cookie):
    if not cookie:
        return False
    try:
        expiry, nonce, signature = cookie.split('.', 2)
        if not expiry.isdecimal() or int(expiry) < time.time() or int(expiry) > time.time() + TTL + 60:
            return False
        return hmac.compare_digest(_sign(f'{expiry}.{nonce}'), signature)
    except (ValueError, RuntimeError):
        return False

def _session():
    value = f'{int(time.time() + TTL)}.{secrets.token_hex(12)}'
    return f'{value}.{_sign(value)}'

class OrbitAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            token = _secret()
        except RuntimeError:
            return JSONResponse({'detail': 'ORBIT_ACCESS_TOKEN must be configured before serving the application'}, status_code=503)
        path = request.url.path
        if path in ('/login', '/logout', '/health'):
            return await call_next(request)
        cookie_ok = _valid_session(request.cookies.get(COOKIE))
        header = request.headers.get('authorization', '')
        bearer_ok = header.startswith('Bearer ') and hmac.compare_digest(header[7:], token)
        if not (cookie_ok or bearer_ok):
            if path.startswith('/api/') or path.startswith('/openapi'):
                return JSONResponse({'detail': 'Authentication required'}, status_code=401)
            return RedirectResponse('/login', status_code=303)
        if cookie_ok and not bearer_ok and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if origin:
                p = urlparse(origin)
                if p.scheme != request.url.scheme or p.netloc != request.headers.get('host'):
                    return JSONResponse({'detail': 'Cross-site request blocked'}, status_code=403)
            elif request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Cross-site request blocked'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Cache-Control'] = 'no-store'
        return response

@router.get('/login', response_class=HTMLResponse)
def login_form():
    return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>ORBIT Access</title></head><body style="background:#090f20;color:#fff;font:16px system-ui;max-width:420px;margin:12vh auto;padding:25px"><h1>ORBIT</h1><p>Enter the demo access passphrase to continue.</p><form method="post" action="/login"><input name="passphrase" type="password" required autocomplete="current-password" style="padding:12px;width:95%"><button style="padding:12px;margin-top:16px">Sign in</button></form></body></html>'''

@router.post('/login')
async def login(request: Request):
    # Parse form without python-multipart dependency (URL-encoded only).
    from urllib.parse import parse_qs
    raw = await request.body()
    if len(raw) > 4096:
        return HTMLResponse('Invalid request', status_code=400)
    passphrase = parse_qs(raw.decode('utf-8', errors='replace')).get('passphrase', [''])[0]
    if not hmac.compare_digest(passphrase, _secret()):
        return HTMLResponse('Incorrect passphrase. <a href="/login">Try again</a>', status_code=401)
    response = RedirectResponse('/app', status_code=303)
    response.set_cookie(COOKIE, _session(), max_age=TTL, httponly=True,
                        secure=os.getenv('ORBIT_COOKIE_SECURE', 'false').lower() == 'true',
                        samesite='strict', path='/')
    return response

@router.post('/logout')
def logout():
    response = RedirectResponse('/login', status_code=303)
    response.delete_cookie(COOKIE, path='/')
    return response
