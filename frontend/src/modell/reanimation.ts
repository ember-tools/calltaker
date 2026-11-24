import type {Abfragegraph} from './abfragegraph'
import {endergebnis, istStillstand} from './abfrageweg'
import type {Abfrageeintrag, Eintraege} from './eintraege'

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

/**
 * Whether the trainee has to stay on the line: CPR guidance has started and the crews have not
 * arrived yet.
 *
 * @param eintraege the entries
 * @param eintreffenUm when the crews arrive, as the server says
 * @param jetzt the present
 * @returns true while the crews are on their way
 */
export function wartetAufKraefte(eintraege: Eintraege, eintreffenUm: number | undefined, jetzt: number): boolean {
    return eintraege.zeiten.reanimation !== undefined && (eintreffenUm === undefined || jetzt < eintreffenUm)
}
