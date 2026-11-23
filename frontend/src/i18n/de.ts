/** Every text the interface shows. */
export default {
    app: {
        name: 'Calltaker',
        untertitel: 'Notrufabfrage-Training für die Berliner Feuerwehr',
    },
    start: {
        anlegenTitel: 'Neue Übung',
        anlegenText: 'Als Ausbilder eine Übung anlegen. Du bekommst einen Code für dich und einen für den Trainee.',
        anlegen: 'Übung anlegen',
        beitretenTitel: 'Beitreten',
        beitretenText: 'Mit dem Code, den du bekommen hast.',
        code: 'Code',
        beitreten: 'Beitreten',
    },
    verbindung: {
        getrennt: 'Getrennt vom Server. Neuer Versuch läuft …',
        ausbilder: 'Ausbilder',
        trainee: 'Trainee',
        verbunden: 'verbunden',
        nichtVerbunden: 'nicht verbunden',
    },
    codes: {
        ausbilder: 'Ausbilder-Code',
        trainee: 'Trainee-Code',
        kopieren: '{code} kopieren',
    },
    ausbilder: {
        titel: 'Ausbilder',
        pool: 'Pool',
        poolLeer: 'Noch keine Szenarien im Pool.',
        poolEins: 'Ein Szenario',
        poolAnzahl: '{anzahl} Szenarien',
        export: 'Pool herunterladen',
        import: 'Pool hochladen',
        modus: 'Beim Hochladen',
        ersetzen: 'Pool ersetzen',
        anhaengen: 'anhängen',
        einesUebernommen: 'Ein Szenario übernommen.',
        uebernommen: '{anzahl} Szenarien übernommen.',
        mitBefunden: 'Davon mit Hinweisen zur Korrektur: {befunde}.',
        keinJson: 'Die Datei ist kein JSON.',
    },
    trainee: {
        titel: 'Trainee',
        warten: 'Noch keine Anrufe.',
    },
    unbekannt: {
        titel: 'Diese Übung gibt es nicht.',
        text: 'Der Code ist falsch, oder die Übung wurde beendet, weil sie lange niemand geöffnet hat.',
        zurueck: 'Zur Startseite',
    },
    allgemein: {
        laden: 'Lädt …',
    },
}
