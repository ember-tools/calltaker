import type {Abfragegraph} from '../modell/abfragegraph'
import type {BewerteteEintraege, Eintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import {abfrage} from './abfrage'
import {anleitung} from './anleitung'
import {personalien} from './personalien'
import {standort} from './standort'
import type {Bewertung, Kontext, Phase} from './typen'

/** Every phase in the order a call goes through them; the call always starts with the location. */
export const PHASEN: readonly Phase[] = [standort, abfrage, personalien, anleitung]

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

/** A phase with how its entries compare with the truth. */
export interface Phasenbewertung {
    phase: Phase
    bewertungen: Bewertung[]
}

/**
 * How the entries of a call compare with its truth, phase by phase.
 *
 * @param eintraege the entries
 * @param szenario the truth
 * @param graph the graph
 * @returns each phase with its comparisons
 */
export function bewerten(eintraege: BewerteteEintraege, szenario: Szenario, graph: Abfragegraph): Phasenbewertung[] {
    return PHASEN.map(phase => ({phase, bewertungen: phase.bewerten(eintraege, szenario, graph)}))
}
