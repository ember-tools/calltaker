import type {Abfragegraph} from './abfragegraph'
import {gewaehltesProtokoll} from './abfrageweg'
import type {Schritteintrag} from './eintraege'

/**
 * Whether the call can involve an orange plate, by the rules the server ships with the graph: a
 * protocol that can, or an answer saying hazardous goods are involved.
 *
 * @param graph the graph
 * @param pfad the trainee's path
 * @returns true when the plate field belongs in the mask
 */
export function mitWarntafel(graph: Abfragegraph, pfad: Schritteintrag[]): boolean {
    const regeln = graph.warntafel
    if (!regeln) return false
    if (regeln.protokolle.includes(gewaehltesProtokoll(graph, pfad)?.protokoll ?? '')) return true
    return pfad.some(schritt => regeln.antworten.some(a => a.knoten === schritt.knoten && a.antwort === schritt.antwort))
}
