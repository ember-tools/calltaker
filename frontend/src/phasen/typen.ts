import type {Abfragegraph} from '../modell/abfragegraph'
import type {Eintraege} from '../modell/eintraege'
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
}
