import type {Abfragegraph} from '../modell/abfragegraph'
import {endergebnis, istStillstand, schwere} from '../modell/abfrageweg'
import {reanimationFaellig} from '../modell/reanimation'
import type {Szenario} from '../modell/szenario'
import {pfadAusAntworten} from '../modell/szenarioentwurf'
import type {AnrufSicht} from '../modell/uebung'
import {dauer, type Zielzeiten} from '../modell/zeit'
import type {Bewertung, Phase} from './typen'

export type {Zielzeiten}

/** The target times until the trainer changes them. */
export const STANDARDZIELE: Zielzeiten = {reanimation: 120, uebergabe: 60}

/** How long after starting CPR guidance the call should be with dispatch. */
export const UEBERGABE_NACH_REANIMATION = 30

/**
 * A phase that exists only in the debrief: it is judged from the call's times, which the trainee's
 * live view does not judge.
 *
 * @param id the phase's id
 * @returns the phase
 */
function nurImDebrief(id: string): Phase {
    return {id, titel: `phase.${id}`, aktiv: () => false, fehlend: () => [], bewerten: () => []}
}

export const reanimationsphase = nurImDebrief('reanimation')
export const uebergabephase = nurImDebrief('uebergabe')

/**
 * Seconds from answering to a moment, when both are known.
 *
 * @param anruf the call
 * @param moment the moment
 * @returns the seconds, or undefined
 */
function abAnnahme(anruf: AnrufSicht, moment?: number): number | undefined {
    return anruf.angenommenUm === undefined || moment === undefined ? undefined : Math.max(0, moment - anruf.angenommenUm)
}

/**
 * Whether the truth calls for CPR: no signs of death, or a cardiac arrest code.
 *
 * @param graph the graph
 * @param szenario the truth
 * @returns true when CPR guidance was due
 */
export function reanimationLautWahrheit(graph: Abfragegraph, szenario: Szenario): boolean {
    const kategorie = graph.knoten[szenario.ziel.knoten]?.kategorie ?? ''
    return istStillstand(kategorie) || reanimationFaellig(graph, {pfad: pfadAusAntworten(graph, szenario.antworten)})
}

/**
 * CPR guidance against the truth: when it was due, how soon after answering it started, against
 * the target, or open while the call runs and wrong once it ended without; started though not
 * due, as a note.
 *
 * @param graph the graph
 * @param anruf the call
 * @param szenario the truth
 * @param ziele the target times
 * @returns the comparison
 */
export function reanimationBewerten(graph: Abfragegraph, anruf: AnrufSicht, szenario: Szenario, ziele: Zielzeiten): Bewertung[] {
    const start = abAnnahme(anruf, anruf.eintraege?.zeiten.reanimation)
    if (!reanimationLautWahrheit(graph, szenario)) {
        return start === undefined ? [] : [{feld: 'bewertung.reanimationUnnoetig', soll: '', ist: dauer(start), urteil: 'hinweis'}]
    }
    const soll = `≤ ${dauer(ziele.reanimation)}`
    if (start === undefined) return [{feld: 'bewertung.reanimation', soll, ist: '', urteil: anruf.zustand === 'beendet' ? 'falsch' : 'offen'}]
    return [{feld: 'bewertung.reanimation', soll, ist: dauer(start), urteil: start <= ziele.reanimation ? 'richtig' : 'teilweise'}, ...amTelefon(anruf)]
}

/**
 * Whether the trainee stayed on the line until the crews arrived, once the call has ended.
 *
 * @param anruf the call
 * @returns the comparison, or nothing while the call runs
 */
function amTelefon(anruf: AnrufSicht): Bewertung[] {
    if (anruf.zustand !== 'beendet' || anruf.beendetUm === undefined || anruf.eintreffenUm === undefined) return []
    return anruf.beendetUm < anruf.eintreffenUm
        ? [{feld: 'bewertung.vorEintreffen', soll: '', ist: '', urteil: 'falsch'}]
        : [{feld: 'bewertung.bisEintreffen', soll: '', ist: '', urteil: 'richtig'}]
}

/**
 * The Fachrichtung of the scenario's true code.
 *
 * @param graph the graph
 * @param szenario the truth
 * @returns its Fachrichtung, if the code is known
 */
function fachrichtungDerWahrheit(graph: Abfragegraph, szenario: Szenario): string | undefined {
    return graph.endpunkte.find(e => e.knoten === szenario.ziel.knoten)?.fachrichtung
}

/**
 * The target for handing over: shortly after starting CPR when the truth calls for it, the set
 * target for fire and technical rescue, none for other medical calls.
 *
 * @param graph the graph
 * @param anruf the call
 * @param szenario the truth
 * @param ziele the target times
 * @returns seconds from answering, or undefined without a target
 */
function uebergabeZiel(graph: Abfragegraph, anruf: AnrufSicht, szenario: Szenario, ziele: Zielzeiten): number | undefined {
    if (reanimationLautWahrheit(graph, szenario)) {
        const start = abAnnahme(anruf, anruf.eintraege?.zeiten.reanimation) ?? ziele.reanimation
        return start + UEBERGABE_NACH_REANIMATION
    }
    const fachrichtung = fachrichtungDerWahrheit(graph, szenario)
    return fachrichtung && fachrichtung !== 'rd' ? ziele.uebergabe : undefined
}

/**
 * The handover to dispatch: how soon after answering, against the target; what was missing at
 * that moment; a code raised afterwards. Without a handover, the end of the call counts as one.
 *
 * @param graph the graph
 * @param anruf the call
 * @param szenario the truth
 * @param ziele the target times
 * @returns the comparison
 */
export function uebergabeBewerten(graph: Abfragegraph, anruf: AnrufSicht, szenario: Szenario, ziele: Zielzeiten): Bewertung[] {
    const eintraege = anruf.eintraege
    const uebergeben = abAnnahme(anruf, eintraege?.zeiten.uebergabe)
    const zeit = uebergeben ?? abAnnahme(anruf, anruf.beendetUm)
    const ziel = uebergabeZiel(graph, anruf, szenario, ziele)
    const bewertungen: Bewertung[] = []
    if (uebergeben === undefined) bewertungen.push({feld: 'bewertung.uebergabeOhne', soll: '', ist: '', urteil: 'hinweis'})
    if (zeit !== undefined) {
        const urteil = ziel === undefined ? 'hinweis' : zeit <= ziel ? 'richtig' : 'teilweise'
        bewertungen.push({feld: 'bewertung.uebergabe', soll: ziel === undefined ? '' : `≤ ${dauer(ziel)}`, ist: dauer(zeit), urteil})
    }
    const stand = eintraege?.uebergeben
    if (!stand) return bewertungen
    if (!stand.ort.koordinaten) bewertungen.push({feld: 'bewertung.uebergabeOhnePunkt', soll: '', ist: '', urteil: 'falsch'})
    const damals = endergebnis(graph, stand.abfrage)
    const medizinisch = fachrichtungDerWahrheit(graph, szenario) === 'rd'
    if (medizinisch && !reanimationLautWahrheit(graph, szenario) && !damals) bewertungen.push({feld: 'bewertung.uebergabeOhneCode', soll: '', ist: '', urteil: 'falsch'})
    const jetzt = eintraege ? endergebnis(graph, eintraege.abfrage) : undefined
    if (damals && jetzt && schwere(jetzt.kategorie) > schwere(damals.kategorie)) {
        bewertungen.push({feld: 'bewertung.verschaerft', soll: '', ist: `${damals.code} → ${jetzt.code}`, urteil: 'hinweis'})
    }
    return bewertungen
}
