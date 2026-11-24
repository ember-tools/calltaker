import {describe, expect, it} from 'vitest'
import {angeboten, antwortAusLoesung, leitfragenAn, leithinweise, leitstand, naechste, offen, rest, wegZurLoesung, type Knotenleitfragen, type Leitfrage} from './leitfragen'
import {testgraph} from './testgraph.test-hilfe'

const jaNein = (id: string, kachel: string, mehr: Partial<Leitfrage> = {}): Leitfrage => ({
    id, frage: `${id}?`, antworten: [{label: 'Ja', behaelt: [kachel]}, {label: 'Nein', nimmt: [kachel]}, {label: 'Weiß nicht'}], ...mehr,
})
const sicher: Leitfrage = {id: 's', frage: 'Strom?', sicherheit: true, wenn: ['3'], antworten: [{label: 'Ja'}, {label: 'Nein'}]}
const KNOTEN: Knotenleitfragen = {knoten: 'x', fragen: [sicher, jaNein('a', '1'), jaNein('b', '2')]}
const ALLE = ['1', '2', '3']

describe('leitfragen', () => {
    it('lässt Antworten Kacheln behalten oder herausnehmen', () => {
        const alle = new Set(ALLE)
        expect([...rest({label: 'J', behaelt: ['1', '9']}, alle)]).toEqual(['1'])
        expect([...rest({label: 'N', nimmt: ['1']}, alle)]).toEqual(['2', '3'])
        expect([...rest({label: '?'}, alle)]).toEqual(ALLE)
    })

    it('bietet keine Antwort an, die nichts übrig ließe', () => {
        const frage: Leitfrage = {id: 'q', frage: '?', antworten: [{label: 'C', behaelt: ['C']}, {label: 'A', behaelt: ['A']}, {label: '?'}]}
        expect(angeboten(frage, new Set(['A', 'B'])).map(a => a.label)).toEqual(['A', '?'])
        expect(offen(frage, new Set(['A', 'B']))).toBe(true)
    })

    it('nimmt die erste Frage, die noch unterscheidet, Sicherheitsfragen auch ohne', () => {
        expect(naechste(KNOTEN, new Set(ALLE))?.frage.id).toBe('s')
        expect(naechste(KNOTEN, new Set(ALLE), 1)?.frage.id).toBe('a')
        expect(naechste(KNOTEN, new Set(['1', '2']))?.frage.id).toBe('a')
        expect(naechste(KNOTEN, new Set(['2']), 1)).toBeUndefined()
        expect(naechste({knoten: 'x', fragen: [jaNein('a', '9'), jaNein('b', '2')]}, new Set(['1', '2']))?.frage.id).toBe('b')
    })

    it('spielt die gegebenen Antworten nach und schlägt am Ende Kacheln vor', () => {
        const antwort = (frage: string, label: string) => ({knoten: 'x', frage, antwort: label})
        const anfang = leitstand(KNOTEN, ALLE, [])
        expect(anfang.frage?.id).toBe('s')
        expect(anfang.vorschlag).toEqual([])
        const unterwegs = leitstand(KNOTEN, ALLE, [antwort('s', 'Nein'), antwort('a', 'Nein')])
        expect(unterwegs.frage?.id).toBe('b')
        expect([...unterwegs.kacheln]).toEqual(['2', '3'])
        const fertig = leitstand(KNOTEN, ALLE, [antwort('s', 'Nein'), antwort('a', 'Nein'), antwort('b', 'Ja')])
        expect(fertig.frage).toBeUndefined()
        expect(fertig.vorschlag).toEqual(['2'])
    })

    it('bricht das Nachspielen bei einer Antwort ab, die nicht mehr passt', () => {
        const stand = leitstand(KNOTEN, ALLE, [{knoten: 'x', frage: 'a', antwort: 'Ja'}])
        expect(stand.beantwortet).toEqual([])
        expect(stand.frage?.id).toBe('s')
        const unbekannt = leitstand(KNOTEN, ALLE, [{knoten: 'x', frage: 's', antwort: 'Vielleicht'}])
        expect(unbekannt.beantwortet).toEqual([])
    })

    it('bricht ab, wenn eine Antwort nicht mehr angeboten wird, und zählt nur Antworten dieses Knotens', () => {
        const knoten: Knotenleitfragen = {knoten: 'x', fragen: [jaNein('a', '1'), {id: 'b', frage: '?', antworten: [{label: 'Eins', behaelt: ['1']}, {label: 'Zwei', behaelt: ['2']}, {label: '?'}]}]}
        const stand = leitstand(knoten, ALLE, [{knoten: 'x', frage: 'a', antwort: 'Nein'}, {knoten: 'x', frage: 'b', antwort: 'Eins'}])
        expect(stand.beantwortet).toHaveLength(1)
        expect([...stand.kacheln]).toEqual(['2', '3'])
        const fremd = leitstand(knoten, ALLE, [{knoten: 'y', frage: 'a', antwort: 'Ja'}])
        expect(fremd.beantwortet).toEqual([])
    })

    it('schlägt nichts vor, solange mehr als drei Kacheln übrig sind, und hält die Reihenfolge', () => {
        const vier = leitstand({knoten: 'x', fragen: [jaNein('a', '9')]}, ['1', '2', '3', '4'], [])
        expect(vier.frage).toBeUndefined()
        expect(vier.vorschlag).toEqual([])
        const drei = leitstand({knoten: 'x', fragen: [{id: 'a', frage: '?', antworten: [{label: 'J', behaelt: ['4', '1']}, {label: 'N'}]}]}, ['1', '2', '3', '4'], [{knoten: 'x', frage: 'a', antwort: 'J'}])
        expect(drei.vorschlag).toEqual(['1', '4'])
    })

    it('findet die Leitfragen eines Knotens im Graphen', () => {
        const graph = {...testgraph(), leitfragen: [KNOTEN, {knoten: 'leer', fragen: []}]}
        expect(leitfragenAn(graph, 'x')).toBe(KNOTEN)
        expect(leitfragenAn(graph, 'leer')).toBeUndefined()
        expect(leitfragenAn(testgraph(), 'x')).toBeUndefined()
    })
})

describe('antwortAusLoesung', () => {
    const frage: Leitfrage = {id: 'a', frage: 'Atmet?', antworten: [{label: 'Ja', nimmt: ['1']}, {label: 'Nein', behaelt: ['1']}, {label: 'Weiß nicht'}]}
    const alle = new Set(['1', '2', '3'])
    const wahl = (antwort: string) => ({x: {antwort}})
    const x: Knotenleitfragen = {knoten: 'x', fragen: [], nurDirekt: ['9']}
    const w: Knotenleitfragen = {knoten: 'w.k0', fragen: []}

    it('nennt die Antwort, die die korrekte Kachel behält, und lässt bei mehreren die Wahl', () => {
        expect(antwortAusLoesung(x, frage, alle, wahl('1'))).toEqual(['Nein'])
        expect(antwortAusLoesung(x, frage, alle, wahl('2'))).toEqual(['Ja'])
        const beide: Leitfrage = {id: 'b', frage: '?', antworten: [{label: 'Ja', behaelt: ['1', '2']}, {label: 'Nein', behaelt: ['2', '3']}, {label: 'Anders', behaelt: ['1']}]}
        expect(antwortAusLoesung(x, beide, alle, wahl('2'))).toEqual(['Ja', 'Nein'])
    })

    it('lässt frei antworten, wenn jede Antwort passt oder die Lösung nichts sagt', () => {
        const egal: Leitfrage = {id: 'c', frage: '?', antworten: [{label: 'Ja'}, {label: 'Nein'}]}
        expect(antwortAusLoesung(x, egal, alle, wahl('2'))).toEqual([])
        expect(antwortAusLoesung(x, frage, new Set(['2', '3']), wahl('1'))).toEqual([])
        expect(antwortAusLoesung(x, frage, alle, {})).toEqual([])
        expect(antwortAusLoesung(x, frage, new Set(['1', '9']), wahl('9'))).toEqual([])
    })

    it('liest eine Sicherheitsfrage aus den verknüpften Antworten des Graphen', () => {
        const strom: Leitfrage = {id: 's', frage: 'Strom?', sicherheit: true, antworten: [{label: 'Ja'}, {label: 'Nein'}], loesung: {knoten: ['w.s1', 'w.s2'], ja: ['ja'], nein: ['nein', 'nie']}}
        expect(antwortAusLoesung(w, strom, alle, {'w.s2': {antwort: 'ja'}})).toEqual(['Ja'])
        expect(antwortAusLoesung(w, strom, alle, {'w.s1': {antwort: 'nie'}})).toEqual(['Nein'])
        expect(antwortAusLoesung(w, strom, alle, {})).toEqual([])
    })
})

describe('leithinweise', () => {
    const graph = {
        ...testgraph(),
        leitfragen: [{knoten: 'p.k0', fragen: [
            {id: 'strom', frage: 'Strom?', sicherheit: true, hinweis: 'Abstand.', antworten: [{label: 'Ja'}, {label: 'Nein'}]},
            {id: 'atmet', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['schwer-2']}, {label: 'Nein', behaelt: ['schwer-2']}, {label: 'Weiß nicht'}]},
            {id: 'blut', frage: 'Blutet es stark?', antworten: [{label: 'Ja', behaelt: ['schwer']}, {label: 'Nein', behaelt: ['leicht']}, {label: 'Weiß nicht'}]},
        ]}],
    }
    const loesung = {'p.k0': {antwort: 'schwer'}}

    it('zeigt bei einer anderen Kachel den Weg über die Leitfragen zur korrekten', () => {
        expect(wegZurLoesung(graph.leitfragen[0]!, ['leicht', 'schwer', 'schwer-2'], 'schwer', loesung).weg).toEqual([
            {frage: 'Atmet die Person?', antwort: 'Ja'},
            {frage: 'Blutet es stark?', antwort: 'Ja'},
        ])
        const hinweise = leithinweise(graph, [{knoten: 'p.k0', antwort: 'leicht'}], [{knoten: 'p.k0', frage: 'strom', antwort: 'Nein'}], loesung)
        expect(hinweise).toEqual([{art: 'weg', knoten: 'p.k0', soll: 'Atmet die Person? Ja → Blutet es stark? Ja → Schwer', ist: 'Leicht'}])
    })

    it('nennt eine nicht gestellte Sicherheitsfrage, sonst nichts bei der korrekten Kachel', () => {
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'schwer'}], [], loesung)).toEqual([{art: 'sicherheit', knoten: 'p.k0', soll: '', ist: 'Strom?'}])
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'schwer', automatisch: true}], [], loesung)).toEqual([])
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'schwer'}], [{knoten: 'p.k0', frage: 'strom', antwort: 'Ja'}], loesung)).toEqual([])
        expect(leithinweise(graph, [{knoten: 'rd.wahl', antwort: 'sturz'}], [], loesung)).toEqual([])
    })
})

describe('wegZurLoesung bei offenen Fragen und Direktkacheln', () => {
    it('nimmt bei einer Frage, die die Lösung offen lässt, die engste Antwort, die die korrekte Kachel behält', () => {
        const eintrag: Knotenleitfragen = {knoten: 'k', fragen: [
            {id: 'grob', frage: 'Grob?', antworten: [{label: 'A', behaelt: ['1', '2']}, {label: 'B', behaelt: ['1', '2', '3']}, {label: 'C', behaelt: ['4']}]},
        ]}
        const {weg, kacheln} = wegZurLoesung(eintrag, ['1', '2', '3', '4'], '1', {k: {antwort: '1'}})
        expect(weg).toEqual([{frage: 'Grob?', antwort: 'A'}])
        expect([...kacheln]).toEqual(['1', '2'])
    })

    it('gibt keinen Weg für eine Direktkachel oder an einem Knoten nur mit Sicherheitsfragen', () => {
        const graph = {...testgraph(), leitfragen: [{knoten: 'p.k0', nurDirekt: ['schwer-2'], fragen: [
            {id: 'strom', frage: 'Strom?', sicherheit: true, antworten: [{label: 'Ja'}, {label: 'Nein'}], loesung: {knoten: ['p.k0'], ja: ['schwer']}},
        ]}]}
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'leicht'}], [{knoten: 'p.k0', frage: 'strom', antwort: 'Ja'}], {'p.k0': {antwort: 'schwer'}})).toEqual([])
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'leicht'}], [{knoten: 'p.k0', frage: 'strom', antwort: 'Ja'}], {'p.k0': {antwort: 'schwer-2'}})).toEqual([])
    })
})

describe('leithinweise mit Bedingungen', () => {
    it('übergeht Sicherheitsfragen, deren Kacheln am Knoten nicht vorkommen', () => {
        const graph = {...testgraph(), leitfragen: [{knoten: 'p.k0', fragen: [
            {id: 'strom', frage: 'Strom?', sicherheit: true, wenn: ['gibt-es-hier-nicht'], antworten: [{label: 'Ja'}, {label: 'Nein'}]},
        ]}]}
        expect(leithinweise(graph, [{knoten: 'p.k0', antwort: 'schwer'}], [], {})).toEqual([])
    })
})
