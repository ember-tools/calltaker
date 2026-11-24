import {describe, expect, it} from 'vitest'
import {angeboten, leitfragenAn, leitstand, naechste, offen, rest, type Knotenleitfragen, type Leitfrage} from './leitfragen'
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
