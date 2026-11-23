import {endergebnis} from '../modell/abfrageweg'
import type {Abfragegraph} from '../modell/abfragegraph'
import {faellige} from '../modell/anleitungen'
import type {Eintraege} from '../modell/eintraege'
import {pfadAusAntworten} from '../modell/szenarioentwurf'
import type {Bewertung, Phase} from './typen'

/**
 * The instructions due by the trainee's own questioning so far.
 *
 * @param graph the graph
 * @param eintraege the entries
 * @returns the due instructions
 */
export function faelligNachEintraegen(graph: Abfragegraph, eintraege: Eintraege) {
    return faellige(graph, eintraege.abfrage.pfad, endergebnis(graph, eintraege.abfrage)?.kategorie)
}

/**
 * The instructions to the caller: the ones due by the questioning, ticked off as they are given.
 * Compared with the truth, every required instruction the truth makes due counts, and a ticked
 * one the truth rules out, such as staying in a flat whose way out is clear, counts as wrong. One
 * the trainer took back keeps its row, as right, so the correction can be undone.
 */
export const anleitung: Phase = {
    id: 'anleitung',
    titel: 'phase.anleitung',
    aktiv: (eintraege, {graph}) => faelligNachEintraegen(graph, eintraege).length > 0,
    fehlend: (eintraege, {graph}) => {
        const gegeben = new Set(eintraege.anleitung.gegeben)
        return faelligNachEintraegen(graph, eintraege).some(a => a.pflicht && !gegeben.has(a.id)) ? ['fehlt.anleitung'] : []
    },
    bewerten: (eintraege, szenario, graph) => {
        const gegeben = new Set(eintraege.anleitung.gegeben)
        const wahrheit = faellige(graph, pfadAusAntworten(graph, szenario.antworten), graph.knoten[szenario.ziel.knoten]?.kategorie)
        const ausgeschlossen = new Set(wahrheit.flatMap(a => a.schliesstAus ?? []))
        const abgewaehlt = new Set(eintraege.anleitung.abgewaehlt ?? [])
        const pflicht: Bewertung[] = wahrheit.filter(a => a.pflicht).map(a => ({
            feld: 'bewertung.anleitung', beschriftung: a.titel, anleitung: a.id, gegeben: gegeben.has(a.id),
            soll: a.titel, ist: gegeben.has(a.id) ? a.titel : '', urteil: gegeben.has(a.id) ? 'richtig' : 'offen',
        }))
        const unpassend: Bewertung[] = (graph.anleitungen ?? [])
            .filter(a => ausgeschlossen.has(a.id) && (gegeben.has(a.id) || abgewaehlt.has(a.id)))
            .map(a => ({
                feld: 'bewertung.anleitung', beschriftung: a.titel, anleitung: a.id, gegeben: gegeben.has(a.id),
                soll: '', ist: gegeben.has(a.id) ? a.titel : '', urteil: gegeben.has(a.id) ? 'falsch' : 'richtig',
            }))
        return [...pflicht, ...unpassend]
    },
}
