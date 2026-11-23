/** The ages an answer applies to, both bounds inclusive, or that it is for an unknown age. */
export interface Altersgrenze {
    min?: number
    max?: number
    unbekannt?: boolean
}

/** One answer to choose from. */
export interface Antwort {
    id: string
    label: string
    aussage?: string
    ziel: string
    nr?: string
    farbe?: string
    protokoll?: string
    alter?: Altersgrenze
    geschlecht?: 'w' | 'm'
}

/** What is recorded when a typed answer is left empty. */
export interface Leer {
    label: string
    aussage: string
}

/** A question answered by typing; `{wert}` in the template stands for what was typed. */
export interface Eingabe {
    vorlage: string
    platzhalter: string
    leer?: Leer
}

/** A switch following the answer given at another node. */
export interface Weiche {
    knoten: string
    ziele: Record<string, string>
}

/**
 * One node of the question graph. Which fields are set decides its kind: a choice (`antworten`), a
 * typed answer (`eingabe` with `ziel`), a switch (`weiche`) or an endpoint (`code`).
 */
export interface Knoten {
    frage?: string
    hinweis?: string
    pflicht?: boolean
    anleitung?: string
    antworten?: Antwort[]
    eingabe?: Eingabe
    ziel?: string
    weiche?: Weiche
    code?: string
    kategorie?: string
    anlass?: string
    stichwort?: string
}

/** Where the opening asks for the person; `geschlecht` maps the answers to "w" and "m". */
export interface Person {
    alter_knoten: string
    geschlecht_knoten: string
    geschlecht: Record<string, 'w' | 'm'>
}

/** Which answers of a node come first when earlier answers point that way. */
export interface Eingrenzung {
    knoten: string
    wenn: {knoten: string, antworten: string[]}[]
    zuerst: string[]
}

/** The graph's version, its root, the notes on its data, and how the questioning narrows. */
export interface Meta {
    version: number
    wurzel: string
    quelle: string
    hinweise: Record<string, string>
    notfallkategorien: Record<string, string>
    person?: Person
    eingrenzung?: Eingrenzung[]
    /** The answers that mean the caller is not on site. */
    abwesend?: {knoten: string, antwort: string}[]
}

/** One step of a path through the graph: the node and the answer taken there. */
export interface Schritt {
    knoten: string
    antwort?: string
}

/** A code with one path that reaches it from its protocol's choice. */
export interface Endpunkt {
    code: string
    kategorie: string
    anlass: string
    stichwort: string
    fachrichtung: string
    protokoll: string
    knoten: string
    pfad: Schritt[]
}

/** One set of conditions that together make an instruction due; left-out conditions do not count. */
export interface Wenn {
    fachrichtung?: 'rd' | 'brand' | 'th'
    protokolle?: string[]
    antworten?: {knoten: string, antwort: string}[]
    /** None of these answers may have been given. */
    nicht?: {knoten: string, antwort: string}[]
    kategorien?: string[]
}

/** An instruction to the caller: sentences to read out, whether it must be given, when it is due. */
export interface Anleitung {
    id: string
    titel: string
    saetze: string[]
    pflicht?: boolean
    wenn: Wenn[]
    schliesstAus?: string[]
    /** Due even when the caller is not on site. */
    auchOhneVorOrt?: boolean
    quelle: string
}

/** The question graph as the server hands it over, with the instructions to the caller. */
export interface Abfragegraph {
    meta: Meta
    knoten: Record<string, Knoten>
    endpunkte: Endpunkt[]
    anleitungen?: Anleitung[]
    /** When a call can involve an orange plate: by protocol, or by an answer saying so. */
    warntafel?: {protokolle: string[], antworten: {knoten: string, antwort: string}[]}
}
