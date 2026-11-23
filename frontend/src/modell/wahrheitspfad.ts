import type {Abfragegraph} from './abfragegraph'
import {aktuellerKnoten} from './abfrageweg'
import type {Schritteintrag} from './eintraege'
import {pfadAusAntworten} from './szenarioentwurf'
import type {Wahl} from './szenario'

/** How a step of the truth stands against the trainee's path. */
export type Schrittstand = 'gleich' | 'anders' | 'offen' | 'hier'

/** One step of the truth path with what the trainee did there. */
export interface Wahrheitsschritt {
    knoten: string
    frage: string
    soll: string
    ist?: string
    stand: Schrittstand
}

/** The truth path laid against the trainee's, and where the trainee left it. */
export interface Pfadvergleich {
    schritte: Wahrheitsschritt[]
    /** The first step where the trainee answered otherwise or asked something the truth does not. */
    abzweigung?: {knoten: string, frage: string, ist: string}
    /** The question the trainee stands at when it lies off the truth path, with the scenario's answer if it has one. */
    abseits?: {knoten: string, frage: string, soll?: string}
}

/**
 * What a step says, as people read it: the answer's label, or the typed value.
 *
 * @param graph the graph
 * @param knoten the node
 * @param wahl the answer id or typed value
 * @param wahl.antwort the chosen answer's id
 * @param wahl.wert the typed value
 * @returns the readable answer
 */
function lesbar(graph: Abfragegraph, knoten: string, wahl: {antwort?: string, wert?: string}): string {
    const antwort = graph.knoten[knoten]?.antworten?.find(a => a.id === wahl.antwort)
    return antwort?.label ?? wahl.wert ?? ''
}

/**
 * Whether two answers at a node agree: the same answer, or the same typed value ignoring case
 * and spacing.
 *
 * @param a one answer
 * @param a.antwort its answer id
 * @param a.wert its typed value
 * @param b the other
 * @param b.antwort its answer id
 * @param b.wert its typed value
 * @returns true when they agree
 */
function stimmt(a: {antwort?: string, wert?: string}, b: {antwort?: string, wert?: string}): boolean {
    if (a.antwort || b.antwort) return a.antwort === b.antwort
    return (a.wert ?? '').trim().toLowerCase() === (b.wert ?? '').trim().toLowerCase()
}

/**
 * Lays the trainee's path against the scenario's truth path, step by step.
 *
 * Steps are matched by node, since the truth is keyed by node: a step the trainee has not reached
 * is open, the one the trainee stands at is marked, and an answer that differs is a deviation.
 * The first deviation, or the first question the truth does not ask, is where the trainee left
 * the truth path; a question the trainee stands at off the path is shown with the scenario's
 * answer when it has one, else the trainer improvises.
 *
 * @param graph the graph
 * @param antworten the scenario's answers by node
 * @param pfad the trainee's path
 * @returns the comparison
 */
export function vergleichePfad(graph: Abfragegraph, antworten: Record<string, Wahl>, pfad: Schritteintrag[]): Pfadvergleich {
    const wahrheit = pfadAusAntworten(graph, antworten)
    const imPfad = new Map(pfad.map(schritt => [schritt.knoten, schritt]))
    const aktuell = aktuellerKnoten(graph, pfad).knoten
    const schritte = wahrheit.map((schritt): Wahrheitsschritt => {
        const frage = graph.knoten[schritt.knoten]?.frage ?? schritt.knoten
        const soll = lesbar(graph, schritt.knoten, schritt)
        const getan = imPfad.get(schritt.knoten)
        if (!getan) return {knoten: schritt.knoten, frage, soll, stand: schritt.knoten === aktuell ? 'hier' : 'offen'}
        return {knoten: schritt.knoten, frage, soll, ist: lesbar(graph, schritt.knoten, getan), stand: stimmt(schritt, getan) ? 'gleich' : 'anders'}
    })
    const imSoll = new Map(wahrheit.map(schritt => [schritt.knoten, schritt]))
    const weg = pfad.find(schritt => !imSoll.has(schritt.knoten) || !stimmt(imSoll.get(schritt.knoten)!, schritt))
    const abzweigung = weg && {knoten: weg.knoten, frage: graph.knoten[weg.knoten]?.frage ?? weg.knoten, ist: lesbar(graph, weg.knoten, weg)}
    const knoten = graph.knoten[aktuell]
    const abseits = !imSoll.has(aktuell) && knoten?.frage
        ? {knoten: aktuell, frage: knoten.frage, soll: antworten[aktuell] ? lesbar(graph, aktuell, antworten[aktuell]) : undefined}
        : undefined
    return {schritte, abzweigung, abseits}
}
