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
 * What the trainer, playing the caller, needs at hand: an opening line, where it happened, what
 * the caller knows and does not, who is affected, the plate, a call-back number and how to sound.
 * Built from the scenario alone, in the caller's own voice.
 *
 * @param graph the graph
 * @param szenario the scenario
 * @returns the bullets in speaking order
 */
export function leitfaden(graph: Abfragegraph, szenario: Szenario): Stichpunkt[] {
    const antworten = szenario.antworten
    const punkte: Stichpunkt[] = []
    const anlass = graph.knoten[szenario.ziel.knoten]?.anlass ?? szenario.titel
    punkte.push({schluessel: 'leitfaden.einstieg', werte: {name: szenario.anrufer.name, anlass}})
    const ort = [zeile(szenario.ort.adresse), szenario.ort.objekt].filter(Boolean).join(', ')
    if (ort) punkte.push({schluessel: 'leitfaden.ort', werte: {ort}})
    const hand = HAND[antworten['eroeffnung.hand']?.antwort ?? '']
    if (hand) punkte.push({schluessel: hand})
    const vorOrt = VOR_ORT[antworten['eroeffnung.vor-ort']?.antwort ?? '']
    if (vorOrt) punkte.push({schluessel: vorOrt})
    const {geschoss, klingel, haustier} = szenario.ort
    if (geschoss || klingel) punkte.push({schluessel: 'leitfaden.wohnung', werte: {geschoss: geschoss || '-', klingel: klingel || '-'}})
    if (haustier) punkte.push({schluessel: 'leitfaden.haustier', werte: {haustier}})
    const person = [szenario.betroffener?.name, alterText(antworten['rd.alter']?.wert), antworten['rd.geschlecht']?.label].filter(Boolean).join(', ')
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
 * An age as the caller says it.
 *
 * @param wert the typed age, if known
 * @returns "54 Jahre", or nothing
 */
function alterText(wert?: string): string {
    const alter = (wert ?? '').trim()
    return alter ? (/^\d+$/.test(alter) ? `${alter} Jahre` : alter) : ''
}
