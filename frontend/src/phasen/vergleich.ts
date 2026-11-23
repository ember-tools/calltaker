import type {Bewertung, Urteil} from './typen'

/**
 * A text in the form names and streets are compared in: lower case, without punctuation and
 * spacing, with "str." read as "straße" and "ß" as "ss".
 *
 * @param text the text
 * @returns its compared form
 */
export function vergleichsform(text: string): string {
    return text.toLowerCase().replace(/str\.?(?=\s|$)/g, 'strasse').replaceAll('ß', 'ss').replace(/[^\p{L}\p{N}]+/gu, '')
}

/**
 * Compares an entry with the truth: open while nothing is entered, otherwise by the test given.
 *
 * @param feld the catalogue key of what is compared
 * @param soll the truth as shown
 * @param ist the entry as shown
 * @param passt whether the entry fits the truth
 * @returns the comparison
 */
export function vergleich(feld: string, soll: string, ist: string, passt: (ist: string) => boolean): Bewertung {
    const urteil: Urteil = !ist.trim() ? 'offen' : passt(ist) ? 'richtig' : 'falsch'
    return {feld, soll, ist, urteil}
}
