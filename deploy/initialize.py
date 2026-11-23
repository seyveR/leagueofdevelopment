"""Run on a fresh server: create secrets locally, never print them."""
from pathlib import Path
import secrets
root=Path('/opt/league')
env=root/'.env'
if not env.exists():
    env.write_text('APP_VERSION=8705a79\nAPP_DOMAIN=ligarazvitiya29.ru\nPOSTGRES_PASSWORD='+secrets.token_urlsafe(40)+'\n')
env.chmod(0o600)
override=Path('/etc/systemd/system/caddy.service.d')
override.mkdir(parents=True,exist_ok=True)
(override/'league.conf').write_text('[Service]\nEnvironment=APP_DOMAIN=ligarazvitiya29.ru\n')
print('Server environment initialized; secret values not displayed.')
