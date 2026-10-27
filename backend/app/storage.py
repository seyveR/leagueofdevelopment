import os,struct,zlib
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import FileResponse
from .db import get_db
from .platform_models import MediaFile
from .security import current_user

class LocalFileStore:
    """Replaceable boundary; keys are generated internally, never user paths."""
    root=Path(os.getenv('FILE_ROOT','/data/files'))
    def put(self,key,content):
        self.root.mkdir(parents=True,exist_ok=True);target=self.root/key
        temporary=target.with_suffix('.tmp');temporary.write_bytes(content);os.replace(temporary,target)
    def path(self,key):return self.root/key
    def remove(self,key):(self.root/key).unlink(missing_ok=True)
FILES=LocalFileStore();LIMIT=3*1024*1024
router=APIRouter(prefix='/api',tags=['Файлы'])
def validate_png(content):
    if content[:8]!=b'\x89PNG\r\n\x1a\n':raise HTTPException(422,'Фотография должна быть PNG')
    offset=8;size=None;ended=False;has_pixels=False
    while offset+12<=len(content):
        n=struct.unpack('>I',content[offset:offset+4])[0];kind=content[offset+4:offset+8]
        if n>LIMIT or offset+12+n>len(content):raise HTTPException(422,'Повреждённый PNG')
        data=content[offset+8:offset+8+n];crc=struct.unpack('>I',content[offset+8+n:offset+12+n])[0]
        if offset==8 and kind!=b'IHDR':raise HTTPException(422,'Повреждённый PNG')
        if kind==b'IDAT':has_pixels=True
        if zlib.crc32(kind+data)&0xffffffff!=crc:raise HTTPException(422,'Повреждённый PNG')
        if kind==b'IHDR':
            if n!=13:raise HTTPException(422,'Повреждённый PNG')
            size=struct.unpack('>II',data[:8])
        offset+=12+n
        if kind==b'IEND':ended=True;break
    if not ended or not has_pixels or not size or not all(0<v<=4096 for v in size) or size[0]*size[1]>12000000 or offset!=len(content):raise HTTPException(422,'PNG: не более 4096 px по стороне и 12 млн пикселей')
@router.post('/files')
async def upload(request:Request,purpose:str='photo',user=Depends(current_user),db=Depends(get_db)):
    if user.role not in ('partner','admin'):raise HTTPException(403)
    from .platform_services import sensitive_limit
    sensitive_limit(db,user,'upload',20)
    if purpose not in ('photo','document'):raise HTTPException(422)
    content=bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content)>LIMIT:raise HTTPException(413,'Максимальный размер — 3 МБ')
    content=bytes(content)
    if purpose=='photo':validate_png(content);extension='png';mime='image/png'
    else:
        if not content.startswith(b'%PDF-') or b'%%EOF' not in content[-1024:]:raise HTTPException(422,'Документ должен быть PDF')
        extension='pdf';mime='application/pdf'
    id=str(uuid4());key=f'{id}.{extension}';FILES.put(key,content)
    try:db.add(MediaFile(id=id,owner_id=user.id,path=key,mime=mime,private=purpose=='document',size=len(content)));db.commit()
    except Exception:FILES.remove(key);raise
    return {'id':id,'url':f'/api/media/{id}','private':purpose=='document','size':len(content)}
@router.get('/media/{id}')
def download(id:str,request:Request,db=Depends(get_db)):
    row=db.get(MediaFile,id)
    if not row:raise HTTPException(404)
    if row.private:
        user=current_user(request,db)
        if user.role!='admin' and row.owner_id!=user.id:raise HTTPException(404)
    path=FILES.path(row.path)
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,media_type=row.mime,filename=row.path if row.private else None,headers={'Content-Security-Policy':"default-src 'none'; sandbox",'X-Content-Type-Options':'nosniff'})
