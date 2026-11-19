#!/usr/bin/env python3
"""Build 3 branded door-focused graphics for one INFINEX review publication.
Only already licensed, editorially checked stock pictures.
Does not publish. Original logo file is preserved verbatim.
"""
import json, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"assets"/"campaigns"/"puertas_20261119"
STOCK=BASE/"assets"/"candidates"
LOGO=BASE/"assets"/"branding"/"logo_infinex_original.jpg"
LOGO_SHA="65e35a825681bad432082014a8b69402d30996be58b3ae97958deb3a40d33f31"
BANK=json.loads((BASE/"assets"/"photo_library.json").read_text(encoding="utf-8"))
assert BANK["license"]=="https://www.pexels.com/license/"
assert hashlib.sha256(LOGO.read_bytes()).hexdigest()==LOGO_SHA
source_ids=["18379563","4671453","9163098"]
sources={str(x["id"]):x for x in BANK["gates"]}
assert len(set(source_ids))==3 and all(i in sources for i in source_ids)
OUT.mkdir(parents=True,exist_ok=True)
W,H=1080,1350
BLACK=(7,10,13)
ORANGE=(255,113,20)
WHITE=(246,247,249)
GRAY=(188,191,195)
def font(sz,bold=False):
    paths=([r"C:\Windows\Fonts\arialbd.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold
           else [r"C:\Windows\Fonts\arial.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for p in paths:
        if Path(p).is_file(): return ImageFont.truetype(p,sz)
    raise RuntimeError("FONT_UNAVAILABLE")
titles=[
    ("TU ENTRADA,","TU ESTILO.","PUERTAS METÁLICAS A MEDIDA"),
    ("DISEÑO A","TU GUSTO.","CHAPA · ALUMINIO · REFUERZOS"),
    ("¿IMAGINAS","LA TUYA?","PIDE PRESUPUESTO SIN COMPROMISO")
]
logo=Image.open(LOGO).convert("RGB")
logo=ImageOps.contain(logo,(155,155),Image.Resampling.LANCZOS)
files=[]
for i,src in enumerate(source_ids,1):
    img=Image.open(STOCK/(src+".jpg")).convert("RGB")
    if min(img.size)<650:raise RuntimeError("SOURCE_TOO_SMALL")
    hero=ImageOps.fit(img,(W,985),Image.Resampling.LANCZOS,centering=(0.5,0.5))
    page=Image.new("RGB",(W,H),BLACK);page.paste(hero,(0,0))
    # Bottom color darkens hero progressively, no misleading extra objects.
    fade=Image.new("RGBA",(W,H),(0,0,0,0)); fd=ImageDraw.Draw(fade)
    for y in range(620,1050):
        a=min(245,int((y-620)*245/430))
        fd.line((0,y,W,y),fill=(0,0,0,a))
    page=Image.alpha_composite(page.convert("RGBA"),fade).convert("RGB")
    d=ImageDraw.Draw(page)
    d.rectangle((0,0,W,14),fill=ORANGE)
    d.rounded_rectangle((43,40,230,230),radius=21,fill=(9,10,12))
    page.paste(logo,(58,55))
    d=ImageDraw.Draw(page)
    d.text((900,71),f"{i:02d} / 03",font=font(29,True),fill=WHITE,stroke_width=1,stroke_fill=(0,0,0))
    d.rounded_rectangle((53,837,235,850),radius=5,fill=ORANGE)
    line1,line2,tagline=titles[i-1]
    d.text((55,875),line1,font=font(78,True),fill=WHITE,stroke_width=2,stroke_fill=BLACK)
    d.text((55,958),line2,font=font(78,True),fill=WHITE,stroke_width=2,stroke_fill=BLACK)
    d.rectangle((54,1080,1026,1082),fill=(55,60,64))
    size=32
    while d.textbbox((0,0),tagline,font=font(size,True))[2]>965:size-=1
    d.text((57,1121),tagline,font=font(size,True),fill=ORANGE)
    d.text((57,1210),"INFINEX   |   IDEAS EN HIERRO",font=font(29,True),fill=WHITE)
    d.text((57,1282),"Fotografía ilustrativa · Pexels",font=font(21),fill=GRAY)
    path=OUT/f"{i:02d}.jpg"
    page.save(path,"JPEG",quality=92,subsampling=0,optimize=True)
    if path.stat().st_size<65000:raise RuntimeError("OUTPUT_TOO_SMALL")
    files.append({"path":path.relative_to(BASE).as_posix(),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                  "source_id":src,"source_page":sources[src]["page"]})
manifest={"campaign":"INFINEX-20261119-PUERTAS-01","theme":"puertas_metalicas",
          "date":"2026-11-19","destination":"infinex_2025",
          "license":"https://www.pexels.com/license/","not_actual_infinex_works":True,
          "logo_sha256":LOGO_SHA,"images":files}
(OUT/"sources.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
sheet=Image.new("RGB",(330*3,450),BLACK)
for i in range(3):
    with Image.open(OUT/f"{i+1:02d}.jpg") as img:
        sheet.paste(img.resize((330,413)),(330*i,0))
sheet.save(OUT/"review_contact.jpg",quality=88)
print("BRANDED_DOORS_CAROUSEL_BUILT",len(files),OUT)
