"""Display-only translations; identifiers and stored appliance names stay unchanged."""

TEXT = {
    "fr": {
        "not_found": "Introuvable : {item}",
        "too_soon": "Ajouté il y a moins de 10 minutes : Home Assistant ne l'a pas encore enregistré. Réessaie dans quelques minutes.",
    },
    "en": {
        "puissance": "power", "énergie": "energy", "en marche": "running",
        "Non identifié": "Unidentified", "Non identifié coût": "Unidentified cost",
        "Classement du mois": "Monthly ranking", "Frigo (estimé)": "Fridge (estimated)",
        "Frigo (estimé) coût": "Fridge (estimated) cost", "Veilles permanentes": "Always on",
        "Veilles permanentes coût": "Always on cost", "Climatisation puissance moyenne": "Air conditioning average power",
        "Climatisation": "Air conditioning", "Économies possibles par an": "Potential annual savings",
        "Ce mois-ci comparé au précédent": "This month compared with last month",
        "Classement : repartir de zéro": "Reset ranking", "coût": "cost",
        "not_found": "Not found: {item}",
        "too_soon": "Added less than 10 minutes ago: Home Assistant has not recorded it yet. Try again in a few minutes.",
    },
    "it": {
        "puissance": "potenza", "énergie": "energia", "en marche": "in funzione",
        "Non identifié": "Non identificato", "Non identifié coût": "Costo non identificato",
        "Classement du mois": "Classifica del mese", "Frigo (estimé)": "Frigorifero (stimato)",
        "Frigo (estimé) coût": "Costo frigorifero (stimato)", "Veilles permanentes": "Consumi sempre attivi",
        "Veilles permanentes coût": "Costo consumi sempre attivi", "Climatisation puissance moyenne": "Potenza media climatizzazione",
        "Climatisation": "Climatizzazione", "Économies possibles par an": "Risparmio annuo possibile",
        "Ce mois-ci comparé au précédent": "Questo mese rispetto al precedente",
        "Classement : repartir de zéro": "Azzera classifica", "coût": "costo",
        "not_found": "Non trovato: {item}",
        "too_soon": "Aggiunto da meno di 10 minuti: Home Assistant non lo ha ancora registrato. Riprova tra qualche minuto.",
    },
}


def display_text(coord, text):
    """Translate a known label without translating user-defined names."""
    return TEXT.get(getattr(coord, "language", "fr"), {}).get(text, text)
