#!/usr/bin/env python3
"""Generates visually coherent, clearly disclosed simulated before/after slides.

The SAME original scene is shown before and with a digitally superimposed metal
gate/fence afterwards. Never claim INFINEX installed anything shown.
Original scene is not reused in any other publication.
"""
from __future__ import annotations
import hashlib,json,io,sys,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter,ImageFont,ImageOps,ImageEnhance

BASE=Path(__file__).resolve().parents[1]
LOGO=BASE/"assets/branding/logo_infinex_original.jpg"
LOGO_SHA="65e35a825681bad432082014a8b69402d30996be58b3ae97958deb3a40d33f31"
PLANS={
 "2026-11-22":dict(topic="puertas",pexels=8134821,author="Max Vakhtbovych",
     source_page="https://www.pexels.com/photo/modern-house-exterior-design-8134821/",
     title="EL ACCESO, SIN PUERTA",after_title="UNA ENTRADA CON CARÁCTER",
     after_detail="Una propuesta de puerta metálica de dos hojas",
     geometry=(410,630,1494,990),style="horizontal"),
 "2026-11-24":dict(topic="cerramientos",pexels=24419877,author="Sharath G.",
     source_page="https://www.pexels.com/photo/view-of-a-yard-24419877/",
     title="UN PASO ABIERTO",after_title="PRIVACIDAD CON DISEÑO",
     after_detail="Un cierre metálico para transformar el acceso",
     geometry=(545,370,1170,1030),style="vertical"),
 "2026-11-26":dict(topic="cerramientos",pexels=13068513,author="Pexels",
     source_page="https://www.pexels.com/photo/large-driveway-in-front-of-the-house-13068513/",
     title="DEL ESPACIO VACÍO",after_title="A UN EXTERIOR DEFINIDO",
     after_detail="Ejemplo digital de cerramiento para la entrada",
     geometry=(410,1400,1510,2060),style="horizontal"),
}
FONT_B=[r"C:\Windows\Fonts\bahnschrift.ttf",r"C:\Windows\Fonts\arialbd.ttf"]
FONT_R=[r"C:\Windows\Fonts\segoeui.ttf",r"C:\Windows\Fonts\arial.ttf"]
def font(sz,bold=True):
    for p in FONT_B if bold else FONT_R:
        if Path(p).exists():return ImageFont.truetype(p,sz)
    return ImageFont.load_default()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def draw_gate(image,geometry,style):
    base=image.convert("RGBA")
    overlay=Image.new("RGBA",base.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    x0,y0,x1,y1=geometry
    if y1>=base.height or x1>=base.width:raise RuntimeError("GATE_GEOMETRY_OUTSIDE_SOURCE")
    # Architectural dark anodized steel; gate shadow and structural perimeter.
    shadow=Image.new("RGBA",base.size,(0,0,0,0))
    sd=ImageDraw.Draw(shadow)
    sd.rectangle((x0+12,y0+13,x1+25,y1+20),fill=(0,0,0,132))
    shadow=shadow.filter(ImageFilter.GaussianBlur(17))
    base=Image.alpha_composite(base,shadow)
    main=(18,24,27,252)
    metal=(29,35,37,254)
    shine=(69,75,76,246)
    black=(7,11,13,254)
    # Long driveway concept: visually connect the entry to continuous metal
    # fence panels, rather than leaving an isolated floating gate.
    if x1-x0>1000 and y0>1100:
        for left,right in ((0,x0-20),(x1+20,base.width-1)):
            d.rectangle((left,y0+50,right,y1),fill=(19,25,28,252))
            for yy in range(y0+70,y1-19,31):
                d.line((left,yy,right,yy),fill=(53,59,61,255),width=4)
            for xx in range(left+18,right-6,105):
                d.line((xx,y0+52,xx,y1),fill=(4,8,10,255),width=7)
        for xx in (x0-23,x1+17):
            d.rectangle((xx,y0-34,xx+25,y1+7),fill=(43,47,46,255))
            d.line((xx+3,y0-32,xx+3,y1+4),fill=(93,96,94,255),width=3)
    d.rectangle((x0,y0,x1,y1),outline=main,width=16)
    if style=="horizontal":
        gap=10
        step=32
        for yy in range(y0+18,y1-18,step):
            lo=min(y1-16,yy+step-gap)
            d.rectangle((x0+17,yy,x1-18,lo),fill=metal)
            d.line((x0+19,yy+1,x1-20,yy+1),fill=shine,width=2)
            d.line((x0+19,lo-2,x1-20,lo-2),fill=black,width=2)
        seam=(x0+x1)//2
        d.rectangle((seam-7,y0+9,seam+8,y1-8),fill=black)
        d.rectangle((seam-3,y0+10,seam,y1-9),fill=shine)
        for xx in (x0+9,x1-9):
            for yy in (y0+82,y1-82):
                d.ellipse((xx-9,yy-9,xx+9,yy+9),fill=(3,5,6,255),outline=(80,84,84,255),width=2)
        # Key cylinder and handle on peatonal leaf.
        d.rounded_rectangle((seam+26,y0+145,seam+38,y0+192),radius=4,fill=(142,145,143,255))
        d.ellipse((seam+20,y0+210,seam+36,y0+226),fill=(146,148,145,255))
    else:
        step=34
        for xx in range(x0+18,x1-15,step):
            hi=min(x1-16,xx+step-11)
            d.rectangle((xx,y0+16,hi,y1-16),fill=metal)
            d.line((xx+2,y0+17,xx+2,y1-17),fill=shine,width=2)
        seam=(x0+x1)//2
        d.rectangle((seam-8,y0+9,seam+8,y1-9),fill=black)
    d.line((x0+10,y0+10,x1-10,y0+10),fill=(100,105,106,200),width=3)
    return Image.alpha_composite(base,overlay).convert("RGB")

def slide(scene,mode,plan,out):
    W,H=1080,1350
    black=(8,11,14)
    orange=(252,111,16)
    canvas=Image.new("RGB",(W,H),black)
    # Crop highlights the same original viewpoint for before & after.
    image=ImageOps.fit(scene,(W,987),Image.Resampling.LANCZOS,centering=(.5,.52))
    canvas.paste(image,(0,0))
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,W,15),fill=orange)
    logo=ImageOps.contain(Image.open(LOGO).convert("RGB"),(180,168),Image.Resampling.LANCZOS)
    d.rounded_rectangle((41,39,41+logo.width+18,57+logo.height+17),radius=16,fill=(8,11,14))
    canvas.paste(logo,(50,56))
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((757,62,1010,129),radius=15,fill=black)
    label="ANTES" if mode=="before" else "DESPUÉS"
    d.text((782,74),label,font=font(41),fill=orange if mode=="after" else (244,244,244))
    # Bottom premium legibility panel: black/white/orange consistent with brand.
    d.rectangle((0,970,W,H),fill=black)
    d.rectangle((62,1002,220,1013),fill=orange)
    title=plan["title"] if mode=="before" else plan["after_title"]
    size=56
    while d.textbbox((0,0),title,font=font(size))[2]>W-135:size-=2
    d.text((60,1040),title,font=font(size),fill=(247,249,250))
    detail=("El mismo espacio, sin instalar la puerta."
            if mode=="before" else plan["after_detail"])
    s=32
    while d.textbbox((0,0),detail,font=font(s,False))[2]>W-120:s-=1
    d.text((60,1133),detail,font=font(s,False),fill=(212,217,219))
    d.line((61,1208,1020,1208),fill=(67,71,73),width=2)
    d.text((60,1227),"PROPUESTA DIGITAL · NO ES UNA OBRA REAL",font=font(25,False),fill=orange)
    d.text((60,1296),"INFINEX  ·  IDEAS EN HIERRO, SOLUCIONES REALES",font=font(22),fill=(225,228,228))
    out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(out,"JPEG",quality=94,subsampling=0,optimize=True)

def build(day):
    p=PLANS[day]
    dest=BASE/"assets"/"before_after"/(day+"_09_"+p["topic"])
    dest.mkdir(parents=True,exist_ok=True)
    source=dest/"original.jpg"
    if not source.exists():
        url=f"https://images.pexels.com/photos/{p['pexels']}/pexels-photo-{p['pexels']}.jpeg?auto=compress&cs=tinysrgb&w=2000"
        req=urllib.request.Request(url,headers={"User-Agent":"INFINEX-licensed-illustrative/1.0"})
        with urllib.request.urlopen(req,timeout=30) as response:
            if not response.headers.get("Content-Type","").startswith("image/"):
                raise RuntimeError("SOURCE_NOT_IMAGE")
            data=response.read()
        if len(data)<100000:raise RuntimeError("SOURCE_TOO_SMALL")
        source.write_bytes(data)
    if digest(LOGO)!=LOGO_SHA:raise RuntimeError("CORPORATE_LOGO_CHANGED")
    original=Image.open(source).convert("RGB")
    if original.width<1400 or original.height<900:
        raise RuntimeError("SOURCE_NOT_SUFFICIENT_RESOLUTION")
    modified=draw_gate(original,p["geometry"],p["style"])
    before=dest/"01_antes.jpg"
    after=dest/"02_despues.jpg"
    slide(original,"before",p,before)
    slide(modified,"after",p,after)
    data={
      "date":day,"slot":"09","time_local":"09:30","type":"BEFORE_AFTER",
      "topic":p["topic"],"scene_key":"pexels:"+str(p["pexels"]),
      "illustrative_simulation":True,"not_actual_infinex_works":True,
      "description":"digital architectural mock-up; no real construction",
      "source_page":p["source_page"],"source_author":p["author"],
      "source_license":"https://www.pexels.com/license/",
      "source_image":"assets/before_after/"+(day+"_09_"+p["topic"])+"/original.jpg",
      "source_sha256":digest(source),
      "logo_sha256":LOGO_SHA,
      "titles":[p["title"],p["after_title"]],
      "images":[
         {"path":before.relative_to(BASE).as_posix(),"sha256":digest(before)},
         {"path":after.relative_to(BASE).as_posix(),"sha256":digest(after)}
      ],
      "approved_for_publish":True
    }
    manifest=dest/"sources.json"
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("INFINEX_BEFORE_AFTER_PREPARED",day,p["topic"],"2x1080x1350",p["pexels"],flush=True)
if __name__=="__main__":
    selected=sys.argv[1:] or list(PLANS)
    for day in selected:build(day)
