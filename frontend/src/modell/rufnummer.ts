const LANDESVORWAHL = '49'
const BERLIN = '4930'
const MOBIL = /^491[5-7]\d/

/**
 * A number typed in any common way as digits with the country code, as the server stores it:
 * `0176 1234567`, `+49 176 1234567`, `+49 (0)176 1234567` and `0049-176-1234567` all become
 * `491761234567`.
 *
 * @param text what was typed
 * @returns the digits with the country code
 */
export function normalisieren(text: string): string {
    let ziffern = text.replaceAll('(0)', '').replace(/\D/g, '')
    if (ziffern.startsWith('00')) ziffern = ziffern.slice(2)
    else if (ziffern.startsWith('0')) ziffern = LANDESVORWAHL + ziffern.slice(1)
    if (ziffern.startsWith(`${LANDESVORWAHL}0`)) ziffern = LANDESVORWAHL + ziffern.slice(LANDESVORWAHL.length + 1)
    return ziffern
}

/**
 * A stored number grouped as people read it: `030 12345678`, `0176 1234567`.
 *
 * @param nummer digits with the country code
 * @returns the number for display
 */
export function anzeigen(nummer: string): string {
    if (!nummer) return ''
    if (!nummer.startsWith(LANDESVORWAHL)) return `+${nummer}`
    const national = `0${nummer.slice(LANDESVORWAHL.length)}`
    if (nummer.startsWith(BERLIN)) return `${national.slice(0, 3)} ${national.slice(3)}`
    if (MOBIL.test(nummer)) return `${national.slice(0, 4)} ${national.slice(4)}`
    return national
}

/**
 * Whether two numbers, however typed, are the same.
 *
 * @param a one number
 * @param b the other
 * @returns true when both normalise to the same digits
 */
export function gleich(a: string, b: string): boolean {
    return normalisieren(a) === normalisieren(b)
}
