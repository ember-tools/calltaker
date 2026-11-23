import type {Abfragegraph} from './abfragegraph'
import {endergebnis, gewaehltesProtokoll} from './abfrageweg'
import type {Eintraege} from './eintraege'
import {reanimationFaellig} from './reanimation'

/** Where the handover to dispatch stands: not possible yet, possible, due now, or done. */
export type Uebergabebereitschaft = 'gesperrt' | 'bereit' | 'faellig' | 'erfolgt'

/** The parts of the entries that dispatch receives, and which can be added to afterwards. */
export type Nachtrag = 'ort' | 'anrufer' | 'betroffener' | 'hinweise' | 'code'

/**
 * Where the handover stands. It is possible once the location has a point and a protocol is
 * chosen, so an interim result exists. It is due for CPR once the beat runs or the code stands, for fire and
 * technical rescue once the location and protocol stand, and for other medical calls with a code.
 *
 * @param graph the graph
 * @param eintraege the entries
 * @returns the state
 */
export function uebergabestand(graph: Abfragegraph, eintraege: Eintraege): Uebergabebereitschaft {
    if (eintraege.uebergabe) return 'erfolgt'
    const pfad = eintraege.abfrage.pfad
    const ende = endergebnis(graph, eintraege.abfrage)
    if (!eintraege.ort.koordinaten || (!gewaehltesProtokoll(graph, pfad) && !ende)) return 'gesperrt'
    if (reanimationFaellig(graph, eintraege.abfrage)) return eintraege.reanimation.laeuft || ende ? 'faellig' : 'bereit'
    const medizinisch = pfad.find(schritt => schritt.knoten === graph.meta.wurzel)?.antwort === 'rd'
    return !medizinisch || ende ? 'faellig' : 'bereit'
}

/**
 * What the trainee changed after the handover, by the part dispatch would see it in.
 *
 * @param graph the graph
 * @param eintraege the entries
 * @returns the parts with additions, empty before the handover
 */
export function nachtraege(graph: Abfragegraph, eintraege: Eintraege): Set<Nachtrag> {
    const stand = eintraege.uebergeben
    const geaendert = new Set<Nachtrag>()
    if (!stand) return geaendert
    const gleich = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b)
    const ort = ({koordinaten, adresse, objekt, geschoss, klingel, anfahrt, gefahren, gefahrgut}: Eintraege['ort']) =>
        ({koordinaten, adresse, objekt, geschoss, klingel, anfahrt, gefahren, gefahrgut: gefahrgut?.un || gefahrgut?.gefahrenzahl ? gefahrgut : undefined})
    if (!gleich(ort(stand.ort), ort(eintraege.ort))) geaendert.add('ort')
    if (!gleich(stand.anrufer, eintraege.anrufer)) geaendert.add('anrufer')
    if (stand.betroffener !== eintraege.betroffener) geaendert.add('betroffener')
    if (stand.hinweise !== eintraege.hinweise) geaendert.add('hinweise')
    if (endergebnis(graph, stand.abfrage)?.code !== endergebnis(graph, eintraege.abfrage)?.code) geaendert.add('code')
    return geaendert
}
