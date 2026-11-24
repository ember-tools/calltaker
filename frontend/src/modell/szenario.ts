/** A postal address in Berlin. */
export interface Adresse {
    strasse: string
    hausnummer: string
    plz: string
    ortsteil: string
}

/**
 * Where the emergency is: address, point and what a crew needs to find it. `koordinaten` is
 * (latitude, longitude) in WGS 84, Leaflet's order, not GeoJSON's.
 */
export interface Ort {
    adresse: Adresse
    koordinaten?: [number, number]
    objekt: string
    geschoss: string
    klingel: string
    anfahrt: string
    gefahren: string
    /** A pet at the place, as the caller would mention it, such as "ein Hund". */
    haustier?: string
}

/** Who calls: the name, the number shown, and the number the caller is reachable under. */
export interface Anrufer {
    name: string
    rufnummer?: string
    rufnummerUnterdrueckt: boolean
    rueckrufnummer?: string
}

/** What the caller answers at one node: an answer id with its label when written, or a typed value. */
export interface Wahl {
    antwort?: string
    label?: string
    wert?: string
}

/** The endpoint the scenario's path ends in, by node, with its code for reading. */
export interface Ziel {
    knoten: string
    code: string
}

/** How the trainer plays the caller; not part of the debrief. */
export interface Rolle {
    stimmung?: 'ruhig' | 'aufgeregt' | 'panisch' | 'verwirrt'
    sprache: string
    notizen: string
}

/** The truth behind one call, as the server hands it over. */
export interface Szenario {
    id: string
    version: 1
    abfrageVersion: number
    titel: string
    herkunft: 'vorbereitet' | 'generiert'
    ort: Ort
    anrufer: Anrufer
    betroffener?: {name: string}
    antworten: Record<string, Wahl>
    ziel: Ziel
    rolle: Rolle
    erweiterungen: Record<string, unknown>
}

/** One thing a check of a scenario against the question graph found. */
export interface Befund {
    art: 'fehler' | 'warnung'
    knoten?: string
    meldung: string
}

/** A downloaded pool of scenarios. */
export interface Pooldatei {
    format: 'calltaker-pool'
    version: 1
    abfrageVersion: number
    szenarien: Szenario[]
}
