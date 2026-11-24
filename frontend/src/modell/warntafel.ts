import type {Abfragegraph} from './abfragegraph'
import type {Schritteintrag} from './eintraege'
import type {Warntafel} from './gefahrstoffe'
import type {Wahl} from './szenario'

/**
 * A plate from the answer to the plate question, which reads "hazard number/UN number".
 *
 * @param wert the answer
 * @returns the plate, or nothing for "no plate" or an unreadable answer
 */
export function tafelAusWert(wert?: string): Warntafel | undefined {
    const treffer = /^(X?\d{2,3})?\/(\d{4})$/.exec((wert ?? '').trim().toUpperCase())
    return treffer ? {gefahrenzahl: treffer[1] ?? '', un: treffer[2]!} : undefined
}

/**
 * The answer to the plate question for a plate.
 *
 * @param tafel the plate
 * @returns "hazard number/UN number"
 */
export function wertAusTafel(tafel: Warntafel): string {
    return `${tafel.gefahrenzahl.trim().toUpperCase()}/${tafel.un.trim()}`
}

/**
 * Whether a node asks for an orange plate.
 *
 * @param graph the graph
 * @param knoten the node
 * @returns true for a plate question
 */
export function istTafelfrage(graph: Abfragegraph, knoten: string): boolean {
    return graph.knoten[knoten]?.eingabe?.art === 'warntafel'
}

/**
 * The plate the trainee recorded in the questioning.
 *
 * @param graph the graph
 * @param pfad the trainee's path
 * @returns the plate, if one was read out
 */
export function tafelImPfad(graph: Abfragegraph, pfad: Schritteintrag[]): Warntafel | undefined {
    return tafelAusWert(pfad.find(schritt => istTafelfrage(graph, schritt.knoten))?.wert)
}

/**
 * The plate a scenario's caller reads out.
 *
 * @param graph the graph
 * @param antworten the scenario's answers
 * @returns the plate, if the scenario has one
 */
export function tafelDerWahrheit(graph: Abfragegraph, antworten: Record<string, Wahl>): Warntafel | undefined {
    const knoten = Object.keys(antworten).find(id => istTafelfrage(graph, id))
    return knoten ? tafelAusWert(antworten[knoten]?.wert) : undefined
}
