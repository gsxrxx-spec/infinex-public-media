#!/usr/bin/env python3
"""INFINEX premium 3-slide doors campaign. Pexels licensed illustrative photos."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import hashlib, json, math
BASE=Path(__file__).resolve().parents[1]
LOGO=BASE/"assets"/"branding"/"logo_infinex_original.jpg"
LOGO_SHA="65e35a825681bad432082014a8b69402d30996be58b3ae97958deb3a40d33f31"
assert hashlib.sha256(LOGO.read_bytes()).hexdigest()==LOGO_SHA
CAND=BASE/"assets"/"candidates"/"premium_doors_nov19"
OUT=BASE/"assets"/"campaigns"/"puertas_premium_nov2026_trial"
OUT.mkdir(parents=True,exist_ok=True)
W,H=1080,1350
ORANGE=(255,111,12); INK=(8,10,13); WHITE=(250,249,247); MUTED=(200,202,206)
FONT_FILES=[r"C:\Windows\Fonts\bahnschrift.ttf",r"C:\Windows\Fonts\arialbd.ttf",r"C:\Windows\Fonts\segoeuib.ttf"]
REGULAR=[r"C:\Windows\Fonts\segoeui.ttf",r"C:\Windows\Fonts\arial.ttf"]
def font(size,bold=False):
    for p in (FONT_FILES if bold else REGULAR):
        if Path(p).is_file():return ImageFont.truetype(p,size)
    raise RuntimeError("NO_BRAND_FONTS")
def measure(d,s,size,bold=False):
    f=font(size,bold)
    return d.textbbox((0,0),s,font=f)[2]
def fit_text(d,s,max_width,size,bold=True):
    while size>=22 and measure(d,s,size,bold)>max_width:size-=1
    return font(size,bold)
def text_shadow(d,xy,s,f,fill):
    x,y=xy
    for dx,dy,a in [(3,4,155),(1,2,155)]:
        d.text((x+dx,y+dy),s,font=f,fill=(0,0,0,a))
    d.text((x,y),s,font=f,fill=fill)
PAGES=[
    dict(id="14499728",source_page="https://www.pexels.com/photo/view-of-a-modern-house-with-flowers-on-a-balcony-and-black-garage-door-14499728/",
         line1="TU ENTRADA,",line2="TU ESTILO.",category="PUERTAS METÁLICAS A MEDIDA",
         copy="Una entrada que refleje tu personalidad.",cta="DESLIZA Y DESCUBRE"),
    dict(id="34190707",source_page="https://www.pexels.com/photo/minimalistic-black-door-on-urban-street-34190707/",
         line1="CADA DETALLE",line2="CUENTA.",category="DISEÑO ADAPTADO A TU ESPACIO",
         copy="Medidas, acabados y detalles a tu gusto.",cta="IMAGINA TU DISEÑO"),
    dict(id="28384143",source_page="https://www.pexels.com/photo/modern-industrial-garage-door-with-number-49-28384143/",
         line1="HAZLA",line2="REALIDAD.",category="¿YA IMAGINAS TU PRÓXIMA PUERTA?",
         copy="Cuéntanos tu idea y déjanos asesorarte.",cta="PIDE PRESUPUESTO SIN COMPROMISO"),
]
logo=Image.open(LOGO).convert("RGB")
files=[]
for i,page in enumerate(PAGES,1):
    src=CAND/(page["id"]+".jpg")
    if not src.exists():raise RuntimeError("SOURCE_NOT_FOUND_"+page["id"])
    original=Image.open(src).convert("RGB")
    if original.width<1000:raise RuntimeError("LOW_RES_STOCK_IMAGE")
    focus={1:0.84,2:0.45,3:0.98}[i]
    image=ImageOps.fit(original,(W,1015),method=Image.Resampling.LANCZOS,centering=(0.5,focus))
    image=ImageEnhance.Contrast(image).enhance(1.10)
    image=ImageEnhance.Color(image).enhance(1.04)
    canvas=Image.new("RGB",(W,H),INK);canvas.paste(image,(0,0))
    # Glowing orange art-direction border.
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,W-1,12),fill=ORANGE)
    d.polygon([(0,0),(410,0),(0,410)],fill=(7,10,13))
    d.line([(0,410),(410,0)],fill=ORANGE,width=7)
    # Premium upper-right dark metal plate masks distracting photo signage.
    d.polygon([(748,0),(W,0),(W,242),(884,242)],fill=INK)
    d.line([(748,0),(884,242)],fill=ORANGE,width=5)
    # Darken lower hero gradually to keep text legible.
    layer=Image.new("RGBA",(W,H),(0,0,0,0));ld=ImageDraw.Draw(layer)
    for y in range(520,1016):
        t=(y-520)/496
        alpha=int(240*t*t)
        ld.line((0,y,W,y),fill=(5,8,12,alpha),width=1)
    canvas=Image.alpha_composite(canvas.convert("RGBA"),layer).convert("RGB")
    # Header brand container.
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((45,35,239,237),radius=18,fill=(5,7,11),outline=(255,111,12),width=3)
    embed=ImageOps.contain(logo,(174,174),method=Image.Resampling.LANCZOS)
    canvas.paste(embed,(142-embed.width//2,136-embed.height//2))
    d=ImageDraw.Draw(canvas)
    d.text((821,68),f"0{i} / 03",font=font(34,True),fill=WHITE,stroke_width=1,stroke_fill=INK)
    # Lower photo headlines.
    d.rounded_rectangle((56,690,212,704),radius=6,fill=ORANGE)
    f=fit_text(d,page["line1"],945,85,True)
    text_shadow(d,(58,727),page["line1"],f,WHITE)
    f2=fit_text(d,page["line2"],940,100,True)
    text_shadow(d,(58,817),page["line2"],f2,ORANGE)
    # Branded offer panel.
    d.rectangle((0,1000,W,H),fill=INK)
    d.rectangle((0,998,W,1008),fill=ORANGE)
    d.text((58,1044),page["category"],font=fit_text(d,page["category"],970,38,True),fill=WHITE)
    d.text((58,1109),page["copy"],font=fit_text(d,page["copy"],975,31,False),fill=MUTED)
    # CTA button graphic
    d.rounded_rectangle((56,1181,1023,1263),radius=12,fill=ORANGE)
    ctaf=fit_text(d,page["cta"],845,35,True)
    d.text((83,1204),page["cta"],font=ctaf,fill=WHITE)
    d.text((978,1196),"›",font=font(48,True),fill=WHITE)
    d.text((58,1296),"INFINEX  ·  IDEAS EN HIERRO. SOLUCIONES REALES.",font=fit_text(d,"INFINEX  ·  IDEAS EN HIERRO. SOLUCIONES REALES.",940,25,True),fill=WHITE)
    d.text((58,1325),"Imagen ilustrativa · Pexels",font=font(17),fill=MUTED)
    img_path=OUT/f"0{i}.jpg"
    canvas.save(img_path,"JPEG",quality=92,subsampling=0,optimize=True)
    if img_path.stat().st_size<110000:raise RuntimeError("RENDER_IS_TOO_SMALL")
    files.append(dict(path=img_path.relative_to(BASE).as_posix(),
                      sha256=hashlib.sha256(img_path.read_bytes()).hexdigest(),
                      source_id=page["id"],source_page=page["source_page"]))
    print("RENDER_OK",i,img_path.stat().st_size)
man={"campaign":"INFINEX-PUERTAS-PREMIUM-TRIAL-20261119","theme":"puertas_metalicas",
     "destination":"infinex_2025","license":"https://www.pexels.com/license/",
     "not_actual_infinex_works":True,"logo_sha256":LOGO_SHA,"images":files}
(OUT/"sources.json").write_text(json.dumps(man,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("MANIFEST_OK",len(files))
