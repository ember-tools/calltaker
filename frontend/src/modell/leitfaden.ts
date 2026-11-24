import type {Abfragegraph} from './abfragegraph'
import {zeile} from './adresse'
import {anzeigen} from './rufnummer'
import type {Szenario} from './szenario'
import {istTafelfrage, tafelDerWahrheit} from './warntafel'

/** One bullet of the speaking guide: a catalogue key and its values. */
export interface Stichpunkt {
    schluessel: string
    werte?: Record<string, string>
}

const SELBST = '1-hand-der-anrufer-ist-selbst-betroffen'
const DABEI = '2-hand-der-anrufer-ist-beim-betroffenen'
const FUER_ANDERE = '3-hand-der-anrufer-meldet-fuer-andere'
const GEHOERT = '4-hand-der-anrufer-hat-es-nur-gehoert'
const AUTOMATISCH = 'automatische-meldung'

const TODESZEICHEN: [RegExp, string][] = [
    [/verwesung/i, 'leitfaden.todeszeichen.verwesung'],
    [/enthauptung/i, 'leitfaden.todeszeichen.enthauptung'],
    [/verkohlung/i, 'leitfaden.todeszeichen.verkohlung'],
    [/schwerste/i, 'leitfaden.todeszeichen.verletzungen'],
]

const VOR_ORT_ALLEIN: Record<string, string> = {
    'ja-der-anrufer-ist-vor-ort': 'leitfaden.wer.vorOrt',
    'nein-nicht-mehr-vor-ort': 'leitfaden.wer.nichtMehrOhne',
    'nein-war-nicht-vor-ort': 'leitfaden.wer.nieOhne',
}

/**
 * Who the caller is, as one sentence from the hand, whether they are on site and their
 * relationship to the affected person, so the two can never contradict each other. A scenario
 * written by hand without a hand answer still says whether the caller is there.
 *
 * @param szenario the scenario
 * @param rd whether the call is a medical one
 * @returns the bullet, or nothing when the opening names no hand
 */
export function werDuBist(szenario: Szenario, rd: boolean): Stichpunkt | undefined {
    const hand = szenario.antworten['eroeffnung.hand']?.antwort
    const vorOrt = szenario.antworten['eroeffnung.vor-ort']?.antwort
    const beziehung = szenario.anrufer.beziehung?.trim()
    if (hand === SELBST) return {schluessel: 'leitfaden.wer.selbst'}
    if (hand === AUTOMATISCH) return {schluessel: 'leitfaden.wer.automatisch'}
    const fall = vorOrt === 'unbekannt' ? 'unbekannt'
        : hand === DABEI ? (rd ? 'dabeiRd' : 'dabeiFw')
            : hand === FUER_ANDERE ? (vorOrt === 'nein-nicht-mehr-vor-ort' ? 'nichtMehr' : 'nie')
                : hand === GEHOERT ? 'gehoert' : ''
    if (!fall) {
        const allein = VOR_ORT_ALLEIN[vorOrt ?? '']
        return allein ? {schluessel: allein} : undefined
    }
    return beziehung ? {schluessel: `leitfaden.wer.${fall}`, werte: {beziehung}} : {schluessel: `leitfaden.wer.${fall}Ohne`}
}

/**
 * What the trainer, playing the caller, needs at hand, in the order the call goes: the call-taker
 * opens with "Notruf Feuerwehr und Rettungsdienst, wo ist der Notfallort?", so the place comes first, then
 * what happened in the caller's own words (the caller never names the Fachrichtung, the call-taker
 * decides it), the name when asked, what the caller knows and does not, who is affected, the plate,
 * what they have seen, a call-back number and how to sound. Built from the scenario alone.
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the bullets in speaking order
 */
export function leitfaden(graph: Abfragegraph, szenario: Szenario): Stichpunkt[] {
    const antworten = szenario.antworten
    const punkte: Stichpunkt[] = []
    const anlass = lageText(graph, szenario)
    const ohneAdresse = szenario.ort.ohneAdresse
    if (ohneAdresse) {
        punkte.push({schluessel: 'leitfaden.ohneAdresse', werte: {wo: ohneAdresse.wo}})
        for (const sicht of ohneAdresse.umgebung) {
            punkte.push({schluessel: 'leitfaden.umgebung', werte: {name: sicht.name, art: sicht.art, richtung: sicht.richtung, meter: String(sicht.meter)}})
        }
    } else {
        const ort = [zeile(szenario.ort.adresse), szenario.ort.objekt].filter(Boolean).join(', ')
        if (ort) punkte.push({schluessel: 'leitfaden.ort', werte: {ort}})
    }
    punkte.push({schluessel: 'leitfaden.lage', werte: {anlass}})
    punkte.push({schluessel: 'leitfaden.name', werte: {name: szenario.anrufer.name}})
    const rd = endpunktVon(graph, szenario)?.fachrichtung === 'rd'
    const wer = werDuBist(szenario, rd)
    if (wer) punkte.push(wer)
    const notizen = szenario.rolle.notizen.trim()
    if (notizen) punkte.push({schluessel: 'leitfaden.notizen', werte: {notizen}})
    const {geschoss, klingel, haustier} = szenario.ort
    if (geschoss || klingel) punkte.push({schluessel: 'leitfaden.wohnung', werte: {geschoss: geschoss || '-', klingel: klingel || '-'}})
    if (haustier) punkte.push({schluessel: 'leitfaden.haustier', werte: {haustier}})
    const person = [szenario.betroffener?.name, alterText(antworten['rd.alter']?.wert), geschlechtText(graph, antworten['rd.geschlecht']?.antwort)].filter(Boolean).join(', ')
    if (person) punkte.push({schluessel: 'leitfaden.betroffen', werte: {person}})
    punkte.push(...beobachtet(graph, szenario))
    const tafel = tafelDerWahrheit(graph, antworten)
    if (tafel) punkte.push({schluessel: 'leitfaden.tafel', werte: {oben: tafel.gefahrenzahl || '-', unten: tafel.un}})
    else if (Object.keys(antworten).some(id => istTafelfrage(graph, id))) punkte.push({schluessel: 'leitfaden.keineTafel'})
    const {rufnummer, rueckrufnummer} = szenario.anrufer
    if (rueckrufnummer && rueckrufnummer !== rufnummer) punkte.push({schluessel: 'leitfaden.rueckruf', werte: {nummer: anzeigen(rueckrufnummer)}})
    if (szenario.rolle.stimmung) punkte.push({schluessel: `leitfaden.stimmung.${szenario.rolle.stimmung}`})
    if (szenario.rolle.sprache) punkte.push({schluessel: 'leitfaden.sprache', werte: {sprache: szenario.rolle.sprache}})
    return punkte
}

/**
 * What happened, in words a caller could use: the code's reason, or where that is only the code
 * (as for many medical codes), the answers along the code's path, such as "Verbrennungen
 * (Verbrühungen) / Explosion (Detonation): GERINGFÜGIGE Verbrennungen".
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the situation, never a bare code
 */
export function lageText(graph: Abfragegraph, szenario: Szenario): string {
    const {knoten, code} = szenario.ziel
    const anlass = graph.knoten[knoten]?.anlass
    if (anlass && anlass !== code) return anlass
    const [protokoll, ...rest] = pfadLabels(graph, szenario).filter(label => !/^ohne weitere Angabe$/i.test(label))
    if (!protokoll) return szenario.titel
    return rest.length ? `${protokoll}: ${rest.join(', ')}` : protokoll
}

/**
 * What the caller has seen or feels beyond the situation itself, read from the answers after the
 * protocol choice (whose label names several situations at once): the signs of death they found,
 * an age they only guess, the headache and dizziness of carbon monoxide in the air they share,
 * and the breath a caller short of air speaks between.
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the bullets, possibly none
 */
function beobachtet(graph: Abfragegraph, szenario: Szenario): Stichpunkt[] {
    const punkte: Stichpunkt[] = []
    const pfad = pfadLabels(graph, szenario).slice(1).join(' ')
    const hand = szenario.antworten['eroeffnung.hand']?.antwort
    const vorOrt = szenario.antworten['eroeffnung.vor-ort']?.antwort
    const daneben = hand === SELBST || (hand === DABEI && vorOrt !== 'nein-nicht-mehr-vor-ort')
    if (szenario.ziel.code.startsWith('09B01')) {
        punkte.push({schluessel: TODESZEICHEN.find(([muster]) => muster.test(pfad))?.[1] ?? 'leitfaden.todeszeichen.kalt'})
    }
    const alter = szenario.antworten['rd.alter']?.wert?.trim() ?? ''
    if (/^etwa\b/i.test(alter)) punkte.push({schluessel: 'leitfaden.geschaetzt', werte: {alter}})
    if (/kohlenmonoxid/i.test(pfad) && !/automatischer alarm|ohne notfallleitsymptome/i.test(pfad) && daneben) punkte.push({schluessel: 'leitfaden.kohlenmonoxid'})
    if (/sprachschwierigkeiten zwischen atemzügen/i.test(pfad) && hand === SELBST) punkte.push({schluessel: 'leitfaden.abgehackt'})
    return punkte
}

/**
 * The answer labels along the path to the scenario's code.
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the labels in path order
 */
function pfadLabels(graph: Abfragegraph, szenario: Szenario): string[] {
    return (endpunktVon(graph, szenario)?.pfad ?? [])
        .map(schritt => graph.knoten[schritt.knoten]?.antworten?.find(antwort => antwort.id === schritt.antwort)?.label)
        .filter((label): label is string => Boolean(label))
}

/**
 * The end point the scenario aims at.
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the end point, if the graph has it
 */
function endpunktVon(graph: Abfragegraph, szenario: Szenario) {
    return graph.endpunkte.find(endpunkt => endpunkt.knoten === szenario.ziel.knoten)
}

const GESCHLECHT = {m: 'männlich', w: 'weiblich'} as const

/**
 * The affected person's sex as an adjective, from the answer given at the sex question.
 *
 * @param graph the graph
 * @param antwort the answer id given there, if any
 * @returns "männlich" or "weiblich", or nothing when the answer names no sex
 */
function geschlechtText(graph: Abfragegraph, antwort?: string): string {
    const geschlecht = graph.knoten['rd.geschlecht']?.antworten?.find(a => a.id === antwort)?.geschlecht
    return geschlecht ? GESCHLECHT[geschlecht] : ''
}

/**
 * An age as the caller says it.
 *
 * @param wert the typed age, if known
 * @returns "54 Jahre", or nothing
 */
function alterText(wert?: string): string {
    const alter = (wert ?? '').trim()
    return alter ? (/^\d+$/.test(alter) ? `${alter} Jahre` : alter) : ''
}
