import type {Bewertung, Urteil} from './typen'

/** Letters of other alphabets that no accent removal turns into German ones. */
const FREMDE_BUCHSTABEN: Record<string, string> = {ı: 'i', ł: 'l', ø: 'o', æ: 'ae', œ: 'oe', đ: 'd', ð: 'd', þ: 'th', ħ: 'h', ŋ: 'n', ß: 'ss'}

/** Kölner Phonetik codes of the letters whose sound does not depend on their neighbours. */
const KOELN: Record<string, string> = {
    a: '0', e: '0', i: '0', j: '0', o: '0', u: '0', y: '0',
    b: '1', f: '3', v: '3', w: '3', g: '4', k: '4', q: '4', l: '5', m: '6', n: '6', r: '7', s: '8', z: '8',
}

/**
 * A text in German letters, as a trainee types what a caller spells: umlauts as "ae", "oe", "ue",
 * accents dropped ("é" as "e", "ş" as "s") and letters of other alphabets replaced ("ı" as "i",
 * "ł" as "l", "ß" as "ss").
 *
 * @param text the text
 * @returns the text in lower-case German letters
 */
export function deutscheBuchstaben(text: string): string {
    return text.toLowerCase()
        .replaceAll('ä', 'ae').replaceAll('ö', 'oe').replaceAll('ü', 'ue')
        .normalize('NFD').replace(/\p{M}+/gu, '')
        .replace(/[ıłøæœđðþħŋß]/g, buchstabe => FREMDE_BUCHSTABEN[buchstabe] ?? buchstabe)
}

/**
 * A text in the form names and streets are compared in: German letters, lower case, without
 * punctuation and spacing, with "str." read as "straße".
 *
 * @param text the text
 * @returns its compared form
 */
export function vergleichsform(text: string): string {
    return deutscheBuchstaben(text.replace(/str\.?(?=\s|$)/gi, 'strasse')).replace(/[^\p{L}\p{N}]+/gu, '')
}

/**
 * The code of one letter, which for some letters depends on its neighbours.
 *
 * @param zeichen the word
 * @param stelle the letter's position
 * @returns its digits, empty for silent letters
 */
function laut(zeichen: string, stelle: number): string {
    const buchstabe = zeichen[stelle]!
    const vorher = zeichen[stelle - 1] ?? ''
    const nachher = zeichen[stelle + 1] ?? ''
    if (buchstabe === 'd' || buchstabe === 't') return nachher && 'csz'.includes(nachher) ? '8' : '2'
    if (buchstabe === 'p') return nachher === 'h' ? '3' : '1'
    if (buchstabe === 'x') return vorher && 'ckq'.includes(vorher) ? '8' : '48'
    if (buchstabe === 'c') {
        if (stelle === 0) return nachher && 'ahkloqrux'.includes(nachher) ? '4' : '8'
        return (vorher && 'sz'.includes(vorher)) || !nachher || !'ahkoqux'.includes(nachher) ? '8' : '4'
    }
    return KOELN[buchstabe] ?? ''
}

/**
 * The Kölner Phonetik code of a word: digits for its sounds, so names spelled differently but
 * sounding alike, such as "Meier" and "Mayer" or "Yılmaz" and "Yilmas", share one.
 *
 * @param wort the word
 * @returns its code, empty when it has no letters
 */
export function phonetik(wort: string): string {
    const zeichen = vergleichsform(wort).replace(/[^a-z]/g, '')
    let code = ''
    for (let stelle = 0; stelle < zeichen.length; stelle++) {
        const wert = laut(zeichen, stelle)
        if (wert && code.at(-1) !== wert[0]) code += wert
        else if (wert.length > 1) code += wert.slice(1)
    }
    return code ? code[0] + code.slice(1).replaceAll('0', '') : ''
}

/**
 * Whether a noted name fits the correct one: the same name, the last name alone, or a word that
 * sounds like the last name, as names are noted from what the caller says.
 *
 * @param ist the name noted
 * @param soll the correct name
 * @returns true when it fits
 */
export function nameGleich(ist: string, soll: string): boolean {
    const nachname = soll.trim().split(/\s+/).at(-1) ?? ''
    const form = vergleichsform(nachname)
    if (vergleichsform(ist) === vergleichsform(soll) || (form && vergleichsform(ist).includes(form))) return true
    const klang = phonetik(nachname)
    return Boolean(klang) && ist.split(/[\s,;-]+/).some(wort => phonetik(wort) === klang)
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
