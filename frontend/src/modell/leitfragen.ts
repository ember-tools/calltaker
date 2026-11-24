import type {Abfragegraph} from './abfragegraph'
import type {Leitfrageneintrag} from './eintraege'
import type {Wahl} from './szenario'

/** One answer to a guidance question: the tiles it keeps, or the tiles it takes out. */
export interface Leitantwort {
    label: string
    behaelt?: string[]
    nimmt?: string[]
}

/**
 * Where a question that narrows no tile finds its answer in the solution: the solution's answer
 * at one of the `knoten` among `ja` means "Ja", among `nein` "Nein", any other leaves it free.
 */
export interface Loesungsbezug {
    knoten: string[]
    ja?: string[]
    nein?: string[]
}

/** One guidance question, when it is offered, and its answers. */
export interface Leitfrage {
    id: string
    frage: string
    hinweis?: string
    sicherheit?: boolean
    wenn?: string[]
    antworten: Leitantwort[]
    loesung?: Loesungsbezug
}

/** The guidance questions of one graph node, and tiles meant to be picked only directly. */
export interface Knotenleitfragen {
    knoten: string
    fragen: Leitfrage[]
    nurDirekt?: string[]
}

export const HOECHSTENS_VORGESCHLAGEN = 3

/**
 * The tiles left after an answer.
 *
 * @param antwort the answer
 * @param kacheln the tiles still in the running
 * @returns the tiles it leaves
 */
export function rest(antwort: Leitantwort, kacheln: ReadonlySet<string>): Set<string> {
    if (antwort.behaelt?.length) return new Set(antwort.behaelt.filter(k => kacheln.has(k)))
    const weg = new Set(antwort.nimmt ?? [])
    return new Set([...kacheln].filter(k => !weg.has(k)))
}

/**
 * The answers offered for the remaining tiles: those that leave some tile, so a caller who
 * contradicts an earlier answer cannot empty the choice.
 *
 * @param frage the question
 * @param kacheln the tiles still in the running
 * @returns the offered answers
 */
export function angeboten(frage: Leitfrage, kacheln: ReadonlySet<string>): Leitantwort[] {
    return frage.antworten.filter(antwort => rest(antwort, kacheln).size > 0)
}

/**
 * Whether a question is offered for the remaining tiles: while one of its `wenn` tiles is left,
 * and, unless it is a safety question, only when its answers still tell tiles apart.
 *
 * @param frage the question
 * @param kacheln the tiles still in the running
 * @returns true when it is offered
 */
export function offen(frage: Leitfrage, kacheln: ReadonlySet<string>): boolean {
    if (frage.wenn?.length && !frage.wenn.some(k => kacheln.has(k))) return false
    if (frage.sicherheit) return true
    const reste = new Set(angeboten(frage, kacheln).map(antwort => [...rest(antwort, kacheln)].sort().join('\n')))
    return reste.size > 1
}

/**
 * The question offered next, from position `ab` on: the first that is still offered. A question
 * passed is never offered again, since the tiles only shrink.
 *
 * @param eintrag the node's guidance questions
 * @param kacheln the tiles still in the running
 * @param ab the first position to look at
 * @returns the question and its position, or nothing when none is left
 */
export function naechste(eintrag: Knotenleitfragen, kacheln: ReadonlySet<string>, ab = 0): {stelle: number, frage: Leitfrage} | undefined {
    for (let stelle = ab; stelle < eintrag.fragen.length; stelle++) {
        const frage = eintrag.fragen[stelle]!
        if (offen(frage, kacheln)) return {stelle, frage}
    }
    return undefined
}

/** Where the guidance stands at one node after the answers given so far. */
export interface Leitstand {
    kacheln: Set<string>
    frage?: Leitfrage
    beantwortet: Leitfrageneintrag[]
    vorschlag: string[]
}

/**
 * Where the guidance stands at a node: the answers given are replayed in order, each to the
 * question then offered; an answer to another question, or one no longer offered, ends the replay,
 * as when the graph changed since. When no question is left, the remaining tiles, if few enough,
 * are the suggestion.
 *
 * @param eintrag the node's guidance questions
 * @param alle the node's tiles
 * @param gegeben the guidance answers given, in order; only those of this node count
 * @returns the tiles left, the question offered next, the answers that counted and the suggestion
 */
export function leitstand(eintrag: Knotenleitfragen, alle: readonly string[], gegeben: readonly Leitfrageneintrag[]): Leitstand {
    let kacheln = new Set(alle)
    let ab = 0
    const beantwortet: Leitfrageneintrag[] = []
    for (const antwort of gegeben.filter(g => g.knoten === eintrag.knoten)) {
        const naechsteFrage = naechste(eintrag, kacheln, ab)
        const gewaehlt = naechsteFrage?.frage.id === antwort.frage
            ? angeboten(naechsteFrage.frage, kacheln).find(a => a.label === antwort.antwort)
            : undefined
        if (!naechsteFrage || !gewaehlt) break
        kacheln = rest(gewaehlt, kacheln)
        ab = naechsteFrage.stelle + 1
        beantwortet.push(antwort)
    }
    const frage = naechste(eintrag, kacheln, ab)?.frage
    const vorschlag = !frage && kacheln.size <= HOECHSTENS_VORGESCHLAGEN ? alle.filter(k => kacheln.has(k)) : []
    return {kacheln, frage, beantwortet, vorschlag}
}

/**
 * The guidance questions of a node, if the catalogue has any.
 *
 * @param graph the graph with its catalogue
 * @param knoten the node's id
 * @returns the node's guidance questions
 */
export function leitfragenAn(graph: Abfragegraph, knoten: string): Knotenleitfragen | undefined {
    return graph.leitfragen?.find(eintrag => eintrag.knoten === knoten && eintrag.fragen.length > 0)
}

/**
 * How the caller answers a guidance question, by the solution: the answers that keep the correct
 * tile while others would take it out. A question linked to graph answers (`loesung`) is
 * answered "Ja" or "Nein" from those. Where every answer keeps the correct tile, the correct tile
 * is one chosen only directly, or the solution does not tell, the caller answers freely.
 *
 * @param eintrag the node's guidance questions
 * @param frage the question offered
 * @param kacheln the tiles still in the running
 * @param antworten the solution's answers, by node
 * @returns the labels that fit, empty when the caller answers freely
 */
export function antwortAusLoesung(eintrag: Knotenleitfragen, frage: Leitfrage, kacheln: ReadonlySet<string>, antworten: Record<string, Wahl>): string[] {
    const bezug = frage.loesung
    if (bezug) {
        const gegeben = bezug.knoten.map(k => antworten[k]?.antwort).find(Boolean) ?? ''
        if (bezug.ja?.includes(gegeben)) return ['Ja']
        if (bezug.nein?.includes(gegeben)) return ['Nein']
        return []
    }
    const korrekt = antworten[eintrag.knoten]?.antwort
    if (!korrekt || !kacheln.has(korrekt) || eintrag.nurDirekt?.includes(korrekt)) return []
    const angebot = angeboten(frage, kacheln)
    const passend = angebot.filter(antwort => rest(antwort, kacheln).has(korrekt))
    const eingrenzend = passend.filter(antwort => rest(antwort, kacheln).size < kacheln.size)
    if (passend.length === angebot.length) return []
    return (eingrenzend.length ? eingrenzend : passend).map(antwort => antwort.label)
}
