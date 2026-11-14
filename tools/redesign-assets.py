from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
p=root/'public/redesign';p.mkdir(exist_ok=True)
im=Image.open(root/'references/redesign/liza.png')
for state,x,y in [('explaining',302,42),('waiting',522,42),('completed',191,42),('support',302,263),('speaking',413,42)]:
    im.crop((x,y,x+107,y+215)).save(p/('liza-'+state+'.png'))
