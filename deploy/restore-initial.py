"""Initial import only. Refuse to overwrite any populated public schema."""
from pathlib import Path
import subprocess,hashlib
root=Path('/opt/league')
def run(args,**kwargs):return subprocess.run(args,cwd=root,check=True,**kwargs)
def compose(*args,**kwargs):return run(['docker','compose',*args],**kwargs)
if (root/'.restored').exists():raise SystemExit('Already restored; refusing another initial import')
for manifest in ['SHA256SUMS','DATA-SHA256SUMS']:
    for line in (root/'transfer'/manifest).read_text().splitlines():
        expected,name=line.split(None,1);name=name.strip()
        if name not in ('images.tar.gz','source.tar.gz','database.dump','files.tar.gz'):raise SystemExit('Unexpected archive name')
        with (root/'transfer'/name).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:raise SystemExit('Checksum mismatch: '+name)
print('All transferred archives verified.',flush=True)
tables=compose('exec','-T','postgres','psql','-U','liga','-d','liga','-Atc',"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'",capture_output=True,text=True).stdout.strip()
if tables!='0':raise SystemExit('Public schema is not empty; refusing overwrite')
compose('cp','transfer/database.dump','postgres:/tmp/league-import.dump')
with (root/'restore.log').open('w') as log:
    compose('exec','-T','postgres','pg_restore','-U','liga','-d','liga','--no-owner','--no-privileges','--exit-on-error','/tmp/league-import.dump',stdout=log,stderr=log)
run(['docker','volume','create','liga-public_liga-files'],stdout=subprocess.DEVNULL)
run(['docker','run','--rm','-v','liga-public_liga-files:/data','-v','/opt/league/transfer:/transfer:ro','postgres:17.5-alpine','tar','-C','/data','-xzf','/transfer/files.tar.gz'])
run(['tar','-C',str(root),'-xzf',str(root/'transfer/source.tar.gz')])
compose('exec','-T','postgres','rm','/tmp/league-import.dump')
(root/'.restored').write_text('Initial import completed from verified archives.\n')
print('Database, files and source restored.',flush=True)
compose('up','-d','--no-build','--pull','never','--wait')
