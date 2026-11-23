import {normalisieren} from '../modell/rufnummer'
import type {Phase} from './typen'

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
}
