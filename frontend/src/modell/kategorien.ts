import type {Abfragegraph} from './abfragegraph'

/** Categories a scenario cannot be drawn for. */
const NICHT_ZIEHBAR = new Set(['', 'Aufwertung entfällt.'])

/** A category filter to suggest, with how many drawable codes it keeps. */
export interface Kategorievorschlag {
    wert: string
    anzahl: number
}

/**
 * How many drawable codes a category filter keeps; the generator matches the start of the
 * category, ignoring case.
 *
 * @param graph the graph
 * @param filter the filter as typed
 * @returns the number of codes
 */
export function passendeCodes(graph: Abfragegraph, filter: string): number {
    const anfang = filter.trim().toLowerCase()
    return graph.endpunkte.filter(e => e.pfad.length && !NICHT_ZIEHBAR.has(e.kategorie) && e.kategorie.toLowerCase().startsWith(anfang)).length
}

/**
 * The filters worth suggesting: each medical level (RD1 to RD5), each category's first word
 * (RD2C, BRAND, TH) and each whole category, broad ones first.
 *
 * @param graph the graph
 * @returns the suggestions with their code counts
 */
export function kategorievorschlaege(graph: Abfragegraph): Kategorievorschlag[] {
    const kategorien = new Set(graph.endpunkte.filter(e => e.pfad.length && !NICHT_ZIEHBAR.has(e.kategorie)).map(e => e.kategorie))
    const werte = new Set<string>()
    for (const kategorie of kategorien) {
        const stufe = /^RD\d/.exec(kategorie)
        if (stufe) werte.add(stufe[0])
        werte.add(kategorie.split(' ')[0]!.replace(/\.$/, ''))
        werte.add(kategorie)
    }
    const breite = (wert: string) => (kategorien.has(wert) ? 2 : /^RD\d$|^[A-Z]+$/.test(wert) ? 0 : 1)
    return [...werte]
        .sort((a, b) => breite(a) - breite(b) || a.localeCompare(b, 'de', {numeric: true}))
        .map(wert => ({wert, anzahl: passendeCodes(graph, wert)}))
}
