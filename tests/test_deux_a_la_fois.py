"""Un appareil ne tourne pas deux fois à la fois, et un appareil sur une prise n'est plus cherché sur la courbe.

- Deux utilisations rangées « Four » qui se chevauchent alors que le compteur montre bien deux consommations : celle
  qui n'est pas confirmée perd ce nom (elle redevient à trier) ; une utilisation confirmée n'est jamais changée.
- Un appareil désormais sur une prise (micro-ondes, lave-linge…) n'est plus rangé par aucun moyen.

Lancer :  python tests/test_deux_a_la_fois.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from ha_stub import C, E, make  # noqa: E402

ok_all = True


def check(label, cond, detail=""):
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK    ' if cond else 'ÉCHEC '}{label} {detail}")


def scene(pinned_b):
    co = make()
    co.groups = {"g1": {"id": "g1", "name": "Four", "status": "nomme"}, "g2": {"id": "g2", "name": "Plaques de cuisson", "status": "nomme"}}
    t0, step = 1_800_000_000, E.STEP
    a = co.store.add_event(t0, t0 + 1800, 300, [2200] * (1800 // step), E.features([2200] * (1800 // step), 13))
    b = co.store.add_event(t0 + 900, t0 + 2400, 300, [1500] * (1500 // step), E.features([1500] * (1500 // step), 13))
    # le compteur : 2 200 W, puis 3 700 W pendant le chevauchement (les deux pour de vrai), puis 1 500 W
    co.store.add_samples([(t0 + k * step, 300 + (2200 if k * step < 1800 else 0) + (1500 if 900 <= k * step < 2400 else 0), 0)
                          for k in range(2400 // step)])
    co._load()
    ea, eb = (next(e for e in co.evs if e.id == i) for i in (a, b))
    ea.gid, eb.gid, ea.pinned, eb.pinned = "g1", "g1", True, pinned_b
    co._dedupe_overlaps(list(co.evs))
    return co, ea, eb


co, ea, eb = scene(False)
check("Deux « Four » en même temps (pour de vrai) : celui pas confirmé redevient à trier", ea.gid == "g1" and eb.gid is None
      and "g1" in eb.excluded, f"({ea.gid}, {eb.gid})")
check("… sans rien effacer (les deux consommations restent)", ea in co.evs and eb in co.evs)
co, ea, eb = scene(True)
check("Si les deux sont confirmées par l'utilisateur, on n'y touche pas", ea.gid == "g1" and eb.gid == "g1")

# Un appareil désormais sur une prise n'est plus utilisé par aucun moyen (ni centre, ni exemples confirmés)
co = make()
co.groups = {"g1": {"id": "g1", "name": "Four", "status": "nomme"}, "g2": {"id": "g2", "name": "Micro-ondes", "mesure": True, "status": "nomme"},
             "g3": {"id": "g3", "name": "Lave-linge", "status": "nomme"}}
co.shared = C.SharedPlugs([{"entity": "sensor.prise", "names": ["Lave-linge", "Sèche-linge"]}])
check("Mesuré par une prise (bouton) ou sur une prise partagée : plus cherché sur la courbe",
      not co._on_plug("g1") and co._on_plug("g2") and co._on_plug("g3"))
seen = {}
real_assign = E.assign
E.assign = lambda evs, cents, examples, cats: seen.update(examples)
for i, gid in ((1, "g1"), (2, "g2"), (3, "g3")):
    co.rows[i] = {"start": 0, "end": 60, "base": 0, "prof": [1000, 1000]}
    co.evs.append(E.Ev(i, E.features([1000, 1000], 12), gid, True))
co._cluster()
E.assign = real_assign
check("… ni par ses utilisations confirmées (exemples)", set(seen) == {"g1"}, f"({sorted(seen)})")

print("\nTout est bon" if ok_all else "\nIl y a des échecs")
sys.exit(0 if ok_all else 1)
