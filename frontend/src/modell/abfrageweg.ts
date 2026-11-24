import type {Abfragegraph, Antwort, Endpunkt, Knoten} from '../modell/abfragegraph'
import type {Abfrageeintrag, Codewahl, Schritteintrag} from './eintraege'

/** An endpoint as a result: where it is, its code and its category. */
export interface Ergebnis {
    knoten: string
    code: string
    kategorie: string
    stichwort: string
}

/** Categories that say nothing about urgency and are never offered as a result. */
const OHNE_RANG = new Set(['', 'Aufwertung entfällt.'])

/**
 * How urgent a category is; higher is more urgent, and a category without rank is -1.
 *
 * Medical categories rank by their level (RD1 before RD5), then by whether an emergency doctor
 * (NC) or an equipped ambulance (C) is sent, then by first responders. Combined alarms rank like
 * the level they include. Fire and rescue categories rank by their number, the small (K.) and
 * medium (M.) ones below and above level 1.
 *
 * @param kategorie the category
 * @returns its rank
 */
export function schwere(kategorie: string): number {
    if (OHNE_RANG.has(kategorie)) return -1
    if (kategorie === 'RD_Mehrere Patienten') return 95
    if (kategorie === 'RD_BT_NA') return 85
    if (kategorie === 'RD_BT_RTW') return 75
    const rd = /^RD(\d)(NC|C|B)?\s?(FR|REA|NNAD)?/.exec(kategorie)
    if (rd) {
        const stufe = (6 - Number(rd[1])) * 20
        const mittel = {NC: 8, C: 4, B: 2}[rd[2] ?? ''] ?? 0
        const zusatz = {REA: 3, NNAD: 2, FR: 1}[rd[3] ?? ''] ?? 0
        return stufe + mittel + zusatz
    }
    const zahl = /(\d+)/.exec(kategorie)
    if (zahl) return Number(zahl[1])
    return / K\.$/.test(kategorie) ? 0.5 : / M\.$/.test(kategorie) ? 1.5 : 0
}

/**
 * The nodes the path leads to, following switches; stops where the path leaves the graph.
 *
 * @param graph the graph
 * @param pfad the steps taken
 * @returns the node the trainee stands at, and how many steps of the path fit the graph
 */
export function aktuellerKnoten(graph: Abfragegraph, pfad: Schritteintrag[]): {knoten: string, passend: number} {
    let aktuell = weichenFolgen(graph, graph.meta.wurzel, pfad)
    for (const [stelle, schritt] of pfad.entries()) {
        if (schritt.knoten !== aktuell) return {knoten: aktuell, passend: stelle}
        const naechster = zielVon(graph.knoten[aktuell], schritt)
        if (!naechster) return {knoten: aktuell, passend: stelle}
        aktuell = weichenFolgen(graph, naechster, pfad.slice(0, stelle + 1))
    }
    return {knoten: aktuell, passend: pfad.length}
}

/**
 * Where a step leads from its node.
 *
 * @param knoten the node
 * @param schritt the step taken there
 * @returns the next node, or undefined when the step does not fit the node
 */
function zielVon(knoten: Knoten | undefined, schritt: Schritteintrag): string | undefined {
    if (!knoten) return undefined
    if (knoten.antworten) return knoten.antworten.find(antwort => antwort.id === schritt.antwort)?.ziel
    if (knoten.eingabe) return knoten.ziel
    return undefined
}

/**
 * Follows switches from a node by the answers given earlier on the path.
 *
 * @param graph the graph
 * @param start the node
 * @param pfad the steps taken so far
 * @returns the first node that is not a switch
 */
function weichenFolgen(graph: Abfragegraph, start: string, pfad: Schritteintrag[]): string {
    let aktuell = start
    for (let tiefe = 0; tiefe < 20; tiefe++) {
        const weiche = graph.knoten[aktuell]?.weiche
        if (!weiche) return aktuell
        const antwort = pfad.find(schritt => schritt.knoten === weiche.knoten)?.antwort
        const ziel = antwort ? weiche.ziele[antwort] : undefined
        if (!ziel) return aktuell
        aktuell = ziel
    }
    return aktuell
}

/**
 * The most urgent endpoint reachable from every node, worked out once per graph.
 *
 * @param graph the graph
 * @returns the endpoint per node, where one is reachable
 */
export function schwersteErreichbare(graph: Abfragegraph): Map<string, Ergebnis> {
    const ergebnis = new Map<string, Ergebnis>()
    const besucht = new Set<string>()
    const besuchen = (id: string): Ergebnis | undefined => {
        if (besucht.has(id)) return ergebnis.get(id)
        besucht.add(id)
        const knoten = graph.knoten[id]
        if (!knoten) return undefined
        if (knoten.code !== undefined) {
            if (schwere(knoten.kategorie ?? '') < 0) return undefined
            const eigen = {knoten: id, code: knoten.code, kategorie: knoten.kategorie ?? '', stichwort: knoten.stichwort ?? ''}
            ergebnis.set(id, eigen)
            return eigen
        }
        const ziele = knoten.antworten?.map(antwort => antwort.ziel) ?? (knoten.weiche ? Object.values(knoten.weiche.ziele) : [knoten.ziel ?? ''])
        const bestes = ziele.map(besuchen).filter((e): e is Ergebnis => e !== undefined).sort((a, b) => schwere(b.kategorie) - schwere(a.kategorie))[0]
        if (bestes) ergebnis.set(id, bestes)
        return bestes
    }
    Object.keys(graph.knoten).forEach(besuchen)
    return ergebnis
}

/**
 * The protocol the path chose, if it got that far.
 *
 * @param graph the graph
 * @param pfad the steps taken
 * @returns the answer that chose the protocol
 */
export function gewaehltesProtokoll(graph: Abfragegraph, pfad: Schritteintrag[]): Antwort | undefined {
    for (const schritt of pfad) {
        const antwort = graph.knoten[schritt.knoten]?.antworten?.find(a => a.id === schritt.antwort)
        if (antwort?.protokoll) return antwort
    }
    return undefined
}

/**
 * The endpoint as a result.
 *
 * @param graph the graph
 * @param wahl the endpoint by node and code
 * @returns the result
 */
export function ergebnisAus(graph: Abfragegraph, wahl: Codewahl): Ergebnis {
    const knoten = graph.knoten[wahl.knoten]
    return {knoten: wahl.knoten, code: wahl.code, kategorie: knoten?.kategorie ?? '', stichwort: knoten?.stichwort ?? ''}
}

/**
 * The code the questioning has reached: an upgrade, the endpoint the path reached, or a
 * cancellation's result, in that order.
 *
 * @param graph the graph
 * @param abfrage the questioning
 * @returns the result, or undefined while the questioning is open
 */
export function endergebnis(graph: Abfragegraph, abfrage: Abfrageeintrag): Ergebnis | undefined {
    if (abfrage.aufwertung) return ergebnisAus(graph, abfrage.aufwertung)
    const {knoten} = aktuellerKnoten(graph, abfrage.pfad)
    const endpunkt = graph.knoten[knoten]
    if (endpunkt?.code !== undefined) return ergebnisAus(graph, {knoten, code: endpunkt.code})
    if (abfrage.abbruch?.ergebnis) return ergebnisAus(graph, abfrage.abbruch.ergebnis)
    return undefined
}

/**
 * The result as it stands now: the final one, or once a protocol is chosen the most urgent
 * endpoint still reachable.
 *
 * @param graph the graph
 * @param abfrage the questioning
 * @param schwerste the most urgent endpoint per node
 * @returns the interim result, or undefined before a protocol is chosen
 */
export function zwischenergebnis(graph: Abfragegraph, abfrage: Abfrageeintrag, schwerste: Map<string, Ergebnis>): Ergebnis | undefined {
    const fertig = endergebnis(graph, abfrage)
    if (fertig) return fertig
    if (!gewaehltesProtokoll(graph, abfrage.pfad)) return undefined
    return schwerste.get(aktuellerKnoten(graph, abfrage.pfad).knoten)
}

/**
 * The endpoints of a protocol more urgent than a category, most urgent first, once per code. For a
 * cardiac arrest, codes as urgent are offered too, so a cause found later can still be named: an
 * arrest reached straight from "atmet nicht" can become one by hanging or drowning.
 *
 * @param graph the graph
 * @param protokoll the protocol's id
 * @param ab the category to start from
 * @param ohne the current code, which is not offered
 * @returns the endpoints to upgrade to
 */
export function hoehereEndpunkte(graph: Abfragegraph, protokoll: string, ab: string, ohne = ''): Endpunkt[] {
    const grenze = schwere(ab)
    const gesehen = new Set<string>()
    return graph.endpunkte
        .filter(e => e.protokoll === protokoll && e.code !== ohne && (schwere(e.kategorie) > grenze || (schwere(e.kategorie) === grenze && istStillstand(ab))))
        .sort((a, b) => schwere(b.kategorie) - schwere(a.kategorie) || a.code.localeCompare(b.code))
        .filter(e => !gesehen.has(e.code) && gesehen.add(e.code))
}

/**
 * What tells answers apart whose labels are the same: the code and category they lead to at
 * worst, then the reason of that code, and as a last resort a running number.
 *
 * @param knoten the node
 * @param schwerste the most urgent endpoint per node
 * @param knotenGraph the graph, for the reasons of the endpoints
 * @returns the addition per answer id, only for answers that share their label
 */
export function unterscheidungen(knoten: Knoten, schwerste: Map<string, Ergebnis>, knotenGraph: Abfragegraph): Map<string, string> {
    const antworten = knoten.antworten ?? []
    const anzahl = new Map<string, number>()
    antworten.forEach(a => anzahl.set(a.label, (anzahl.get(a.label) ?? 0) + 1))
    const doppelt = antworten.filter(a => (anzahl.get(a.label) ?? 0) > 1)
    const stufen = [
        (a: Antwort) => kurz(schwerste.get(a.ziel)),
        (a: Antwort) => `${kurz(schwerste.get(a.ziel))} · ${anlassVon(knotenGraph, schwerste.get(a.ziel))}`,
    ]
    const zusatz = new Map<string, string>()
    const gruppen = new Map<string, Antwort[]>()
    doppelt.forEach(a => gruppen.set(a.label, [...(gruppen.get(a.label) ?? []), a]))
    for (const gruppe of gruppen.values()) {
        const stufe = stufen.find(s => new Set(gruppe.map(s)).size === gruppe.length)
        gruppe.forEach((antwort, stelle) => zusatz.set(antwort.id, stufe ? stufe(antwort) : `${kurz(schwerste.get(antwort.ziel))} · ${stelle + 1}`))
    }
    return zusatz
}

/**
 * A result as code and category.
 *
 * @param ergebnis the result
 * @returns the short form, or an empty text
 */
function kurz(ergebnis: Ergebnis | undefined): string {
    return ergebnis ? `${ergebnis.code} · ${ergebnis.kategorie}` : ''
}

/**
 * The reason of a result's endpoint.
 *
 * @param graph the graph
 * @param ergebnis the result
 * @returns its reason, or an empty text
 */
function anlassVon(graph: Abfragegraph, ergebnis: Ergebnis | undefined): string {
    return ergebnis ? graph.knoten[ergebnis.knoten]?.anlass ?? '' : ''
}

/**
 * Whether a category is a cardiac arrest: resuscitation, or resuscitation of a newborn.
 *
 * @param kategorie the category
 * @returns true for an arrest category
 */
export function istStillstand(kategorie: string): boolean {
    return kategorie.startsWith('RD1NC REA') || kategorie.startsWith('RD1NC NNAD')
}

/**
 * Whether one node can be reached from another along answers, inputs and switches.
 *
 * @param graph the graph
 * @param von the node to start at
 * @param ziel the node to reach
 * @returns true when a way leads there
 */
export function erreichbar(graph: Abfragegraph, von: string, ziel: string): boolean {
    const gesehen = new Set<string>()
    const offen = [von]
    while (offen.length) {
        const id = offen.pop()!
        if (id === ziel) return true
        if (gesehen.has(id)) continue
        gesehen.add(id)
        const knoten = graph.knoten[id]
        if (!knoten) continue
        offen.push(...(knoten.antworten ?? []).map(a => a.ziel), ...(knoten.ziel ? [knoten.ziel] : []), ...Object.values(knoten.weiche?.ziele ?? {}))
    }
    return false
}

/**
 * The Fachrichtung the trainee chose at the root, if any.
 *
 * @param graph the graph
 * @param pfad the trainee's path
 * @returns the root answer, such as "rd"
 */
export function fachrichtungImPfad(graph: Abfragegraph, pfad: Schritteintrag[]): string | undefined {
    return pfad.find(schritt => schritt.knoten === graph.meta.wurzel)?.antwort
}
