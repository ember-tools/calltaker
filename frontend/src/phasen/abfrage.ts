import type {Abfragegraph} from '../modell/abfragegraph'
import {endergebnis, type Ergebnis} from '../modell/abfrageweg'
import type {Ziel} from '../modell/szenario'
import type {Bewertung, Codestufe, Phase, Urteil} from './typen'

/** Categories that say nothing about the resources alerted. */
const OHNE_KATEGORIE = new Set(['', 'Aufwertung entfällt.'])

const URTEIL_JE_STUFE: Record<Codestufe, Urteil> = {exakt: 'richtig', protokoll: 'teilweise', kategorie: 'teilweise', falsch: 'falsch'}

/**
 * The protocol an endpoint belongs to, from the code index.
 *
 * @param graph the graph
 * @param knoten the endpoint's node
 * @returns the protocol's id, or an empty text
 */
function protokollVon(graph: Abfragegraph, knoten: string): string {
    return graph.endpunkte.find(endpunkt => endpunkt.knoten === knoten)?.protokoll ?? ''
}

/**
 * How close an entered code comes to the true one.
 *
 * The same protocol is read from the code index, not from the code's digits alone, since a fire
 * protocol and a medical one can share their first two digits. A wrong code of the same category
 * alerts the same resources, so it counts as close; when either code has no usable category, that
 * tier does not apply.
 *
 * @param graph the graph
 * @param soll the true target
 * @param ist the code reached
 * @returns the tier
 */
export function codestufe(graph: Abfragegraph, soll: Ziel, ist: Ergebnis): Codestufe {
    if (ist.knoten === soll.knoten || ist.code === soll.code) return 'exakt'
    const protokoll = protokollVon(graph, soll.knoten)
    if (protokoll && protokoll === protokollVon(graph, ist.knoten)) return 'protokoll'
    const wahr = graph.knoten[soll.knoten]?.kategorie ?? ''
    if (!OHNE_KATEGORIE.has(wahr) && !OHNE_KATEGORIE.has(ist.kategorie) && wahr === ist.kategorie) return 'kategorie'
    return 'falsch'
}

/** The questioning: through the graph until it reaches a code. */
export const abfrage: Phase = {
    id: 'abfrage',
    titel: 'phase.abfrage',
    aktiv: () => true,
    fehlend: (eintraege, {graph}) => (endergebnis(graph, eintraege.abfrage) ? [] : ['fehlt.code']),
    bewerten: (eintraege, szenario, graph): Bewertung[] => {
        const ziel = szenario.ziel
        const erreicht = endergebnis(graph, eintraege.abfrage)
        const anzeige = (code: string, knoten: string) => [code, graph.knoten[knoten]?.kategorie].filter(Boolean).join(' · ')
        const soll = anzeige(ziel.code, ziel.knoten)
        const zusaetze: Bewertung[] = []
        const {aufwertung, abbruch, pfad} = eintraege.abfrage
        const ohne = aufwertung ? endergebnis(graph, {pfad}) : undefined
        if (ohne) zusaetze.push({feld: 'bewertung.codeVorAufwertung', soll: '', ist: anzeige(ohne.code, ohne.knoten), urteil: 'hinweis'})
        if (abbruch) zusaetze.push({feld: 'bewertung.abbruch', soll: '', ist: abbruch.grund, urteil: 'hinweis'})
        if (!erreicht) return [{feld: 'bewertung.code', soll, ist: '', urteil: 'offen'}, ...zusaetze]
        const stufe = codestufe(graph, ziel, erreicht)
        return [{feld: 'bewertung.code', soll, ist: anzeige(erreicht.code, erreicht.knoten), urteil: URTEIL_JE_STUFE[stufe], stufe}, ...zusaetze]
    },
}
