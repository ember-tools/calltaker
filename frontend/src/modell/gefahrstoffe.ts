/** One entry of the list of UN numbers. */
export interface Stoff {
    un: string
    gefahrenzahl: string
    klasse: string
    bezeichnung: string
}

/** The list with where it comes from. */
export interface Gefahrstoffliste {
    herkunft: {quelle?: string, lizenz?: string, stand?: string}
    stoffe: Stoff[]
}

/** An orange plate: hazard number on top, UN number below. */
export interface Warntafel {
    un: string
    gefahrenzahl: string
}

/** A hazard number as a plate shows it: two or three digits, perhaps after an X. */
export const GEFAHRENZAHL = /^X?\d{2,3}$/

const ZIFFERN: Record<string, string> = {
    '2': 'Gas, Druck oder chemische Reaktion',
    '3': 'entzündbar (Flüssigkeit oder Gas)',
    '4': 'entzündbarer fester Stoff',
    '5': 'oxidierend, brandfördernd',
    '6': 'giftig',
    '7': 'radioaktiv',
    '8': 'ätzend',
    '9': 'Gefahr einer spontanen heftigen Reaktion',
}

/**
 * What a hazard number says, read by the ADR rules: each digit names a danger, the first one the
 * main danger; a doubled digit makes it stronger, except 22 for a refrigerated liquefied gas; a
 * leading X means it reacts dangerously with water.
 *
 * @param gefahrenzahl the number from the top of the plate
 * @returns the dangers in reading order, empty when the number cannot be read
 */
export function gefahrenzahlDeuten(gefahrenzahl: string): string[] {
    const zahl = gefahrenzahl.trim().toUpperCase()
    if (!GEFAHRENZAHL.test(zahl)) return []
    const wasser = zahl.startsWith('X')
    const ziffern = wasser ? zahl.slice(1) : zahl
    const gefahren: string[] = []
    if (wasser) gefahren.push('reagiert gefährlich mit Wasser, kein Wasser verwenden')
    const gesehen = new Set<string>()
    if (ziffern.startsWith('22')) {
        gefahren.push('tiefgekühlt verflüssigtes Gas')
        gesehen.add('2')
    }
    for (const ziffer of ziffern) {
        if (gesehen.has(ziffer)) continue
        gesehen.add(ziffer)
        const bedeutung = ZIFFERN[ziffer]
        if (!bedeutung) continue
        gefahren.push(ziffern[0] === ziffer && ziffern[1] === ziffer ? `stark ${bedeutung}` : bedeutung)
    }
    return gefahren
}

/**
 * The entries for a UN number.
 *
 * @param stoffe the list
 * @param un the number
 * @returns every entry with that number
 */
export function stoffeZu(stoffe: Stoff[], un: string): Stoff[] {
    const nummer = un.trim()
    return /^\d{4}$/.test(nummer) ? stoffe.filter(stoff => stoff.un === nummer) : []
}

/**
 * The hazard numbers a UN number can carry on a plate, by the list.
 *
 * @param stoffe the list
 * @param un the UN number
 * @returns each distinct plate number, in list order
 */
export function gefahrenzahlenZu(stoffe: Stoff[], un: string): string[] {
    return [...new Set(stoffeZu(stoffe, un).map(stoff => stoff.gefahrenzahl).filter(zahl => GEFAHRENZAHL.test(zahl)))]
}

/**
 * Entries whose name contains the text, for typing a name instead of a number.
 *
 * @param stoffe the list
 * @param text what was typed
 * @param hoechstens how many to return
 * @returns the matches, those starting with the text first
 */
export function stoffeSuchen(stoffe: Stoff[], text: string, hoechstens = 8): Stoff[] {
    const suche = text.trim().toLowerCase()
    if (suche.length < 2) return []
    const treffer = stoffe.filter(stoff => stoff.bezeichnung.toLowerCase().includes(suche))
    const vorn = (stoff: Stoff) => (stoff.bezeichnung.toLowerCase().startsWith(suche) ? 0 : 1)
    return [...treffer].sort((a, b) => vorn(a) - vorn(b)).slice(0, hoechstens)
}
