import {endergebnis} from '../modell/abfrageweg'
import type {Phase} from './typen'

/** The questioning: through the graph until it reaches a code. */
export const abfrage: Phase = {
    id: 'abfrage',
    titel: 'phase.abfrage',
    aktiv: () => true,
    fehlend: (eintraege, {graph}) => (endergebnis(graph, eintraege.abfrage) ? [] : ['fehlt.code']),
}
