"""Prise mesurée en décalage avec le compteur, et appareil qu'on monte cran par cran.

Lancer :  python tests/test_decalage.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "empreinte"))
import engine as E  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

T0 = 1_800_000_000.0
FOND = 300.0


def courbe(duree, step=7):
    return [T0 + k * step for k in range(int(duree / step))]


def test_prise_en_retard():
    """Une résistance de lave-linge (1800 W, sur une prise mesurée) qui se coupe 20 s puis se rallume :
    le compteur le voit tout de suite, la prise 8 s plus tard. Aucun appareil ne doit apparaître."""
    ts = courbe(1800)
    ps, subs = [], []
    for t in ts:
        dt = t - T0
        lave = 0 if 600 <= dt < 620 else 1800                 # ce que fait vraiment le lave-linge
        lu = 0 if 608 <= dt < 628 else 1800                   # ce que la prise signale (8 s de retard)
        ps.append(FOND + lave)
        subs.append(lu)
    brut, _ = E.segment(ts, [p - s for p, s in zip(ps, subs)])
    corrige, _ = E.segment(ts, E.realign(ts, ps, subs))
    assert brut, "sans correction, le décalage crée un faux appareil (sinon le test ne prouve rien)"
    assert not corrige, f"faux appareil restant : {corrige}"


def test_prise_en_avance():
    """La prise signale l'arrêt 10 s avant le compteur : rien non plus."""
    ts = courbe(1800)
    ps, subs = [], []
    for t in ts:
        dt = t - T0
        ps.append(FOND + (1800 if dt < 900 else 0))
        subs.append(1800 if dt < 890 else 0)
    corrige, _ = E.segment(ts, E.realign(ts, ps, subs))
    assert not corrige, f"faux appareil restant : {corrige}"


def test_vrai_appareil_garde():
    """Un vrai appareil (bouilloire) qui démarre au même moment qu'une prise : il reste là."""
    ts = courbe(1800)
    ps, subs = [], []
    for t in ts:
        dt = t - T0
        prise = 1000 if dt >= 600 else 0
        bouilloire = 2000 if 600 <= dt < 780 else 0
        ps.append(FOND + prise + bouilloire)
        subs.append(1000 if dt >= 608 else 0)
    found, _ = E.segment(ts, E.realign(ts, ps, subs))
    assert len(found) == 1, found
    e = found[0]
    assert 150 <= e["end"] - e["start"] <= 220 and 1700 <= max(e["prof"]) <= 2300, e


def test_plaque_cran_par_cran():
    """Une plaque montée en 5 crans de 150 W (aucun saut de 350 W) pendant 5 min : elle est retrouvée."""
    ts = courbe(1800)
    ps = []
    for t in ts:
        dt = t - T0
        p = 0
        if 600 <= dt < 900:
            p = 150 * min(5, 1 + int((dt - 600) // 30))
        ps.append(FOND + p)
    found, _ = E.segment(ts, ps)
    assert len(found) == 1, found
    e = found[0]
    # (le premier cran, sous 200 W, ne se distingue pas encore du fond)
    assert e.get("creep") and abs(e["start"] - (T0 + 600)) <= 45 and 240 <= e["end"] - e["start"] <= 330, e
    assert 650 <= max(e["prof"]) <= 800, e


def test_petit_appareil_reste_allume():
    """Après une montée lente, un petit appareil (200 W) reste allumé : il ne prolonge pas l'utilisation."""
    ts = courbe(3600)
    ps = []
    for t in ts:
        dt = t - T0
        p = 0
        if dt >= 600:
            p += 200
        if 640 <= dt < 900:
            p += 450
        ps.append(FOND + p)
    found, _ = E.segment(ts, ps)
    assert len(found) == 1, found
    assert found[0]["end"] - T0 <= 960, found[0]


def test_lent_et_faible_ignore():
    """Une montée de 250 W au total (un écran, une lampe) n'ouvre rien."""
    ts = courbe(1800)
    ps = [FOND + (125 if t - T0 >= 600 else 0) + (125 if t - T0 >= 660 else 0) for t in ts]
    found, _ = E.segment(ts, ps)
    assert not found, found


def _lave_linge_en_retard():
    """Compteur et prise d'un lave-linge dont la résistance se coupe 20 s ; la prise le signale 8 s après."""
    rows = []
    for t in courbe(1800):
        dt = t - T0
        lave = 0 if 600 <= dt < 620 else 1800
        lu = 0 if 608 <= dt < 628 else 1800
        rows.append((t, FOND + lave, lu))
    return rows


def test_analyse_sans_faux_appareil():
    """L'analyse de Empreinte (pas seulement le découpage) ne garde aucune utilisation."""
    sys.path.insert(0, os.path.dirname(__file__))
    from ha_stub import C, make
    co = make()
    rows = _lave_linge_en_retard()
    real = C.time.time
    try:
        C.time.time = lambda: rows[-1][0] + 600
        co.store.add_samples(rows)
        co.processed_until = rows[0][0]
        co._process()
    finally:
        C.time.time = real
    assert not co.evs, [co.rows[e.id] for e in co.evs]


def test_faux_appareils_deja_enregistres_retires():
    """Une fausse utilisation enregistrée avant la correction est retirée une fois, une vraie est gardée."""
    sys.path.insert(0, os.path.dirname(__file__))
    from ha_stub import make
    co = make()
    rows = _lave_linge_en_retard()
    co.store.add_samples(rows)
    f = E.features([1500], 12.0)
    ghost = co.store.add_event(T0 + 600, T0 + 615, FOND, [1500], f)
    real_ev = co.store.add_event(T0 + 1200, T0 + 1215, FOND, [1500], f)   # rien ne bouge sur la prise ici
    for eid, s in ((ghost, T0 + 600), (real_ev, T0 + 1200)):
        co.rows[eid] = {"start": s, "end": s + 15, "base": FOND, "prof": [1500]}
        co.evs.append(E.Ev(eid, f))
    co._drop_lag_ghosts()
    assert [e.id for e in co.evs] == [real_ev], [e.id for e in co.evs]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(f"{len(tests)} tests passés")
