import type {Abfragegraph} from './abfragegraph'
import {endergebnis, istStillstand} from './abfrageweg'
import type {Abfrageeintrag} from './eintraege'

const TODESZEICHEN = {knoten: 'rd.09.todeszeichen', antwort: 'keine'}

/**
 * Whether CPR guidance is due: once the caller said there are no certain signs of death, or the
 * questioning reached a cardiac arrest code.
 *
 * @param graph the graph
 * @param abfrage the questioning so far
 * @returns true when the trainee should start CPR guidance
 */
export function reanimationFaellig(graph: Abfragegraph, abfrage: Abfrageeintrag): boolean {
    if (abfrage.pfad.some(s => s.knoten === TODESZEICHEN.knoten && s.antwort === TODESZEICHEN.antwort)) return true
    const ende = endergebnis(graph, abfrage)
    return Boolean(ende && istStillstand(ende.kategorie))
}
