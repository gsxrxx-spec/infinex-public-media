import sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import infinex_daily as d
m={"topic":"escaleras","images":[{"sha256":str(i)*64} for i in (1,2,3)]}
def reject(x):
    try:d.require_product_visual_review(x)
    except RuntimeError:return
    raise AssertionError("unreviewed or wrong product accepted")
reject(m)
m["visual_review"]={"status":"APPROVED_BY_SYSTEM_VISUAL_REVIEW","policy_version":d.VISUAL_POLICY_VERSION,"topic":"escaleras","logo_sha256":d.LOGO_SHA256,"sha256":[x["sha256"] for x in m["images"]],"slides":[{"sha256":x["sha256"],"decision":"APPROVED","metal_product_is_main_subject":True,"matches_exact_service":True,"finished_attractive_realistic":True,"no_unrelated_or_deteriorated_scene":True,"visible_product_reason":"synthetic test only","metal_structure_and_treads":True} for x in m["images"]]}
assert d.require_product_visual_review(m)
for key in ("metal_structure_and_treads","matches_exact_service","finished_attractive_realistic"):
    bad=copy.deepcopy(m);bad["visual_review"]["slides"][1][key]=False;reject(bad)
bad=copy.deepcopy(m);bad["images"][0]["sha256"]="f"*64;reject(bad)
print("PRODUCT_VISUAL_GUARD_TESTS_OK")
