import type {Abfragegraph} from './abfragegraph'
import {endergebnis, istStillstand} from './abfrageweg'
import type {Abfrageeintrag, Eintraege, Schritteintrag} from './eintraege'

const TODESZEICHEN = {knoten: 'rd.09.todeszeichen', antwort: 'keine'}

/**
 * Whether CPR guidance is due: once the caller said there are no certain signs of death, or the
 * questioning reached a cardiac arrest code.
 *
 * @param graph the graph
 * @param abfrage the questioning so far
 * @returns true when the trainee should start CPR guidance
 */
export function reanimationFaellig(graph: Abfragegraph, abfrage: Abfrageeintrag): boolean {
    if (abfrage.pfad.some(s => s.knoten === TODESZEICHEN.knoten && s.antwort === TODESZEICHEN.antwort)) return true
    const ende = endergebnis(graph, abfrage)
    return Boolean(ende && istStillstand(ende.kategorie))
}

/**
 * Whether the trainee has to stay on the line: CPR guidance has started and the crews have not
 * arrived yet.
 *
 * @param eintraege the entries
 * @param eintreffenUm when the crews arrive, as the server says
 * @param jetzt the present
 * @returns true while the crews are on their way
 */
export function wartetAufKraefte(eintraege: Eintraege, eintreffenUm: number | undefined, jetzt: number): boolean {
    return eintraege.zeiten.reanimation !== undefined && (eintreffenUm === undefined || jetzt < eintreffenUm)
}

/** The age groups whose CPR steps differ. */
export type Altersgruppe = 'neugeborenes' | 'saeugling' | 'kind' | 'erwachsener'

export const ALTERSGRUPPEN: readonly Altersgruppe[] = ['neugeborenes', 'saeugling', 'kind', 'erwachsener']

/** The steps of each age group, as keys under `reanimation.schritte.<gruppe>`, in reading order. */
export const SCHRITTE: Record<Altersgruppe, readonly string[]> = {
    neugeborenes: ['lage', 'beatmung', 'pruefen', 'hand', 'druck', 'takt', 'weiter'],
    saeugling: ['lage', 'beatmung', 'hand', 'druck', 'takt', 'ohne', 'weiter', 'wechsel'],
    kind: ['lage', 'beatmung', 'hand', 'druck', 'takt', 'ohne', 'weiter', 'wechsel'],
    erwachsener: ['lage', 'frei', 'hand', 'druck', 'takt', 'weiter', 'wechsel', 'beatmung'],
}

/** Which group the steps are for, whether the questioning settled it, and the age it read. */
export interface Gruppenwahl {
    gruppe: Altersgruppe
    sicher: boolean
    alter?: string
}

const PFADALTER: Record<string, Altersgruppe> = {
    'bei-patientenalter-bis-30-tage': 'neugeborenes',
    'bei-patientenalter-bis-12-jahre': 'kind',
    'bei-patientenalter-aelter-12-jahre': 'erwachsener',
}
const GEBURT = /^rd\.24\b|schwangerschaft-geburt/

/**
 * The age group the CPR steps are for, first match wins: the age answers of the arrest protocol
 * ("bis 30 Tage", "bis 12 Jahre", "älter 12 Jahre") or a newborn arrest code, refined by a typed
 * baby's age; then the typed age alone; else adult steps, marked as not settled so the trainee
 * asks. The newborn steps are those right after a birth, so a baby up to 30 days old counts as a
 * newborn only when the call is about a birth, and otherwise as an infant.
 *
 * @param pfad the answers given, in order
 * @param kategorie the category of the code reached, if any
 * @returns the group, whether it is settled, and the typed age
 */
export function altersgruppe(pfad: readonly Schritteintrag[], kategorie?: string): Gruppenwahl {
    const alter = pfad.find(schritt => schritt.knoten === 'rd.alter')?.wert?.trim() || undefined
    const geburt = pfad.some(schritt => GEBURT.test(schritt.knoten) || GEBURT.test(schritt.antwort ?? ''))
    const ausAlter = alter ? gruppeAusAlter(alter, geburt) : undefined
    const baby: Altersgruppe = geburt ? 'neugeborenes' : 'saeugling'
    if (kategorie?.includes('NNAD')) return {gruppe: baby, sicher: true, alter}
    const gefunden = [...pfad].reverse().map(schritt => PFADALTER[schritt.antwort ?? '']).find(Boolean)
    const ausPfad = gefunden === 'neugeborenes' ? baby : gefunden
    if (ausPfad === 'kind' && ausAlter === 'saeugling') return {gruppe: 'saeugling', sicher: true, alter}
    if (ausPfad) return {gruppe: ausPfad, sicher: true, alter}
    if (ausAlter) return {gruppe: ausAlter, sicher: true, alter}
    return {gruppe: 'erwachsener', sicher: false, alter}
}

/**
 * The age group a typed age falls in: up to four weeks a newborn around a birth, else an infant;
 * under a year an infant; up to twelve a child; from thirteen an adult.
 *
 * @param text the typed age, such as "8 Monate", "3 Tage" or "54"
 * @param geburt whether the call is about a birth
 * @returns the group, or nothing when the text holds no number
 */
export function gruppeAusAlter(text: string, geburt: boolean): Altersgruppe | undefined {
    const zahl = /(\d+)/.exec(text)
    if (!zahl) return undefined
    const jahre = /(\d+)\s*jahr/i.exec(text)
    const wert = Number(zahl[1])
    if (jahre) return Number(jahre[1]) === 0 ? gruppeAusAlter(text.replace(jahre[0], ''), geburt) : Number(jahre[1]) <= 12 ? 'kind' : 'erwachsener'
    if (/\b(tag|woche)/i.test(text)) {
        const tage = /\bwoche/i.test(text) ? wert * 7 : wert
        return tage <= 28 && geburt ? 'neugeborenes' : 'saeugling'
    }
    if (/\bmonat/i.test(text)) return wert < 12 ? 'saeugling' : 'kind'
    if (wert === 0) return 'saeugling'
    return wert <= 12 ? 'kind' : 'erwachsener'
}

/**
 * The group whose steps the bar shows: the trainee's own choice, else the one the questioning
 * suggests.
 *
 * @param graph the graph
 * @param eintraege the entries
 * @returns the group in force, and how it was found
 */
export function wirksameGruppe(graph: Abfragegraph, eintraege: Eintraege): Gruppenwahl & {gewaehlt: boolean} {
    const vorschlag = altersgruppe(eintraege.abfrage.pfad, endergebnis(graph, eintraege.abfrage)?.kategorie)
    const gewaehlt = eintraege.reanimation.gruppe
    return gewaehlt ? {...vorschlag, gruppe: gewaehlt, sicher: true, gewaehlt: true} : {...vorschlag, gewaehlt: false}
}
