import {anzeigen, gleich, normalisieren} from '../modell/rufnummer'
import type {Phase} from './typen'
import {vergleich, vergleichsform} from './vergleich'

/** A callback number needs at least this many digits to count as taken down. */
const ZIFFERN_MINDESTENS = 5

/**
 * The caller's details: the name, and a callback number, which confirming the shown number fills
 * in and which is typed when the caller gives another or the number is withheld.
 */
export const personalien: Phase = {
    id: 'personalien',
    titel: 'phase.personalien',
    aktiv: () => true,
    fehlend: eintraege => {
        const fehlt: string[] = []
        if (!eintraege.anrufer.name.trim()) fehlt.push('fehlt.name')
        if (normalisieren(eintraege.anrufer.rueckrufnummer).length < ZIFFERN_MINDESTENS) fehlt.push('fehlt.rueckrufnummer')
        return fehlt
    },
    bewerten: (eintraege, szenario) => {
        const wahrerName = szenario.anrufer.name
        const nachname = vergleichsform(wahrerName.split(' ').at(-1) ?? '')
        const erreichbar = szenario.anrufer.rueckrufnummer || szenario.anrufer.rufnummer || ''
        const name = wahrerName.trim()
            ? [vergleich('bewertung.name', wahrerName, eintraege.anrufer.name, ist => vergleichsform(ist) === vergleichsform(wahrerName) || vergleichsform(ist).includes(nachname))]
            : []
        return [
            ...name,
            vergleich('bewertung.rueckrufnummer', anzeigen(erreichbar), eintraege.anrufer.rueckrufnummer ? anzeigen(normalisieren(eintraege.anrufer.rueckrufnummer)) : '', ist => gleich(ist, erreichbar)),
        ]
    },
}
