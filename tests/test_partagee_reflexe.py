"""Une prise partagée qui démarre est relue tout de suite (sans attendre la minute suivante), une seule fois.

Lancer :  python tests/test_partagee_reflexe.py
"""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from ha_stub import C, make  # noqa: E402

ok_all = True


def check(label, cond, detail=""):
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK    ' if cond else 'ÉCHEC '}{label} {detail}")


co = make()
co.shared = C.SharedPlugs([{"entity": "sensor.prise_linge", "names": ["Lave-linge", "Sèche-linge"]}])
tasks = []
co.hass = types.SimpleNamespace(async_create_task=lambda c: (tasks.append(c), c.close()))


def ev(eid, w):
    return types.SimpleNamespace(data={"entity_id": eid, "new_state": types.SimpleNamespace(state=str(w))})


co.sub_now["sensor.prise_linge"] = 0.0
co._on_measured(ev("sensor.prise_linge", 45))
check("La prise démarre : relue tout de suite", len(tasks) == 1)
co._on_measured(ev("sensor.prise_linge", 3))
co._on_measured(ev("sensor.prise_linge", 50))
check("… pas une deuxième fois juste après (le tambour s'arrête et repart)", len(tasks) == 1)
co.shared.open["sensor.prise_linge"] = {"start": 0, "guess": "Lave-linge", "conf": 0.9}
co._shared_kick = 0
co._on_measured(ev("sensor.prise_linge", 3))
co._on_measured(ev("sensor.prise_linge", 50))
check("… ni pendant le programme (il est déjà suivi)", len(tasks) == 1)
co.sub_now["sensor.pc"] = 0.0
co._on_measured(ev("sensor.pc", 200))
check("Une prise mesurée ordinaire ne déclenche rien", len(tasks) == 1)

print("\nTout est bon" if ok_all else "\nIl y a des échecs")
sys.exit(0 if ok_all else 1)
