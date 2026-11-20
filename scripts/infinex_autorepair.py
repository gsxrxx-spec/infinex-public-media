#!/usr/bin/env python3
"""INFINEX editorial auto-repair: try better assets/copy before refusing a slot.

The publisher may change to another INFINEX service if the requested theme
has no genuinely new verified photographs. It NEVER weakens rights/uniqueness
or assumes unknown stock is safe.
"""
from __future__ import annotations
import itertools
from typing import Iterable
from infinex_carousel_quality import headings_for, validate_headings, norm
THEME_ORDER=("puertas","escaleras","cerramientos","soldadura")
HEADLINES={
 "puertas":(
   ("TRANSFORMA TU ENTRADA","TU PUERTA, TU ESTILO","UN ACCESO QUE ENAMORA","DALE ESTILO A TU CASA","ENTRA CON PERSONALIDAD","TU FACHADA MERECE MÁS"),
   ("ACABADOS PARA ELEGIR","SEGURIDAD CON DISEÑO","MEDIDAS A TU GUSTO","DETALLES QUE MARCAN","OPCIONES PARA TU ESPACIO","PERSONALIZA CADA DETALLE"),
   ("DISEÑAMOS TU PUERTA","DA EL PRIMER PASO","PIDE UNA PROPUESTA","HABLEMOS DE TU ENTRADA","ESTRENA TU DISEÑO","HAZ REALIDAD TU IDEA")
 ),
 "escaleras":(
   ("ESCALERAS QUE DESTACAN","TU ESPACIO PUEDE MÁS","SUBE CON ESTILO","OTRA FORMA DE SUBIR","TU CASA, OTRO NIVEL","UN INTERIOR DIFERENTE"),
   ("CADA HUECO CUENTA","ACABADOS CON CARÁCTER","TRAZADOS A TU MEDIDA","DISEÑO Y FUNCIONALIDAD","BARANDILLAS A ELEGIR","APROVECHA EL ESPACIO"),
   ("TU ESCALERA IDEAL","DISEÑEMOS CADA TRAMO","PIDE TU PROPUESTA","CREAMOS TU RECORRIDO","CUÉNTANOS TU IDEA","HABLEMOS DE MEDIDAS")
 ),
 "cerramientos":(
   ("TU EXTERIOR SE TRANSFORMA","DA CARÁCTER AL JARDÍN","UN ACCESO DISTINTO","MÁS ESTILO FUERA","DA VIDA A TU VALLA","OTRA ENTRADA ES POSIBLE"),
   ("PRIVACIDAD A TU MEDIDA","DETALLES A TU GUSTO","ESTILO Y PROTECCIÓN","ACABADOS QUE ENCAJAN","LA ALTURA QUE NECESITAS","MATERIALES PARA ELEGIR"),
   ("HABLEMOS DE TU VALLA","DEFINE TU CERRAMIENTO","PIDE TU PROPUESTA","EMPECEMOS TU PROYECTO","CUÉNTANOS TU EXTERIOR","LO DISEÑAMOS CONTIGO")
 ),
 "soldadura":(
   ("EL METAL TIENE FUTURO","CREAMOS CON PRECISIÓN","DAR FORMA A TUS IDEAS","EL HIERRO SE TRANSFORMA","SOLUCIONES DE METAL","DA UNA SEGUNDA VIDA"),
   ("UNIONES BIEN PENSADAS","DETALLES QUE IMPORTAN","REFUERZOS A MEDIDA","REPARACIONES METÁLICAS","TRABAJOS CON ACABADO","MÁS FUNCIONALIDAD"),
   ("HABLEMOS DE TU PIEZA","CUÉNTANOS EL PROBLEMA","PIDENOS UNA PROPUESTA","VALOREMOS TU PROYECTO","TE AYUDAMOS A DECIDIR","EMPECEMOS POR TU IDEA")
 )
}
def alternate_topics(intended:str,previous:str|None):
    if intended not in THEME_ORDER:raise RuntimeError("INFINEX_EDITORIAL_BAD_THEME")
    i=THEME_ORDER.index(intended)
    return [x for x in [*THEME_ORDER[i:],*THEME_ORDER[:i]] if x!=previous]

def unique_headlines(theme:str,edition:int,prior_titles:Iterable[str]):
    seen={norm(s) for s in prior_titles}
    # Start with the already-designed premium variants before any new copy.
    for k in range(4):
        titles=headings_for(theme,edition+4*k)
        if all(norm(s) not in seen for s in titles):
            return titles
    blocks=HEADLINES[theme]
    for idx in range(6**3):
        titles=tuple(blocks[i][(idx//(6**i))%6] for i in range(3))
        if any(norm(s) in seen for s in titles):continue
        validate_headings(titles)
        return titles
    raise RuntimeError("INFINEX_EDITORIAL_ALL_COPY_VARIANTS_USED")
