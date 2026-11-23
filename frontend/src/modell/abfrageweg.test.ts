import {describe, expect, it} from 'vitest'
import {aktuellerKnoten, endergebnis, hoehereEndpunkte, schwere, schwersteErreichbare, unterscheidungen, zwischenergebnis} from './abfrageweg'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'

const graph = testgraph()
const schwerste = schwersteErreichbare(graph)

describe('abfrageweg', () => {
    it('folgt dem Pfad und der Weiche', () => {
        expect(aktuellerKnoten(graph, []).knoten).toBe('fachrichtung')
        expect(aktuellerKnoten(graph, BIS_SITUATION.slice(0, 2)).knoten).toBe('rd.alter')
        expect(aktuellerKnoten(graph, [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}]).knoten).toBe('fw.grund')
        expect(aktuellerKnoten(graph, BIS_SITUATION)).toEqual({knoten: 'p.k0', passend: 4})
    })

    it('hält an, wo der Pfad nicht mehr passt', () => {
        expect(aktuellerKnoten(graph, [{knoten: 'fachrichtung', antwort: 'rd'}, {knoten: 'falsch', antwort: 'x'}])).toEqual({knoten: 'hand', passend: 1})
    })

    it('ordnet Kategorien nach Dringlichkeit', () => {
        const reihe = ['RD1NC REA.', 'RD1NC FR.', 'RD2NC.', 'RD2C FR.', 'RD3C.', 'RD4B.', 'RD5.']
        expect([...reihe].sort((a, b) => schwere(b) - schwere(a))).toEqual(reihe)
        expect(schwere('BRAND 4')).toBeGreaterThan(schwere('BRAND 2'))
        expect(schwere('Aufwertung entfällt.')).toBe(-1)
    })

    it('zeigt erst mit einem Protokoll ein Zwischenergebnis, und dann das dringendste', () => {
        expect(zwischenergebnis(graph, {pfad: BIS_SITUATION.slice(0, 3)}, schwerste)).toBeUndefined()
        expect(zwischenergebnis(graph, {pfad: BIS_SITUATION}, schwerste)?.code).toBe('17E01')
    })

    it('kommt am Endpunkt, durch Aufwertung oder durch Abbruch zu einem Ergebnis', () => {
        expect(endergebnis(graph, {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]})?.code).toBe('17A01')
        expect(endergebnis(graph, {pfad: BIS_SITUATION, aufwertung: {knoten: 'p.e2', code: '17D01'}})?.kategorie).toBe('RD2NC.')
        expect(endergebnis(graph, {pfad: BIS_SITUATION, abbruch: {grund: 'aufgelegt', ergebnis: {knoten: 'p.e3', code: '17E01'}}})?.code).toBe('17E01')
        expect(endergebnis(graph, {pfad: BIS_SITUATION})).toBeUndefined()
    })

    it('bietet zur Aufwertung nur dringendere Codes des Protokolls', () => {
        expect(hoehereEndpunkte(graph, 'rd.17', 'RD4C.').map(e => e.code)).toEqual(['17E01', '17D01'])
        expect(hoehereEndpunkte(graph, 'rd.17', 'RD1NC REA.')).toEqual([])
    })

    it('unterscheidet Antworten mit gleichem Label', () => {
        const zusatz = unterscheidungen(graph.knoten['p.k0']!, schwerste, graph)
        expect(zusatz.get('schwer')).toBe('17D01 · RD2NC.')
        expect(zusatz.get('schwer-2')).toBe('17E01 · RD1NC REA.')
        expect(zusatz.has('leicht')).toBe(false)
    })
})
