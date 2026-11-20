#!/usr/bin/env python3
"""INFINEX strict carousel originality and distinct headings.

Historical Pexels IDs survive deleted posts. Exact JPEG and perceptual hero
fingerprints provide additional protection against resized/re-encoded photos.
Never substitute stock sources automatically when fewer than 3 unique approved
photos remain.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from PIL import Image

REGISTRY = "assets/carousel_photo_registry.json"
LEGACY_HEADLINES = {
    "puertas metalicas", "escaleras a medida",
    "vallas y cerramientos", "soldadura a medida",
}
# Distinct main headlines across *each* slide; each triplet tells a story.
HEADLINE_SETS = {
    "puertas": (
        ("UNA ENTRADA CON ESTILO", "ACABADOS A TU GUSTO", "ESTRENA TU NUEVA PUERTA"),
        ("TU CASA EMPIEZA AQUÍ", "DISEÑOS QUE ENCAJAN", "CUÉNTANOS TU IDEA"),
        ("CAMBIA TU FACHADA", "ELIGE CADA DETALLE", "DAMOS FORMA A TU PUERTA"),
        ("UNA PUERTA ÚNICA", "MEDIDAS PERSONALIZADAS", "PIDE TU PRESUPUESTO"),
    ),
    "escaleras": (
        ("ESCALERAS QUE INSPIRAN", "APROVECHA CADA HUECO", "DISEÑEMOS TU ESCALERA"),
        ("SUBE EL NIVEL DE TU CASA", "TU ESTILO, TUS MEDIDAS", "HAGÁMOSLA REALIDAD"),
        ("TRANSFORMA TU INTERIOR", "ACABADOS A ELEGIR", "TU PROYECTO EMPIEZA HOY"),
        ("UN DISEÑO QUE DESTACA", "ESPACIOS MEJOR PENSADOS", "PIDE TU PROPUESTA"),
    ),
    "cerramientos": (
        ("RENUEVA TU EXTERIOR", "PRIVACIDAD CON DISEÑO", "CREEMOS TU CERRAMIENTO"),
        ("UN JARDÍN CON CARÁCTER", "ELIGE TU ACABADO", "HABLEMOS DE TU VALLA"),
        ("DA FORMA A TU ENTRADA", "SEGURIDAD Y ESTÉTICA", "PIDE TU PRESUPUESTO"),
        ("SEPARA CON ELEGANCIA", "OPCIONES PERSONALIZADAS", "CUÉNTANOS QUÉ BUSCAS"),
    ),
    "soldadura": (
        ("EL HIERRO TIENE SOLUCIÓN", "UNIONES QUE IMPORTAN", "CUÉNTANOS TU PROYECTO"),
        ("DALE VIDA A TU IDEA", "REFUERZOS A MEDIDA", "VAMOS A VALORARLO"),
        ("CREAMOS CON METAL", "CUIDAMOS LOS DETALLES", "PIDE TU PROPUESTA"),
        ("SOLUCIONES DE HIERRO", "CADA PIEZA TIENE UN FIN", "HABLEMOS DE TU IDEA"),
    ),
}

def norm(s: str) -> str:
    v=unicodedata.normalize("NFKD", str(s).casefold())
    v="".join(c for c in v if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+"," ",v).strip()

def headings_for(theme:str,edition:int)->tuple[str,str,str]:
    sets=HEADLINE_SETS.get(theme)
    if not sets or edition<0:raise RuntimeError("EDITORIAL_HEADLINE_TOPIC_UNKNOWN")
    selected=sets[(edition//4)%len(sets)]
    validate_headings(selected)
    return selected

def validate_headings(titles):
    if not isinstance(titles,(list,tuple)) or len(titles)!=3:
        raise RuntimeError("EDITORIAL_REQUIRES_THREE_MAIN_HEADLINES")
    normalized=[norm(s) for s in titles]
    if len(set(normalized))!=3 or not all(len(s)>9 for s in normalized):
        raise RuntimeError("EDITORIAL_DUPLICATE_OR_GENERIC_HEADLINES")
    if any(h in LEGACY_HEADLINES for h in normalized):
        raise RuntimeError("EDITORIAL_OLD_REPEATED_HEADING_FORBIDDEN")

def manifest_paths(base:Path,exclude:Path|None=None):
    paths=list((base/"assets"/"daily").glob("*/*/sources.json"))
    paths+=list((base/"assets"/"campaigns").glob("*/sources.json"))
    excluded=exclude.resolve() if exclude else None
    return [p for p in paths if not excluded or p.resolve()!=excluded]

def gather_history(base:Path, exclude:Path|None=None):
    source_ids=set()
    title_set=set()
    pictures=[]
    for p in manifest_paths(base,exclude):
        try: m=json.loads(p.read_text(encoding="utf-8-sig"))
        except (ValueError,UnicodeError) as exc:
            raise RuntimeError("EDITORIAL_HISTORIC_MANIFEST_INVALID") from exc
        for item in m.get("sources",[]):
            if item.get("id") is not None:source_ids.add(str(item["id"]))
        for item in m.get("images",[]):
            if item.get("source_id") is not None:source_ids.add(str(item["source_id"]))
            name=item.get("path")
            if name and (base/name).is_file():
                pictures.append(base/name)
        for h in m.get("titles",[]):
            title_set.add(norm(h))
    # 18 November's first two historical carousel assets predate manifest use.
    pictures.extend((base/"assets/2026-11-18").glob("*.jpg"))
    pictures.extend((base/"assets/2026-11-18/visual-b").glob("*.jpg"))
    return source_ids,title_set,pictures

def source_signature(image:Image.Image)->str:
    """64-bit difference hash of the hero area excluding logo and lower copy."""
    im=image.convert("RGB")
    w,h=im.size
    crop=im.crop((int(.28*w),int(.29*h),int(.89*w),int(.57*h)))
    gray=crop.convert("L").resize((9,8),Image.Resampling.LANCZOS)
    values=list(gray.getdata())
    bits=0
    for y in range(8):
        for x in range(8):
            bits=(bits<<1)|int(values[y*9+x]>values[y*9+x+1])
    return f"{bits:016x}"

def hamming(a:str,b:str)->int:
    return (int(a,16)^int(b,16)).bit_count()

def file_image_signature(path:Path)->str:
    with Image.open(path) as image:
        return source_signature(image)

def _read_registry(base:Path):
    p=base/REGISTRY
    if not p.is_file():raise RuntimeError("INFINEX_PHOTO_REGISTRY_MISSING")
    data=json.loads(p.read_text(encoding="utf-8-sig"))
    if data.get("schema")!=1 or not isinstance(data.get("entries"),list):
        raise RuntimeError("INFINEX_PHOTO_REGISTRY_INVALID")
    return data

def _remote_registry(base:Path):
    # The repo checkout may predate another publication: always read remote.
    for args in (["git","fetch","--quiet","origin","main"],
                 ["git","show","origin/main:"+REGISTRY]):
        p=subprocess.run(args,cwd=base,capture_output=True,text=True,timeout=40)
        if p.returncode!=0:
            raise RuntimeError("INFINEX_PHOTO_REGISTRY_REMOTE_UNAVAILABLE")
        if args[1]=="show":
            try:return json.loads(p.stdout)
            except ValueError:raise RuntimeError("INFINEX_PHOTO_REMOTE_REGISTRY_INVALID")
    raise RuntimeError("INFINEX_PHOTO_REMOTE_REGISTRY_UNAVAILABLE")

def used_photos(base:Path, exclude:Path|None=None,remote:bool=False):
    historic,titles,paths=gather_history(base,exclude)
    info=_read_registry(base)
    registries=[info]
    if remote:registries.append(_remote_registry(base))
    hashes=set()
    fingerprints=set()
    for registry in registries:
        for e in registry["entries"]:
            historic.update(str(x) for x in e.get("source_ids",[]))
            titles.update(norm(x) for x in e.get("titles",[]))
            hashes.update(x for x in e.get("image_sha256",[]) if x)
            fingerprints.update(x for x in e.get("hero_dhash",[]) if x)
    for file in paths:
        if file.is_file():
            hashes.add(hashlib.sha256(file.read_bytes()).hexdigest())
            fingerprints.add(file_image_signature(file))
    return historic,titles,hashes,fingerprints

def ensure_unique(base:Path,manifest:dict,exclude:Path|None=None,remote:bool=False):
    if len(manifest.get("sources",[]))!=3 or len(manifest.get("images",[]))!=3:
        raise RuntimeError("EDITORIAL_THREE_IMAGES_REQUIRED")
    titles=manifest.get("titles",[])
    validate_headings(titles)
    ids=[str(x.get("id","")) for x in manifest["sources"]]
    if any(not x for x in ids) or len(set(ids))!=3:
        raise RuntimeError("EDITORIAL_DUPLICATE_PHOTO_SOURCE_IN_CAROUSEL")
    current_ids,prior_titles,known_sha,known_dhash=used_photos(base,exclude,remote)
    if set(ids)&current_ids:raise RuntimeError("EDITORIAL_PHOTO_ALREADY_USED_PEXELS_ID")
    if set(map(norm,titles))&prior_titles:raise RuntimeError("EDITORIAL_MAIN_HEADLINE_ALREADY_USED")
    new_hashes=[]
    new_perceptual=[]
    for info in manifest["images"]:
        path=base/info["path"]
        if not path.is_file():raise RuntimeError("EDITORIAL_IMAGE_MISSING")
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=info["sha256"]:raise RuntimeError("EDITORIAL_IMAGE_HASH_CHANGED")
        fingerprint=file_image_signature(path)
        if sha in known_sha or sha in new_hashes:
            raise RuntimeError("EDITORIAL_IDENTICAL_IMAGE_REUSED")
        if any(hamming(fingerprint,old)<=3 for old in [*known_dhash,*new_perceptual]):
            raise RuntimeError("EDITORIAL_NEAR_IDENTICAL_IMAGE_REUSED")
        new_hashes.append(sha)
        new_perceptual.append(fingerprint)
    return new_hashes,new_perceptual

def reserve(base:Path,manifest:dict,day:str,slot:str,exclude:Path):
    sha,perceptual=ensure_unique(base,manifest,exclude=exclude,remote=True)
    item={"key":day+"_"+slot,"source_ids":[str(x["id"]) for x in manifest["sources"]],
          "image_sha256":sha,"hero_dhash":perceptual,
          "titles":manifest["titles"],"status":"RESERVED_NO_REUSE"}
    registry=_read_registry(base)
    if any(e.get("key")==item["key"] for e in registry["entries"]):
        raise RuntimeError("EDITORIAL_SLOT_ALREADY_RESERVED")
    registry["entries"].append(item)
    path=base/REGISTRY
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,path)
    return item

def confirmed_reserved(base:Path,day:str,slot:str,manifest:dict):
    remote=_remote_registry(base)
    for item in remote.get("entries",[]):
        if item.get("key")==day+"_"+slot:
            if ([str(x["id"]) for x in manifest["sources"]]==item.get("source_ids") and
                [x["sha256"] for x in manifest["images"]]==item.get("image_sha256") and
                manifest.get("titles")==item.get("titles")):
                return True
            raise RuntimeError("EDITORIAL_PHOTO_RESERVATION_MISMATCH")
    raise RuntimeError("EDITORIAL_PHOTO_RESERVATION_NOT_ON_REMOTE")
