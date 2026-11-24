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

const HAND: Record<string, string> = {
    '1-hand-der-anrufer-ist-selbst-betroffen': 'leitfaden.hand.selbst',
    '2-hand-der-anrufer-ist-beim-betroffenen': 'leitfaden.hand.dabei',
    '3-hand-der-anrufer-meldet-fuer-andere': 'leitfaden.hand.fuerAndere',
    '4-hand-der-anrufer-hat-es-nur-gehoert': 'leitfaden.hand.gehoert',
    'automatische-meldung': 'leitfaden.hand.automatisch',
}

const VOR_ORT: Record<string, string> = {
    'ja-der-anrufer-ist-vor-ort': 'leitfaden.vorOrt.ja',
    'nein-nicht-mehr-vor-ort': 'leitfaden.vorOrt.nichtMehr',
    'nein-war-nicht-vor-ort': 'leitfaden.vorOrt.nie',
    'unbekannt': 'leitfaden.vorOrt.unklar',
}

/**
 * What the trainer, playing the caller, needs at hand, in the order the call goes: the call-taker
 * opens with "Notruf Feuerwehr und Rettungsdienst, wo ist der Notfallort?", so the place comes first, then
 * what happened in the caller's own words (the caller never names the Fachrichtung, the call-taker
 * decides it), the name when asked, what the caller knows and does not, who is affected, the plate,
 * a call-back number and how to sound. Built from the scenario alone.
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
    const hand = HAND[antworten['eroeffnung.hand']?.antwort ?? '']
    if (hand) punkte.push({schluessel: hand})
    const vorOrt = VOR_ORT[antworten['eroeffnung.vor-ort']?.antwort ?? '']
    if (vorOrt) punkte.push({schluessel: vorOrt})
    const {geschoss, klingel, haustier} = szenario.ort
    if (geschoss || klingel) punkte.push({schluessel: 'leitfaden.wohnung', werte: {geschoss: geschoss || '-', klingel: klingel || '-'}})
    if (haustier) punkte.push({schluessel: 'leitfaden.haustier', werte: {haustier}})
    const person = [szenario.betroffener?.name, alterText(antworten['rd.alter']?.wert), geschlechtText(graph, antworten['rd.geschlecht']?.antwort)].filter(Boolean).join(', ')
    if (person) punkte.push({schluessel: 'leitfaden.betroffen', werte: {person}})
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
    const pfad = graph.endpunkte.find(endpunkt => endpunkt.knoten === knoten)?.pfad ?? []
    const labels = pfad
        .map(schritt => graph.knoten[schritt.knoten]?.antworten?.find(antwort => antwort.id === schritt.antwort)?.label)
        .filter((label): label is string => Boolean(label) && !/^ohne weitere Angabe$/i.test(label ?? ''))
    const [protokoll, ...rest] = labels
    if (!protokoll) return szenario.titel
    return rest.length ? `${protokoll}: ${rest.join(', ')}` : protokoll
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
