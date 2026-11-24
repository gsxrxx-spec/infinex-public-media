#!/usr/bin/env python3
"""Propuesta inédita 24/11: sustituir puerta envejecida por cerramiento moderno.

El montaje se construye EN LA MISMA FOTO (Pexels 37164155), con lados
anclados a ambos pilares de piedra y el pie sobre el umbral existente.
No modifica ni reutiliza la publicación rechazada del 22/11.
"""
from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw,ImageEnhance,ImageFilter
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"scripts"))
from infinex_prepare_before_after import slide,LOGO,LOGO_SHA
from infinex_gate_geometry_qa import validate_fit

DATE="2026-11-24"
PHOTO_ID=37164155
TOPIC="puertas"
src=BASE/"assets/candidates/gates_for_repair/37164155.jpg"
dest=BASE/"assets/before_after/2026-11-24_09_puertas"
dest.mkdir(parents=True,exist_ok=True)
original=Image.open(src).convert("RGB")
if original.width<1500 or original.height<900:raise RuntimeError("PHOTO_TOO_SMALL")
if hashlib.sha256(LOGO.read_bytes()).hexdigest()!=LOGO_SHA:raise RuntimeError("LOGO_INVALID")
photo=dest/"original.jpg"
if not photo.exists():photo.write_bytes(src.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if sha(photo)!=sha(src):raise RuntimeError("PHOTO_MISMATCH")
W,H=original.size
# The stone pillars bound x=330..967, the existing wooden gate top=440
# and bottom=819; gate replacement has 1 cm-ish clearance to threshold.
site={
 "left_support_top":333,"left_support_bottom":332,
 "right_support_top":969,"right_support_bottom":966,
 "gate_left_top":335,"gate_left_bottom":334,
 "gate_right_top":967,"gate_right_bottom":964,
 "gate_top_y":439,"gate_bottom_y":814,"threshold_y":824,
 "support_type_left":"masonry_pillar","support_type_right":"masonry_pillar",
 "supports_visible":True,"perspective_checked":True,"ground_contact_checked":True,
 "architectural_source_notes":"Both old stone gate piers are clearly visible and extend down to the gravel threshold; the original weathered wood gate occupies the identical span."
}
assert validate_fit(site,original.size)
enhanced=ImageEnhance.Color(original).enhance(1.055)
after=enhanced.convert("RGBA")
plane=Image.new("RGBA",after.size,(0,0,0,0))
d=ImageDraw.Draw(plane)
x0,y0,x1,y1=site["gate_left_top"],site["gate_top_y"],site["gate_right_top"],site["gate_bottom_y"]
# A FULLY OPAQUE replacement panel hides old wooden slats. No remnants
# are visible between new metal slats, as would happen with an overlay.
outer=(12,17,20,255)
steel=(31,38,42,255)
rim=(72,82,86,255)
light=(90,101,105,255)
d.rectangle((x0,y0,x1,y1),fill=outer)
# Two filled steel leaves, solid inside - their black horizontal stripes
# are pressed reliefs, not holes, so original wood never shows through.
gap=9
center=(x0+x1)//2
d.rectangle((x0+14,y0+14,center-gap,y1-12),fill=steel)
d.rectangle((center+gap,y0+14,x1-14,y1-12),fill=steel)
for yy in range(y0+31,y1-26,30):
    for left,right in ((x0+15,center-gap-1),(center+gap+1,x1-15)):
        d.rectangle((left,yy,right,yy+4),fill=(74,85,89,255))
        d.line((left,yy+5,right,yy+5),fill=(9,12,14,255),width=3)
# Top / lower frame, central meeting post.
d.rectangle((x0,y0,x1,y0+12),fill=outer)
d.rectangle((x0,y1-13,x1,y1),fill=outer)
d.rectangle((center-7,y0,center+7,y1),fill=(7,11,13,255))
d.line((x0+7,y0+5,x1-7,y0+5),fill=rim,width=2)
d.line((center-4,y0+7,center-4,y1-6),fill=light,width=2)
# External hinges bolt both leaves to existing masonry piers.
for wall_x in (x0,x1):
    for yy in (y0+78,y1-70):
        d.rounded_rectangle((wall_x-13,yy-15,wall_x+13,yy+15),
                            radius=3,fill=(10,13,15,255),outline=(111,121,123,255),width=2)
        for p in (-7,7):
            d.ellipse((wall_x-2,yy+p-2,wall_x+3,yy+p+3),fill=(167,170,168,255))
# Single handle and key cylinder at realistic waist height.
handle_y=y0+198
d.rounded_rectangle((center+24,handle_y-25,center+35,handle_y+17),
                    radius=3,fill=(177,184,182,255),outline=(51,57,57,255),width=2)
d.ellipse((center+26,handle_y+33,center+34,handle_y+41),fill=(165,172,169,255))
# Tiny foot-clearance shadow at the driveway, within natural threshold.
shadow=Image.new("RGBA",after.size,(0,0,0,0))
sd=ImageDraw.Draw(shadow)
sd.polygon([(x0,y1+2),(x1,y1+2),(x1+9,y1+10),(x0+8,y1+10)],fill=(3,6,8,103))
shadow=shadow.filter(ImageFilter.GaussianBlur(3))
after=Image.alpha_composite(after,shadow)
after=Image.alpha_composite(after,plane).convert("RGB")
plan={
 "title":"UNA PUERTA QUE PIDE CAMBIO",
 "before_detail":"Puerta de madera con desgaste y deterioro.",
 "after_title":"UN ACCESO MODERNO Y SEGURO",
 "after_detail":"Diseño ilustrativo de doble hoja metálica",
}
before_path=dest/"01_antes.jpg"
after_path=dest/"02_despues.jpg"
slide(original,"before",plan,before_path)
slide(after,"after",plan,after_path)
manifest={
 "date":DATE,"slot":"09","time_local":"09:30","type":"BEFORE_AFTER",
 "topic":TOPIC,"scene_key":"pexels:"+str(PHOTO_ID),
 "illustrative_simulation":True,"not_actual_infinex_works":True,
 "description":"Ejemplo digital de renovación de puerta antigua a hojas modernas, sin obra real",
 "source_page":"https://www.pexels.com/photo/rustic-wooden-gate-in-lush-green-landscape-37164155/",
 "source_author":"Colaborador de Pexels",
 "source_license":"https://www.pexels.com/license/",
 "source_image":photo.relative_to(BASE).as_posix(),
 "source_sha256":sha(photo),"logo_sha256":LOGO_SHA,
 "titles":[plan["title"],plan["after_title"]],
 "images":[{"path":before_path.relative_to(BASE).as_posix(),"sha256":sha(before_path)},
           {"path":after_path.relative_to(BASE).as_posix(),"sha256":sha(after_path)}],
 "geometry_annotation":site,
 "visual_review":{"status":"PENDING","render_sha256":sha(after_path)},
 "approved_for_publish":False
}
manifest_path=dest/"sources.json"
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("INFINEX_NEW_BEFORE_AFTER_DRAFT_NEW_SOURCE",DATE,PHOTO_ID,"SHA",sha(after_path))
