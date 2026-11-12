"""Un appareil désormais sur une prise mesurée (« Mesuré par une prise ») n'est plus cherché sur la courbe :
ni proposé (« Micro-ondes ? »), ni rangé ; son historique reste. Pareil pour un appareil d'une prise partagée.

Lancer :  python tests/test_mesure_prise.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from ha_stub import C, make  # noqa: E402
import test_tracking as TT  # noqa: E402
import test_scenarios as S  # noqa: E402

ok_all = True
real_time = C.time.time


def check(label, cond, detail=""):
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK    ' if cond else 'ÉCHEC '}{label} {detail}")


def dishwasher():
    """Le scénario de test_coordinator : un lave-vaisselle suivi, un thé et un café pendant ses pauses."""
    ts3, ps3, _ = TT.build([("lv", "lv_long", 3600), ("the", "bouilloire", 5400), ("cafe", "cafe", 7200),
                            ("the2", "bouilloire", 12000)], 7)
    co3 = make()
    cut = S.T0 + 3600 + 240
    C.time.time = lambda: cut
    co3.store.add_samples([(t, p, 0) for t, p in zip(ts3, ps3) if t <= cut])
    co3.processed_until = ts3[0]
    co3._process()
    part = next(x for x in co3.running_parts if abs(x["p"] - 2000) < 400)
    co3._action({"action": "label_now", "name": "Lave-vaisselle", "at": part["start"], "p": part["p"]})
    for minute in range(5, 300):
        now = S.T0 + 3600 + minute * 60
        C.time.time = lambda now=now: now
        co3.store.add_samples([(t, p, 0) for t, p in zip(ts3, ps3) if now - 60 < t <= now])
        co3._process()
    return co3


def check(label, cond, detail=""):
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK    ' if cond else 'ÉCHEC '}{label} {detail}")


co = dishwasher()
gid = next(g for g, x in co.groups.items() if x.get("name") == "Lave-vaisselle")
n_before = sum(1 for e in co.evs if e.gid == gid)
lone = next(e for e in co.evs if e.gid == gid)
check("Avant : le lave-vaisselle est cherché sur la courbe", gid in co.cents)
co._action({"action": "measured", "gid": gid, "on": True})
check("« Mesuré par une prise » : il n'est plus cherché ni proposé", gid not in co.cents
      and "Lave-vaisselle" not in co._guess_names(type(lone)(999, lone.f)))
check("… son historique reste", sum(1 for e in co.evs if e.gid == gid) == n_before)
co._action({"action": "measured", "gid": gid, "on": False})
check("« Plus sur une prise » : il est de nouveau cherché", gid in co.cents)
co.shared = C.SharedPlugs([{"entity": "sensor.prise", "names": ["Lave-vaisselle", "Lave-linge"]}])
co._recompute()
check("Un appareil d'une prise partagée n'est pas cherché sur la courbe", gid not in co.cents)
C.time.time = real_time

print("\nTout est bon" if ok_all else "\nIl y a des échecs")
sys.exit(0 if ok_all else 1)
