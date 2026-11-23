import type {Adresse} from './szenario'

/** One step of the trainee's path: the node, and the answer chosen or the value typed. */
export interface Schritteintrag {
    knoten: string
    antwort?: string
    wert?: string
    /** A step the questioning took itself, because earlier answers decided it. */
    automatisch?: boolean
}

/** An endpoint chosen outside the path: by upgrading, or as the interim result on cancelling. */
export interface Codewahl {
    knoten: string
    code: string
}

/** The questioning as done: the path, and an upgrade or a cancellation, if any. */
export interface Abfrageeintrag {
    pfad: Schritteintrag[]
    aufwertung?: Codewahl
    abbruch?: {grund: string, ergebnis?: Codewahl}
    /** Whether the questioning has a code, as the phases decide it; the server only times it. */
    codeErreicht?: boolean
}

/** Everything the trainee entered during one call. */
export interface Eintraege {
    ort: {
        adresse: Adresse
        koordinaten?: [number, number]
        objekt: string
        geschoss: string
        klingel: string
        anfahrt: string
        gefahren: string
    }
    anrufer: {name: string, rufnummerBestaetigt: boolean, rueckrufnummer: string}
    betroffener: string
    abfrage: Abfrageeintrag
    hinweise: string
    zeiten: {adresse?: number, code?: number}
}

/**
 * Entries of a call nothing has been entered for yet.
 *
 * @returns empty entries
 */
export function leereEintraege(): Eintraege {
    return {
        ort: {adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: ''}, objekt: '', geschoss: '', klingel: '', anfahrt: '', gefahren: ''},
        anrufer: {name: '', rufnummerBestaetigt: false, rueckrufnummer: ''},
        betroffener: '',
        abfrage: {pfad: []},
        hinweise: '',
        zeiten: {},
    }
}
