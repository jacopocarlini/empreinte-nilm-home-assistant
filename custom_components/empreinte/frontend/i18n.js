const messages = {
  fr: {
    overview: "Aperçu", discoveries: "Découvertes", habits: "Habitudes", map: "Carte",
    appliances: "Appareils", report: "Rapport", weeklyReport: "Rapport de la semaine",
    similarityMap: "Carte des ressemblances", today: "Aujourd'hui", yesterday: "Hier",
    detection: "Détection d'appareils", help: "Comment ça marche", theme: "Thème",
    home: "Ma maison", partial: "",
  },
  en: {
    overview: "Overview", discoveries: "Discoveries", habits: "Habits", map: "Map",
    appliances: "Appliances", report: "Report", weeklyReport: "Weekly report",
    similarityMap: "Similarity map", today: "Today", yesterday: "Yesterday",
    detection: "Appliance detection", help: "How it works", theme: "Theme",
    home: "My home", partial: "Translation is incomplete; some text remains in French.",
  },
  it: {
    overview: "Panoramica", discoveries: "Scoperte", habits: "Abitudini", map: "Mappa",
    appliances: "Dispositivi", report: "Rapporto", weeklyReport: "Rapporto settimanale",
    similarityMap: "Mappa delle somiglianze", today: "Oggi", yesterday: "Ieri",
    detection: "Rilevamento dispositivi", help: "Come funziona", theme: "Tema",
    home: "La mia casa", partial: "Traduzione incompleta: alcuni testi sono ancora in francese.",
  },
};

export function locale(language) {
  return ({ fr: "fr-FR", en: "en-GB", it: "it-IT" })[language] || "fr-FR";
}

export function translate(language, key) {
  return (messages[language] || messages.fr)[key] ?? messages.fr[key] ?? key;
}
