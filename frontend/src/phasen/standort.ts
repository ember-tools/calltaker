import type {Phase} from './typen'

/** The location: where the emergency is, as a point on the map. */
export const standort: Phase = {
    id: 'standort',
    titel: 'phase.standort',
    aktiv: () => true,
    fehlend: eintraege => (eintraege.ort.koordinaten ? [] : ['fehlt.einsatzort']),
}
