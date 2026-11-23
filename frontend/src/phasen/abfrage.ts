import {endergebnis} from '../modell/abfrageweg'
import type {Phase} from './typen'
import {vergleich} from './vergleich'

/** The questioning: through the graph until it reaches a code. */
export const abfrage: Phase = {
    id: 'abfrage',
    titel: 'phase.abfrage',
    aktiv: () => true,
    fehlend: (eintraege, {graph}) => (endergebnis(graph, eintraege.abfrage) ? [] : ['fehlt.code']),
    bewerten: (eintraege, szenario, graph) => {
        const ziel = szenario.ziel
        const erreicht = endergebnis(graph, eintraege.abfrage)
        const anzeige = (code: string, knoten: string) => [code, graph.knoten[knoten]?.kategorie].filter(Boolean).join(' · ')
        return [vergleich('bewertung.code', anzeige(ziel.code, ziel.knoten), erreicht ? anzeige(erreicht.code, erreicht.knoten) : '', () => erreicht?.knoten === ziel.knoten || erreicht?.code === ziel.code)]
    },
}
