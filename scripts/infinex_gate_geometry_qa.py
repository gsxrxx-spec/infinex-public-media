#!/usr/bin/env python3
"""INFINEX strict gate geometry and site-fit QA.

A dark bar across a photo is NOT an installed gate. Both edges must join actual
structural supports and the gate's feet must be at the entrance threshold.
Coordinates are explicitly annotated on the *original source photograph*.
A human visual review remains mandatory: numeric checks cannot infer all
architectural details or replace inspection of the final render.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFilter
import hashlib
from pathlib import Path

def validate_fit(spec:dict, image_size:tuple[int,int], require_final_review=False):
    required=("left_support_top","left_support_bottom","right_support_top","right_support_bottom",
              "gate_left_top","gate_left_bottom","gate_right_top","gate_right_bottom",
              "gate_top_y","gate_bottom_y","threshold_y","support_type_left","support_type_right",
              "supports_visible","perspective_checked","ground_contact_checked",
              "architectural_source_notes")
    missing=[k for k in required if k not in spec]
    if missing:raise RuntimeError("INFINEX_GATE_FIT_ANNOTATION_MISSING:"+",".join(missing))
    w,h=image_size
    xs=[spec[k] for k in required if k in
        ("left_support_top","left_support_bottom","right_support_top","right_support_bottom",
         "gate_left_top","gate_left_bottom","gate_right_top","gate_right_bottom")]
    for x in xs:
        if type(x) not in (int,float) or not 0<=x<w:
            raise RuntimeError("INFINEX_GATE_FIT_INVALID_X")
    top,bottom,ground=(spec[k] for k in ("gate_top_y","gate_bottom_y","threshold_y"))
    if any(type(v) not in (int,float) for v in (top,bottom,ground)):
        raise RuntimeError("INFINEX_GATE_FIT_INVALID_Y")
    if not (0<=top<bottom<ground<h and ground-bottom<=22):
        raise RuntimeError("INFINEX_GATE_FLOATS_ABOVE_THRESHOLD_OR_WRONG_HEIGHT")
    for side in ("left","right"):
        for level in ("top","bottom"):
            xg=spec[f"gate_{side}_{level}"]
            xsup=spec[f"{side}_support_{level}"]
            if abs(xg-xsup)>14:
                raise RuntimeError("INFINEX_GATE_EDGE_NOT_ATTACHED_TO_"+side.upper()+"_PILLAR")
    left=(spec["gate_left_top"],spec["gate_left_bottom"])
    right=(spec["gate_right_top"],spec["gate_right_bottom"])
    widths=[r-l for l,r in zip(left,right)]
    if min(widths)<210 or max(widths)>w*.95:
        raise RuntimeError("INFINEX_GATE_BAD_OPENING_WIDTH")
    if not (0.65<widths[0]/widths[1]<1.45):
        raise RuntimeError("INFINEX_GATE_PERSPECTIVE_INCONSISTENT")
    if any(abs(xl-y)>80 for xl,y in zip(left,right)):
        pass
    if (spec.get("supports_visible") is not True or
        spec.get("perspective_checked") is not True or
        spec.get("ground_contact_checked") is not True or
        spec.get("support_type_left") not in ("masonry_pillar","steel_post","concrete_wall") or
        spec.get("support_type_right") not in ("masonry_pillar","steel_post","concrete_wall")):
        raise RuntimeError("INFINEX_GATE_NO_TWO_VISIBLE_REAL_SUPPORTS")
    if len(str(spec.get("architectural_source_notes","")).strip())<30:
        raise RuntimeError("INFINEX_GATE_SUPPORT_VISUAL_JUSTIFICATION_MISSING")
    if require_final_review:
        review=spec.get("final_render_visual_review",{})
        if (review.get("status")!="PASS" or
            len(str(review.get("render_sha256","")))!=64 or
            not review.get("reviewed_at") or
            not review.get("verified_pillar_alignment") or
            not review.get("verified_no_floating") or
            not review.get("verified_correct_scale") or
            not review.get("verified_realistic_perspective")):
            raise RuntimeError("INFINEX_GATE_FINAL_VISUAL_QA_REQUIRED")
    return True

def draw_fitted_gate(photo:Image.Image,spec:dict)->Image.Image:
    """A two-leaf gate hinged between actual opening walls, no floating box."""
    validate_fit(spec,photo.size)
    original=photo.convert("RGBA")
    layer=Image.new("RGBA",original.size,(0,0,0,0))
    draw=ImageDraw.Draw(layer)
    top,bottom=spec["gate_top_y"],spec["gate_bottom_y"]
    def edge(side,y):
        r=(y-top)/(bottom-top)
        a=spec[f"gate_{side}_top"];b=spec[f"gate_{side}_bottom"]
        return int(round(a+(b-a)*r))
    # Ground-level shadow: short and physically attached to the gate base.
    shadow=Image.new("RGBA",original.size,(0,0,0,0))
    sd=ImageDraw.Draw(shadow)
    sx0,sx1=edge("left",bottom),edge("right",bottom)
    sd.polygon([(sx0+3,bottom),(sx1+4,bottom),
                (sx1+16,min(bottom+18,original.height-1)),
                (sx0+14,min(bottom+18,original.height-1))],fill=(4,6,9,104))
    original=Image.alpha_composite(original,shadow.filter(ImageFilter.GaussianBlur(7)))
    main=(22,27,30,255);panel=(27,34,37,250);highlight=(71,81,83,245)
    inner=(8,11,13,255)
    # Panel frame, exactly inside the two existing stone supports.
    lt=(edge("left",top),top);lb=(edge("left",bottom),bottom)
    rt=(edge("right",top),top);rb=(edge("right",bottom),bottom)
    draw.polygon([lt,rt,rb,lb],outline=main,width=15)
    # Physical dual-leaf arrangement; equal slat spacing and true opening seam.
    def middle(y):
        return int(edge("left",y)*.50+edge("right",y)*.50)
    draw.line((middle(top),top+5,middle(bottom),bottom-5),fill=(3,6,8,255),width=17)
    draw.line((middle(top)+3,top+6,middle(bottom)+3,bottom-6),fill=highlight,width=2)
    for y in range(int(top+23),int(bottom-13),31):
        slat_height=19
        for leaf in (0,1):
            left=edge("left",y)+17 if leaf==0 else middle(y)+10
            right=middle(y)-10 if leaf==0 else edge("right",y)-17
            if right<=left+10:continue
            draw.rectangle((left,y,right,y+slat_height),fill=panel)
            draw.line((left+1,y+2,right-1,y+2),fill=highlight,width=3)
            draw.line((left+1,y+slat_height,right-1,y+slat_height),fill=inner,width=2)
    # Top and bottom longitudinal bars.
    draw.line((lt[0]+2,top+12,rt[0]-3,top+12),fill=(82,89,89,255),width=3)
    draw.line((lb[0]+5,bottom-14,rb[0]-5,bottom-14),fill=main,width=14)
    # Hinge brackets visibly connect gate leaves to masonry piers.
    for side in ("left","right"):
        for y in (int(top+(bottom-top)*.25),int(top+(bottom-top)*.75)):
            x=edge(side,y)
            inner_offset=10 if side=="left" else -10
            draw.rounded_rectangle((x-11,y-15,x+11,y+15),radius=4,
                                  fill=(10,14,17,255),outline=(112,119,122,255),width=2)
            for dy in (-7,7):
                draw.ellipse((x-3,y+dy-2,x+3,y+dy+3),fill=(159,165,162,255))
            draw.rectangle((min(x,x+inner_offset),y-7,max(x,x+inner_offset),y+7),
                           fill=(34,41,44,255))
    seam=middle(top)
    # Accessible handle and a cylinder on the right leaf at realistic mid height.
    handle_y=int(top+(bottom-top)*.53)
    draw.rounded_rectangle((seam+24,handle_y-27,seam+38,handle_y+31),radius=4,
                           fill=(165,171,170,255),outline=(57,63,62,255),width=2)
    draw.ellipse((seam+27,handle_y+45,seam+37,handle_y+55),fill=(152,159,158,255))
    # Bottom gate edge is within centimeters of the tiled threshold by guard.
    return Image.alpha_composite(original,layer).convert("RGB")

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
