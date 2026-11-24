import type {Abfragegraph} from './abfragegraph'
import type {Leitfrageneintrag, Schritteintrag} from './eintraege'
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

/** A debrief hint from the guidance questions, ready to show as an assessment. */
export interface Leithinweis {
    art: 'weg' | 'sicherheit'
    knoten: string
    soll: string
    ist: string
}

/**
 * The way the guidance questions take to the correct tile, answering as the solution does. Where
 * the solution leaves a question open, the narrowest answer that keeps the correct tile is taken,
 * as a trainee could; only answers that narrow the tiles count as steps.
 *
 * @param eintrag the node's guidance questions
 * @param alle the node's tiles
 * @param korrekt the correct tile
 * @param antworten the solution's answers, by node
 * @returns the narrowing questions with their answers, and the tiles left at the end
 */
export function wegZurLoesung(eintrag: Knotenleitfragen, alle: readonly string[], korrekt: string, antworten: Record<string, Wahl>): {weg: {frage: string, antwort: string}[], kacheln: Set<string>} {
    let kacheln: Set<string> = new Set(alle)
    let ab = 0
    const weg: {frage: string, antwort: string}[] = []
    for (let naechsteFrage = naechste(eintrag, kacheln, ab); naechsteFrage; naechsteFrage = naechste(eintrag, kacheln, ab)) {
        const {stelle, frage} = naechsteFrage
        ab = stelle + 1
        const angebot = angeboten(frage, kacheln)
        const laut = antwortAusLoesung(eintrag, frage, kacheln, antworten)
        const reste = angebot
            .filter(a => (laut.length ? laut.includes(a.label) : true))
            .map(antwort => ({antwort, uebrig: rest(antwort, kacheln)}))
            .filter(({uebrig}) => uebrig.has(korrekt) && uebrig.size < kacheln.size)
            .sort((a, b) => a.uebrig.size - b.uebrig.size)
        const engste = reste[0]
        if (!engste) continue
        kacheln = engste.uebrig
        weg.push({frage: frage.frage, antwort: engste.antwort.label})
    }
    return {weg, kacheln}
}

/**
 * What the debrief points out about the guidance questions, as hints, never as faults: where the
 * trainee picked another tile than the correct one at a node whose guidance questions lead to it,
 * the way they would have taken; and safety questions at a node the trainee went through but did
 * not ask. Steps the questioning took by itself are passed over.
 *
 * @param graph the graph with its catalogue
 * @param pfad the trainee's answers
 * @param gestellt the guidance questions the trainee asked
 * @param antworten the solution's answers, by node
 * @returns the hints, in the order of the path
 */
export function leithinweise(graph: Abfragegraph, pfad: readonly Schritteintrag[], gestellt: readonly Leitfrageneintrag[], antworten: Record<string, Wahl>): Leithinweis[] {
    const hinweise: Leithinweis[] = []
    for (const schritt of pfad) {
        const eintrag = leitfragenAn(graph, schritt.knoten)
        if (!eintrag || schritt.automatisch) continue
        const kacheln = graph.knoten[schritt.knoten]?.antworten ?? []
        const ids = kacheln.map(k => k.id)
        const label = (id?: string) => kacheln.find(k => k.id === id)?.label ?? ''
        for (const frage of eintrag.fragen.filter(f => f.sicherheit && offen(f, new Set(ids)))) {
            if (!gestellt.some(g => g.knoten === schritt.knoten && g.frage === frage.id)) hinweise.push({art: 'sicherheit', knoten: schritt.knoten, soll: '', ist: frage.frage})
        }
        const korrekt = antworten[schritt.knoten]?.antwort
        if (!korrekt || !schritt.antwort || schritt.antwort === korrekt || !ids.includes(korrekt) || eintrag.nurDirekt?.includes(korrekt)) continue
        const {weg, kacheln: rest} = wegZurLoesung(eintrag, ids, korrekt, antworten)
        if (!weg.length || !rest.has(korrekt) || rest.size > HOECHSTENS_VORGESCHLAGEN) continue
        const soll = [...weg.map(w => `${w.frage} ${w.antwort}`), label(korrekt)].join(' → ')
        hinweise.push({art: 'weg', knoten: schritt.knoten, soll, ist: label(schritt.antwort)})
    }
    return hinweise
}
