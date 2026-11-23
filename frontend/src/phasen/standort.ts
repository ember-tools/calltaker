import type {Eintraege} from '../modell/eintraege'
import {abstandGerundet} from '../modell/karte'
import type {Adresse, Szenario} from '../modell/szenario'
import type {Bewertung, Phase} from './typen'
import {vergleich, vergleichsform} from './vergleich'

/** An entered point this close to the true one counts as right. */
export const PUNKT_GENAU_METER = 75

/**
 * An address as one line.
 *
 * @param adresse the address
 * @returns street and number, postcode and Ortsteil
 */
export function zeile(adresse: Adresse): string {
    const strasse = `${adresse.strasse} ${adresse.hausnummer}`.trim()
    return [strasse, `${adresse.plz} ${adresse.ortsteil}`.trim()].filter(Boolean).join(', ')
}

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

/** The location: where the emergency is, as a point on the map. */
export const standort: Phase = {
    id: 'standort',
    titel: 'phase.standort',
    aktiv: () => true,
    fehlend: eintraege => (eintraege.ort.koordinaten ? [] : ['fehlt.einsatzort']),
    bewerten: (eintraege, szenario) => {
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
        if (wahr.geschoss) bewertungen.push(vergleich('bewertung.geschoss', wahr.geschoss, eintraege.ort.geschoss, ist => vergleichsform(ist) === vergleichsform(wahr.geschoss)))
        return bewertungen
    },
}
