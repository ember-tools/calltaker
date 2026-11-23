import type {Abfragegraph} from '../modell/abfragegraph'
import type {Eintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import type {AnrufSicht} from '../modell/uebung'

/** What a phase may look at besides the entries: the graph and the call as the trainee sees it. */
export interface Kontext {
    graph: Abfragegraph
    anruf: AnrufSicht
}

/**
 * One section of a call. Phases read only the trainee's entries, never the truth, so the
 * trainee's own view can tell what is complete.
 */
export interface Phase {
    id: string
    /** The catalogue key of the phase's name. */
    titel: string
    /** Whether the phase belongs to this call at all. */
    aktiv(eintraege: Eintraege, kontext: Kontext): boolean
    /** The catalogue keys of what is still missing; empty once the phase is complete. */
    fehlend(eintraege: Eintraege, kontext: Kontext): string[]
    /** How the entries compare with the truth; for the trainer and the debrief, never the trainee's live view. */
    bewerten(eintraege: Eintraege, szenario: Szenario, graph: Abfragegraph): Bewertung[]
}

/**
 * How one entry compares with the truth: right, partly right, wrong, or not entered yet; or a
 * note that is shown but not judged, such as the reason for cancelling.
 */
export type Urteil = 'richtig' | 'teilweise' | 'falsch' | 'offen' | 'hinweis'

/** One entry compared with the truth. */
export interface Bewertung {
    /** The catalogue key of what is compared. */
    feld: string
    soll: string
    ist: string
    urteil: Urteil
    /** For a point: how far the entered one lies from the true one, in metres. */
    abstand?: number
    /** For a code: how close it comes to the true one. */
    stufe?: Codestufe
}

/**
 * How close an entered code comes to the true one: the same code, the same protocol (as the code
 * index assigns it), or the same emergency category, which alerts the same resources.
 */
export type Codestufe = 'exakt' | 'protokoll' | 'kategorie' | 'falsch'
