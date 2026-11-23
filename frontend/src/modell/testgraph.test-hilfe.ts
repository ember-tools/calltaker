import type {Abfragegraph, Endpunkt} from './abfragegraph'

/**
 * A small question graph for tests: two Fachrichtungen, a shared opening with a switch, a typed
 * age, one medical protocol whose two answers share a label, and one fire protocol.
 *
 * @returns the graph
 */
export function testgraph(): Abfragegraph {
    const sturz = (antwort: string) => [{knoten: 'rd.wahl', antwort: 'sturz'}, {knoten: 'p.k0', antwort}]
    const pfade: Record<string, Endpunkt['pfad']> = {'p.e1': sturz('leicht'), 'p.e2': sturz('schwer'), 'p.e3': sturz('schwer-2'), 'fw.e': [{knoten: 'fw.grund', antwort: 'brand'}]}
    const endpunkt = (knoten: string, code: string, kategorie: string, protokoll: string, fachrichtung: string): Endpunkt =>
        ({knoten, code, kategorie, anlass: code, stichwort: kategorie, fachrichtung, protokoll, pfad: pfade[knoten] ?? []})
    return {
        meta: {version: 1, wurzel: 'fachrichtung', quelle: '', hinweise: {}, notfallkategorien: {}},
        knoten: {
            'fachrichtung': {frage: 'Grund?', antworten: [{id: 'rd', label: 'Med', ziel: 'hand', farbe: 'rd'}, {id: 'fw', label: 'Feuer', ziel: 'hand', farbe: 'fw'}]},
            'hand': {frage: 'Hand?', antworten: [{id: 'eins', label: '1. Hand', ziel: 'weiche'}]},
            'weiche': {weiche: {knoten: 'fachrichtung', ziele: {rd: 'rd.alter', fw: 'fw.grund'}}},
            'rd.alter': {frage: 'Alter?', eingabe: {vorlage: '{wert}', platzhalter: 'Jahre', leer: {label: 'unbekannt', aussage: ''}}, ziel: 'rd.wahl'},
            'rd.wahl': {frage: 'Beschwerde?', antworten: [{id: 'sturz', label: 'Sturz', ziel: 'p.k0', protokoll: 'rd.17', nr: '17'}]},
            'p.k0': {frage: 'Situation?', hinweis: 'Nicht bewegen lassen.', antworten: [
                {id: 'leicht', label: 'Leicht', ziel: 'p.e1'},
                {id: 'schwer', label: 'Schwer', ziel: 'p.e2'},
                {id: 'schwer-2', label: 'Schwer', ziel: 'p.e3'},
            ]},
            'p.e1': {code: '17A01', kategorie: 'RD4C.', stichwort: 'RD4C.'},
            'p.e2': {code: '17D01', kategorie: 'RD2NC.', stichwort: 'RD2NC.'},
            'p.e3': {code: '17E01', kategorie: 'RD1NC REA.', stichwort: 'RD1NC REA.'},
            'fw.grund': {frage: 'Warum?', antworten: [{id: 'brand', label: 'Brand', ziel: 'fw.e', protokoll: 'fw.brand'}]},
            'fw.e': {code: '67B01', kategorie: 'BRAND 2', stichwort: 'BRAND 2'},
        },
        endpunkte: [
            endpunkt('p.e1', '17A01', 'RD4C.', 'rd.17', 'rd'),
            endpunkt('p.e2', '17D01', 'RD2NC.', 'rd.17', 'rd'),
            endpunkt('p.e3', '17E01', 'RD1NC REA.', 'rd.17', 'rd'),
            endpunkt('fw.e', '67B01', 'BRAND 2', 'fw.brand', 'fw'),
        ],
    }
}

/** The path to the medical protocol's situation question. */
export const BIS_SITUATION = [
    {knoten: 'fachrichtung', antwort: 'rd'},
    {knoten: 'hand', antwort: 'eins'},
    {knoten: 'rd.alter', wert: '81'},
    {knoten: 'rd.wahl', antwort: 'sturz'},
]
