import type {Abfragegraph} from '../modell/abfragegraph'
import {leereEintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import type {AnrufSicht} from '../modell/uebung'
import {vergleichePfad, type Pfadvergleich} from '../modell/wahrheitspfad'
import {bewerten, nochOffen, type Phasenbewertung} from './register'

/** The times of a call in seconds; a step not reached stays undefined. */
export interface Gespraechszeiten {
    /** From ringing to accepting. */
    annahme?: number
    /** From accepting to the location having a point. */
    adresse?: number
    /** From accepting to a code. */
    code?: number
    /** From accepting to ending. */
    gespraech?: number
}

/** Everything the debrief of one call shows. */
export interface Debrief {
    phasen: Phasenbewertung[]
    pfad: Pfadvergleich
    zeiten: Gespraechszeiten
    /** What was still missing when the call was ended, as catalogue keys. */
    fehlend: string[]
}

/**
 * A span between two moments, when both are known.
 *
 * @param von the start
 * @param bis the end
 * @returns the seconds between them, or undefined
 */
function spanne(von?: number, bis?: number): number | undefined {
    return von === undefined || bis === undefined ? undefined : Math.max(0, bis - von)
}

/**
 * The times of a call: ringing to accepting, accepting to the location, to the code, and the
 * length of the conversation. The location and code moments are the server's, stamped when they
 * were first entered.
 *
 * @param anruf the call
 * @returns its times
 */
export function zeitenVon(anruf: AnrufSicht): Gespraechszeiten {
    const zeiten = anruf.eintraege?.zeiten ?? {}
    return {
        annahme: spanne(anruf.klingeltSeit, anruf.angenommenUm),
        adresse: spanne(anruf.angenommenUm, zeiten.adresse),
        code: spanne(anruf.angenommenUm, zeiten.code),
        gespraech: spanne(anruf.angenommenUm, anruf.beendetUm),
    }
}

/**
 * The debrief of a call: each phase's entries against the truth, the path against the truth path
 * with its first branch, the times, and what was missing when it ended.
 *
 * @param graph the graph
 * @param anruf the call as the trainee sees it
 * @param szenario its truth
 * @returns the debrief
 */
export function debrief(graph: Abfragegraph, anruf: AnrufSicht, szenario: Szenario): Debrief {
    const eintraege = anruf.eintraege ?? leereEintraege()
    return {
        phasen: bewerten(eintraege, szenario, graph),
        pfad: vergleichePfad(graph, szenario.antworten, eintraege.abfrage.pfad),
        zeiten: zeitenVon(anruf),
        fehlend: nochOffen(eintraege, {graph, anruf}),
    }
}
