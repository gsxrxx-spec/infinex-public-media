#!/usr/bin/env python3
"""INFINEX new *offline* corrected gate demo; NEVER posts to Instagram.

Uses the already-published photograph only for a non-public regression test.
The old source is NEVER eligible to be published in another post.
"""
from pathlib import Path
from PIL import Image
import sys
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"scripts"))
from infinex_gate_geometry_qa import validate_fit,draw_fitted_gate,sha
from infinex_prepare_before_after import slide,PLANS

source=BASE/"assets/before_after/2026-11-22_09_puertas/original.jpg"
photo=Image.open(source).convert("RGB")
site={
  "left_support_top":455,"left_support_bottom":455,
  "right_support_top":1649,"right_support_bottom":1650,
  "gate_left_top":457,"gate_left_bottom":459,
  "gate_right_top":1647,"gate_right_bottom":1648,
  "gate_top_y":691,"gate_bottom_y":1077,"threshold_y":1088,
  "support_type_left":"masonry_pillar","support_type_right":"masonry_pillar",
  "supports_visible":True,"perspective_checked":True,
  "ground_contact_checked":True,
  "architectural_source_notes":"Left and right stone entrance pillars visibly border the foreground driveway; drainage threshold is located at their feet."
}
# Old visual error: gate used to stop far short of the right pier and float above ground.
bad={**site,"gate_left_top":410,"gate_left_bottom":410,
     "gate_right_top":1494,"gate_right_bottom":1494,
     "gate_bottom_y":990}
try:
    validate_fit(bad,photo.size)
    raise AssertionError("OLD_FLOATING_GATE_WRONGLY_APPROVED")
except RuntimeError as err:
    assert "INFINEX_GATE" in str(err)
    print("PREVIOUS_PUBLICATION_ERROR_DETECTED",str(err))
assert validate_fit(site,photo.size)
new=draw_fitted_gate(photo,site)
trial=BASE/"assets/candidates/gate_fit_regression_2026-11-22"
trial.mkdir(parents=True,exist_ok=True)
new.save(trial/"corrected_installation_scene.jpg",quality=94,subsampling=0)
slide(new,"after",PLANS["2026-11-22"],trial/"02_DESPUES_CORREGIDO_SOLO_PRUEBA.jpg")
slide(photo,"before",PLANS["2026-11-22"],trial/"01_ANTES_SOLO_PRUEBA.jpg")
print("NEW_GATE_TEST_RAN_OFFLINE_NO_INSTAGRAM_POST",str(trial))
print("FIT_QA_PASS_PILLARS_CONNECTED_THRESHOLD_ALIGNED",sha(trial/"02_DESPUES_CORREGIDO_SOLO_PRUEBA.jpg"))
