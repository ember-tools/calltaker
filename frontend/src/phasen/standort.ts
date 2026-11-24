import {zeile} from '../modell/adresse'
import type {Eintraege} from '../modell/eintraege'
import {abstandGerundet} from '../modell/karte'
import {tafelDerWahrheit, tafelImPfad} from '../modell/warntafel'
import type {Abfragegraph} from '../modell/abfragegraph'
import {fachrichtungImPfad, gewaehltesProtokoll} from '../modell/abfrageweg'
import type {Szenario} from '../modell/szenario'
import type {Bewertung, Phase} from './typen'
import {vergleich, vergleichsform} from './vergleich'

export {zeile}

/** An entered point this close to the true one counts as right. */
export const PUNKT_GENAU_METER = 75

/**
 * The entered point compared with the true one, by distance.
 *
 * @param eintraege the entries
 * @param szenario the truth
 * @returns the comparison, or nothing when the truth has no point
 */
function punkt(eintraege: Eintraege, szenario: Szenario): Bewertung[] {
    const wahr = szenario.ort.koordinaten
    if (!wahr) return []
    const erfasst = eintraege.ort.koordinaten
    if (!erfasst) return [{feld: 'bewertung.punkt', soll: '', ist: '', urteil: 'offen'}]
    const abstand = abstandGerundet(wahr, erfasst)
    return [{feld: 'bewertung.punkt', soll: '', ist: '', urteil: abstand <= PUNKT_GENAU_METER ? 'richtig' : 'falsch', abstand}]
}

/**
 * Whether the trainee has a home address but neither floor nor doorbell yet: a medical call, or
 * a fire or rescue protocol that plays inside a home.
 *
 * @param graph the graph
 * @param eintraege the entries
 * @returns true while floor and doorbell are still to be asked
 */
export function wohnungOhneGeschoss(graph: Abfragegraph, eintraege: Eintraege): boolean {
    const {adresse, objekt, geschoss, klingel} = eintraege.ort
    if (!adresse.hausnummer.trim() || objekt.trim() || geschoss.trim() || klingel.trim()) return false
    const medizinisch = fachrichtungImPfad(graph, eintraege.abfrage.pfad) === 'rd'
    const protokoll = gewaehltesProtokoll(graph, eintraege.abfrage.pfad)?.protokoll ?? ''
    return medizinisch || (graph.wohnungsprotokolle ?? []).includes(protokoll)
}

/**
 * Whether the trainee noted the pet among the dangers at the place; shown, not judged as wrong.
 *
 * @param haustier the pet as the truth names it
 * @param gefahren what the trainee entered as dangers
 * @returns the comparison
 */
function haustierErwaehnt(haustier: string, gefahren: string): Bewertung {
    const bekannt = /hund|katze|schlange/i.exec(haustier)?.[0]
    const tier = vergleichsform(bekannt ?? haustier.trim().split(/\s+/).at(-1) ?? '')
    return {feld: 'bewertung.haustier', soll: haustier, ist: gefahren, urteil: tier && vergleichsform(gefahren).includes(tier) ? 'richtig' : 'hinweis'}
}

/** The location: where the emergency is, as a point on the map. */
export const standort: Phase = {
    id: 'standort',
    titel: 'phase.standort',
    aktiv: () => true,
    fehlend: (eintraege, {graph}) => [
        ...(eintraege.ort.koordinaten ? [] : ['fehlt.einsatzort']),
        ...(wohnungOhneGeschoss(graph, eintraege) ? ['fehlt.geschossKlingel'] : []),
    ],
    bewerten: (eintraege, szenario, graph) => {
        const wahr = szenario.ort
        const bewertungen: Bewertung[] = []
        if (wahr.adresse.strasse) {
            const erfasst = eintraege.ort.adresse
            const passt = () => vergleichsform(erfasst.strasse) === vergleichsform(wahr.adresse.strasse) && vergleichsform(erfasst.hausnummer) === vergleichsform(wahr.adresse.hausnummer)
            bewertungen.push(vergleich('bewertung.adresse', zeile(wahr.adresse), zeile(eintraege.ort.adresse), passt))
        } else if (wahr.objekt) {
            bewertungen.push(vergleich('bewertung.objekt', wahr.objekt, eintraege.ort.objekt, ist => vergleichsform(ist).includes(vergleichsform(wahr.objekt))))
        }
        bewertungen.push(...punkt(eintraege, szenario))
        const tafel = tafelDerWahrheit(graph, szenario.antworten)
        if (tafel) bewertungen.push(vergleich('bewertung.gefahrgut', tafel.un, tafelImPfad(graph, eintraege.abfrage.pfad)?.un ?? '', ist => ist === tafel.un))
        if (wahr.geschoss) bewertungen.push(vergleich('bewertung.geschoss', wahr.geschoss, eintraege.ort.geschoss, ist => vergleichsform(ist) === vergleichsform(wahr.geschoss)))
        if (wahr.klingel) bewertungen.push(vergleich('bewertung.klingel', wahr.klingel, eintraege.ort.klingel, ist => vergleichsform(ist).includes(vergleichsform(wahr.klingel))))
        if (wahr.haustier) bewertungen.push(haustierErwaehnt(wahr.haustier, eintraege.ort.gefahren))
        return bewertungen
    },
}
