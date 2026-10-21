import sys
from PIL import Image, ImageDraw, ImageFont
F='/usr/share/fonts/truetype/sand-box/google/Nunito/Nunito-VariableFont_wght.ttf'
CAP={'1_villages':('See every street your cart can drive','The Villages, FL'),
     '2_keywest':('Routes that stick to legal streets','Key West, FL'),
     '3_destin':('Steer clear of fast, no-go roads','Destin, FL'),
     '4_wailea':('37 cart towns, from Maui to Maine','Wailea & Kihei, Maui'),
     '5_hhi':('Battery check for the round trip','Hilton Head, SC')}
def font(sz,w):
    f=ImageFont.truetype(F,sz)
    try: f.set_variation_by_name(w)
    except Exception: pass
    return f
def wrap(d,t,f,maxw):
    words=t.split();lines=[];cur=''
    for w in words:
        s=(cur+' '+w).strip()
        if d.textlength(s,font=f)<=maxw: cur=s
        else: lines.append(cur);cur=w
    lines.append(cur);return lines
def make(name,raw,W,H,capH,big,small,out):
    im=Image.new('RGB',(W,H));d=ImageDraw.Draw(im)
    for y in range(capH):  # teal gradient
        t=y/capH;c=tuple(int(a+(b-a)*t) for a,b in zip((20,184,196),(11,110,134)));d.line([(0,y),(W,y)],fill=c)
    app=Image.open(raw).convert('RGB');assert app.size==(W,H-capH),(app.size,(W,H-capH))
    im.paste(app,(0,capH))
    t,sub=CAP[name];fb=font(big,'ExtraBold');fs=font(small,'Bold')
    lines=wrap(d,t,fb,W*0.86);lh=int(big*1.15);total=len(lines)*lh+int(small*1.6)
    y=(capH-total)//2
    for L in lines:
        d.text(((W-d.textlength(L,font=fb))/2,y),L,font=fb,fill='white');y+=lh
    y+=int(small*0.35);d.text(((W-d.textlength(sub,font=fs))/2,y),sub,font=fs,fill=(220,250,252))
    im.save(out,optimize=True);print(out,im.size)
kind=sys.argv[1]
import os;os.makedirs('screenshots/iphone_6.9',exist_ok=True);os.makedirs('screenshots/ipad_13',exist_ok=True)
for n in CAP:
    if kind=='iphone': make(n,f'raw/{n}_440x769.png',1320,2868,561,104,58,f'screenshots/iphone_6.9/{n}.png')
    else: make(n,f'raw/{n}_1032x1176.png',2064,2752,400,96,54,f'screenshots/ipad_13/{n}.png')
