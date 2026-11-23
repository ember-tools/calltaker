import type {Abfragegraph, Endpunkt} from './abfragegraph'
import {aktuellerKnoten, erreichbar} from './abfrageweg'
import type {Schritteintrag} from './eintraege'
import type {Szenario, Wahl, Ziel} from './szenario'

/** A scenario being written: like a stored one, but without an id or a target yet. */
export type Entwurf = Omit<Szenario, 'id' | 'ziel'> & {id?: string, ziel?: Szenario['ziel']}

/**
 * A scenario with nothing filled in yet, written against the given graph version.
 *
 * @param abfrageVersion the version of the question graph
 * @returns the empty draft
 */
export function leererEntwurf(abfrageVersion: number): Entwurf {
    return {
        version: 1,
        abfrageVersion,
        titel: '',
        herkunft: 'vorbereitet',
        ort: {adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: ''}, objekt: '', geschoss: '', klingel: '', anfahrt: '', gefahren: ''},
        anrufer: {name: '', rufnummer: '', rufnummerUnterdrueckt: false, rueckrufnummer: ''},
        betroffener: {name: ''},
        antworten: {},
        rolle: {sprache: '', notizen: ''},
        erweiterungen: {},
    }
}

/**
 * The path a scenario's answers lay out from the root, as far as the graph lets them.
 *
 * Answers are keyed by node; walking from the root takes at each node the answer the scenario
 * gives there. The walk stops at the first node the scenario has no usable answer for.
 *
 * @param graph the graph
 * @param antworten the scenario's answers by node
 * @returns the path
 */
export function pfadAusAntworten(graph: Abfragegraph, antworten: Record<string, Wahl>): Schritteintrag[] {
    const pfad: Schritteintrag[] = []
    for (let schritte = 0; schritte < 200; schritte++) {
        const {knoten: id} = aktuellerKnoten(graph, pfad)
        const knoten = graph.knoten[id]
        const wahl = antworten[id]
        if (!knoten || !wahl) break
        if (knoten.antworten && knoten.antworten.some(a => a.id === wahl.antwort)) pfad.push({knoten: id, antwort: wahl.antwort})
        else if (knoten.eingabe) pfad.push(wahl.wert ? {knoten: id, wert: wahl.wert} : {knoten: id})
        else break
    }
    return pfad
}

/**
 * A scenario's answers from a path. A choice keeps the label it was written with when the same
 * answer was already given, so a warning about a changed label stays until that step is chosen
 * anew; a new choice takes the label it has today.
 *
 * @param graph the graph
 * @param pfad the path
 * @param bisher the answers so far
 * @returns the answers by node
 */
export function antwortenAusPfad(graph: Abfragegraph, pfad: Schritteintrag[], bisher: Record<string, Wahl> = {}): Record<string, Wahl> {
    const antworten: Record<string, Wahl> = {}
    for (const schritt of pfad) {
        const antwort = graph.knoten[schritt.knoten]?.antworten?.find(a => a.id === schritt.antwort)
        const alt = bisher[schritt.knoten]
        const label = alt?.antwort === antwort?.id && alt?.label ? alt.label : antwort?.label
        antworten[schritt.knoten] = antwort ? {antwort: antwort.id, label} : schritt.wert ? {wert: schritt.wert} : {}
    }
    return antworten
}

/**
 * A path to an endpoint found by its code.
 *
 * The longest start of the path so far that reaches the endpoint's protocol choice is kept.
 * Otherwise an opening is laid from the root: the endpoint's Fachrichtung, the answers the path
 * so far gave to the same questions as long as they still lead to the protocol's choice, and
 * elsewhere the first answer that does, or an empty input.
 *
 * @param graph the graph
 * @param bisher the path so far
 * @param endpunkt the endpoint
 * @returns the path ending at the endpoint
 */
export function pfadZumEndpunkt(graph: Abfragegraph, bisher: Schritteintrag[], endpunkt: Endpunkt): Schritteintrag[] {
    const wahl = endpunkt.pfad[0]?.knoten
    if (!wahl) return bisher
    const rest = endpunkt.pfad.map(schritt => ({knoten: schritt.knoten, antwort: schritt.antwort}))
    for (let laenge = bisher.length; laenge >= 0; laenge--) {
        if (aktuellerKnoten(graph, bisher.slice(0, laenge)).knoten === wahl) return [...bisher.slice(0, laenge), ...rest]
    }
    return [...eroeffnung(graph, bisher, endpunkt.fachrichtung, wahl), ...rest]
}

/**
 * An opening from the root to a protocol choice.
 *
 * @param graph the graph
 * @param bisher the path so far, whose answers are reused where they fit
 * @param fachrichtung the Fachrichtung to take at the root
 * @param wahl the protocol choice to reach
 * @returns the opening, which stops early when the choice cannot be reached
 */
function eroeffnung(graph: Abfragegraph, bisher: Schritteintrag[], fachrichtung: string, wahl: string): Schritteintrag[] {
    const frueher = new Map(bisher.map(schritt => [schritt.knoten, schritt]))
    const anfang: Schritteintrag[] = []
    for (let id = aktuellerKnoten(graph, anfang).knoten; id !== wahl && anfang.length < 50; id = aktuellerKnoten(graph, anfang).knoten) {
        const knoten = graph.knoten[id]
        const passt = (s?: Schritteintrag) => s && (knoten?.eingabe || knoten?.antworten?.some(a => a.id === s.antwort && erreichbar(graph, a.ziel, wahl)))
        const alt = frueher.get(id)
        if (id === graph.meta.wurzel) anfang.push({knoten: id, antwort: fachrichtung})
        else if (passt(alt)) anfang.push(alt!)
        else if (knoten?.eingabe) anfang.push({knoten: id})
        else if (knoten?.antworten?.length) anfang.push({knoten: id, antwort: (knoten.antworten.find(a => erreichbar(graph, a.ziel, wahl)) ?? knoten.antworten[0]!).id})
        else break
    }
    return anfang
}

/**
 * The endpoints whose code or reason contains every word of a search.
 *
 * @param graph the graph
 * @param text the search
 * @param grenze how many to return at most
 * @returns the matching endpoints
 */
export function sucheEndpunkte(graph: Abfragegraph, text: string, grenze = 30): Endpunkt[] {
    const woerter = text.toLowerCase().split(/\s+/).filter(Boolean)
    if (woerter.length === 0) return []
    return graph.endpunkte
        .filter(e => woerter.every(w => `${e.code} ${e.anlass} ${e.kategorie}`.toLowerCase().includes(w)))
        .slice(0, grenze)
}

/**
 * The endpoint a path ends in, as a scenario's target.
 *
 * @param graph the graph
 * @param pfad the path
 * @returns the target, or undefined while the path has not reached a code
 */
export function zielAusPfad(graph: Abfragegraph, pfad: Schritteintrag[]): Ziel | undefined {
    const {knoten: id, passend} = aktuellerKnoten(graph, pfad)
    const code = graph.knoten[id]?.code
    return code && passend === pfad.length ? {knoten: id, code} : undefined
}

/**
 * A draft of a stored scenario, with every text field present so the form can bind to it.
 *
 * @param szenario the scenario
 * @returns its draft, a copy that can be changed freely
 */
export function entwurfAus(szenario: Szenario): Entwurf {
    const kopie = JSON.parse(JSON.stringify(szenario)) as Szenario
    return {
        ...kopie,
        anrufer: {...kopie.anrufer, rufnummer: kopie.anrufer.rufnummer ?? '', rueckrufnummer: kopie.anrufer.rueckrufnummer ?? ''},
        betroffener: {name: kopie.betroffener?.name ?? ''},
        rolle: {...kopie.rolle},
    }
}

/**
 * What a draft still lacks before it can be stored, as catalogue keys. The server checks it
 * again in full; this only keeps the save button honest.
 *
 * @param entwurf the draft
 * @returns the missing parts, empty when it can be stored
 */
export function fehltZumSpeichern(entwurf: Entwurf): string[] {
    const fehlt: string[] = []
    if (!entwurf.titel.trim()) fehlt.push('editor.fehltTitel')
    if (!entwurf.anrufer.name.trim()) fehlt.push('editor.fehltName')
    const nummer = entwurf.anrufer.rufnummerUnterdrueckt ? entwurf.anrufer.rueckrufnummer : entwurf.anrufer.rufnummer
    if (!nummer?.trim()) fehlt.push('editor.fehltNummer')
    if (!entwurf.ziel) fehlt.push('editor.fehltCode')
    return fehlt
}
