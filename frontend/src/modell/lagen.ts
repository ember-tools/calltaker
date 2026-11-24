import type {Abfragegraph} from './abfragegraph'

/** Categories a scenario cannot be drawn for. */
const NICHT_ZIEHBAR = new Set(['', 'Aufwertung entfällt.'])

/** A protocol the generator can be limited to: its id, how the questioning names it, its codes. */
export interface Lage {
    protokoll: string
    name: string
    anzahl: number
}

/** The protocols of one Fachrichtung, named as the questioning names it. */
export interface Lagengruppe {
    fachrichtung: string
    name: string
    lagen: Lage[]
}

/**
 * The protocols a trainer can limit made-up scenarios to, by Fachrichtung and in alphabetical
 * order, each named as the questioning offers it, such as "Sturz" or "Verkehrsunfall", with the
 * number of codes it can draw.
 *
 * @param graph the graph
 * @returns the groups, without protocols that have nothing to draw
 */
export function lagen(graph: Abfragegraph): Lagengruppe[] {
    const namen = new Map<string, string>()
    for (const knoten of Object.values(graph.knoten)) {
        for (const antwort of knoten.antworten ?? []) {
            if (antwort.protokoll && !namen.has(antwort.protokoll)) namen.set(antwort.protokoll, antwort.label)
        }
    }
    const anzahl = new Map<string, number>()
    const fachrichtung = new Map<string, string>()
    for (const endpunkt of graph.endpunkte) {
        if (!endpunkt.pfad.length || NICHT_ZIEHBAR.has(endpunkt.kategorie)) continue
        anzahl.set(endpunkt.protokoll, (anzahl.get(endpunkt.protokoll) ?? 0) + 1)
        fachrichtung.set(endpunkt.protokoll, endpunkt.fachrichtung)
    }
    const wurzel = graph.knoten[graph.meta.wurzel]?.antworten ?? []
    return wurzel.map(eintrag => ({
        fachrichtung: eintrag.id,
        name: eintrag.label,
        lagen: [...anzahl]
            .filter(([protokoll]) => fachrichtung.get(protokoll) === eintrag.id)
            .map(([protokoll, zahl]) => ({protokoll, name: namen.get(protokoll) ?? protokoll, anzahl: zahl}))
            .sort((a, b) => a.name.localeCompare(b.name, 'de')),
    })).filter(gruppe => gruppe.lagen.length)
}
