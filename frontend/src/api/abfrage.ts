/** The ages an answer applies to, both bounds inclusive. */
export interface Altersgrenze {
    min?: number
    max?: number
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

/** The graph's version, its root and the notes on its data. */
export interface Meta {
    version: number
    wurzel: string
    quelle: string
    hinweise: Record<string, string>
    notfallkategorien: Record<string, string>
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

/** The question graph as the server hands it over. */
export interface Abfragegraph {
    meta: Meta
    knoten: Record<string, Knoten>
    endpunkte: Endpunkt[]
}

/**
 * Loads the question graph from the server.
 *
 * @returns the graph with its code index
 */
export async function ladeAbfrage(): Promise<Abfragegraph> {
    const antwort = await fetch('/api/abfrage')
    if (!antwort.ok) throw new Error(`Abfragegraph nicht ladbar: HTTP ${antwort.status}`)
    return await antwort.json() as Abfragegraph
}
