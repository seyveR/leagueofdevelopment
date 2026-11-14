from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
p=root/'public/redesign';p.mkdir(exist_ok=True)
# Character PNGs are now isolated generated assets. Never overwrite them with sheet crops.
im=Image.open(root/'references/redesign/palette.png')
for row in range(4):
    for col in range(5):
        x=366+col*115;y=55+row*98
        im.crop((x,y,x+102,y+86)).save(p/('icon-'+str(row*5+col)+'.png'))
