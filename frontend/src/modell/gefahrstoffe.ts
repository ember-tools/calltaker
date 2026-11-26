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

/** Combinations that ADR 5.3.2.3.2 gives a meaning of their own instead of reading them digit by digit. */
const SPECIAL_COMBINATIONS: Record<string, string> = {
    '22': 'tiefgekühlt verflüssigtes Gas, erstickend',
    '323': 'entzündbarer flüssiger Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '333': 'pyrophorer flüssiger Stoff',
    '362': 'entzündbarer flüssiger Stoff, giftig, der mit Wasser reagiert und entzündbare Gase bildet',
    '382': 'entzündbarer flüssiger Stoff, ätzend, der mit Wasser reagiert und entzündbare Gase bildet',
    '423': 'fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '44': 'entzündbarer fester Stoff, der sich bei erhöhter Temperatur in geschmolzenem Zustand befindet',
    '446': 'entzündbarer fester Stoff, giftig, der sich bei erhöhter Temperatur in geschmolzenem Zustand befindet',
    '462': 'fester Stoff, giftig, der mit Wasser reagiert und entzündbare Gase bildet',
    '482': 'fester Stoff, ätzend, der mit Wasser reagiert und entzündbare Gase bildet',
    '539': 'entzündbares organisches Peroxid',
    '606': 'ansteckungsgefährlicher Stoff',
    '623': 'giftiger flüssiger Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '642': 'giftiger fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '823': 'ätzender flüssiger Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '842': 'ätzender fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
    '90': 'umweltgefährdender Stoff; verschiedene gefährliche Stoffe',
    '99': 'verschiedene gefährliche erwärmte Stoffe',
}

/** Special combinations whose ADR meaning changes when an X stands before them. */
const WATER_REACTIVE_COMBINATIONS: Record<string, string> = {
    '462': 'fester Stoff, der mit Wasser gefährlich reagiert und giftige Gase bildet',
    '482': 'fester Stoff, der mit Wasser gefährlich reagiert und ätzende Gase bildet',
}

const REFRIGERATED_GAS = 'tiefgekühlt verflüssigtes Gas'

const WATER_WARNING = 'reagiert gefährlich mit Wasser, kein Wasser verwenden'

/**
 * Reads the digits one by one: each names a danger, the first one the main danger, a doubled
 * first digit makes it stronger and a 0 only pads a single danger.
 *
 * @param ziffern the digits without a leading X
 * @returns the dangers in reading order
 */
function readDigits(ziffern: string): string[] {
    const gefahren: string[] = []
    const gesehen = new Set<string>()
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
 * Reads the digits by ADR 5.3.2.3: a special combination has its own meaning, 223 and 225 are a
 * refrigerated liquefied gas with one more danger, every other number is read digit by digit.
 *
 * @param ziffern the digits without a leading X
 * @param wasser whether an X stood before them
 * @returns the dangers in reading order
 */
function readCombination(ziffern: string, wasser: boolean): string[] {
    const special = (wasser ? WATER_REACTIVE_COMBINATIONS[ziffern] : undefined) ?? SPECIAL_COMBINATIONS[ziffern]
    if (special) return [special]
    if (ziffern.startsWith('22')) return [REFRIGERATED_GAS, ...readDigits(ziffern.slice(2))]
    return readDigits(ziffern)
}

/**
 * What a hazard number says, read by the ADR rules: each digit names a danger, the first one the
 * main danger; a doubled digit makes it stronger and a 0 only pads a single danger; the
 * combinations of ADR 5.3.2.3.2 such as 22, 44, 90 or 99 have a meaning of their own; a leading X
 * means it reacts dangerously with water.
 *
 * @param gefahrenzahl the number from the top of the plate
 * @returns the dangers in reading order, empty when the number cannot be read
 */
export function gefahrenzahlDeuten(gefahrenzahl: string): string[] {
    const zahl = gefahrenzahl.trim().toUpperCase()
    if (!GEFAHRENZAHL.test(zahl)) return []
    const wasser = zahl.startsWith('X')
    const ziffern = wasser ? zahl.slice(1) : zahl
    const gefahren = readCombination(ziffern, wasser)
    return wasser ? [WATER_WARNING, ...gefahren] : gefahren
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
