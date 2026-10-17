"""Safe, on-demand freshness checks of a fixed allowlist of organizer pages.
HTTP reachability is NOT evidence that registration is open.
"""
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from backend.real_opportunities import discover_real_opportunities

ALLOWED_HOSTS = {'ghw.mlh.com', 'www.outreachy.org', 'summerofcode.withgoogle.com'}


def _safe_url(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname in ALLOWED_HOSTS and not p.username and not p.password and p.port is None


async def check_sources(category='all'):
    entries = discover_real_opportunities(category)
    timeout = httpx.Timeout(7.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={'User-Agent':'ORBIT-Hackathon-SourceCheck/1.0'}) as client:
        async def check(entry):
            row = dict(entry)
            row['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
            row['registration_open_verified'] = False
            row['live_checked'] = True
            row['live_status'] = 'unknown'
            row['check_note'] = 'Registration is not confirmed by HTTP availability; verify on the organizer website.'
            if not _safe_url(row['url']):
                row['live_status'] = 'blocked_url'
                return row
            try:
                response = await client.get(row['url'])
                if response.status_code == 200:
                    row['live_status'] = 'official_page_reachable'
                elif response.status_code in (301, 302, 303, 307, 308):
                    row['live_status'] = 'redirect_unverified'
                else:
                    row['live_status'] = f'http_{response.status_code}'
            except httpx.HTTPError:
                row['live_status'] = 'network_check_failed'
            return row
        return await asyncio.gather(*(check(item) for item in entries))
