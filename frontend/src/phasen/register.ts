import type {Eintraege} from '../modell/eintraege'
import {abfrage} from './abfrage'
import {personalien} from './personalien'
import {standort} from './standort'
import type {Kontext, Phase} from './typen'

/** Every phase in the order a call goes through them; the call always starts with the location. */
export const PHASEN: readonly Phase[] = [standort, abfrage, personalien]

/** A phase of this call with what it still misses. */
export interface Phasenstand {
    phase: Phase
    fehlend: string[]
}

/**
 * The phases of this call and what each still misses.
 *
 * @param eintraege the entries
 * @param kontext the graph and the call
 * @returns the active phases in order
 */
export function phasenstand(eintraege: Eintraege, kontext: Kontext): Phasenstand[] {
    return PHASEN.filter(phase => phase.aktiv(eintraege, kontext)).map(phase => ({phase, fehlend: phase.fehlend(eintraege, kontext)}))
}

/**
 * Everything still missing before the call is complete.
 *
 * @param eintraege the entries
 * @param kontext the graph and the call
 * @returns the catalogue keys of what is missing
 */
export function nochOffen(eintraege: Eintraege, kontext: Kontext): string[] {
    return phasenstand(eintraege, kontext).flatMap(stand => stand.fehlend)
}
