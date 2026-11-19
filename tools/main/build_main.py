import base64, io, os, sys
from fontTools import subset
HERE=os.path.dirname(os.path.abspath(__file__)); FONT_DIR=os.path.join(HERE,'..','fonts')
src=open(os.path.join(HERE,'index.src.html'),encoding='utf-8').read()
text=src+''.join(chr(c) for c in range(32,127))+'−±→…—•“”·'
faces=[]
for fam,path,rng in [("Pretendard Variable","PretendardVariable.woff2","45 920"),("Archivo","archivo-latin-wdth-normal.woff2","100 900")]:
    opts=subset.Options(); opts.flavor='woff2'; opts.layout_features=['*']
    f=subset.load_font(os.path.join(FONT_DIR,path),opts)
    s=subset.Subsetter(opts); s.populate(text=text); s.subset(f)
    bio=io.BytesIO(); subset.save_font(f,bio,opts)
    b64=base64.b64encode(bio.getvalue()).decode()
    st="font-stretch:62% 125%;" if fam=="Archivo" else ""
    faces.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:{rng};{st}font-display:swap}}")
out=src.replace('/*FONTS*/',''.join(faces))
open(sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,'index.html'),'w',encoding='utf-8').write(out)
print(len(out)//1024,'KB')
