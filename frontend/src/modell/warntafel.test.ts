import {describe, expect, it} from 'vitest'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'
import {mitWarntafel} from './warntafel'

describe('mitWarntafel', () => {
    const graph = {...testgraph(), warntafel: {protokolle: ['fw.brand'], antworten: [{knoten: 'p.k0', antwort: 'schwer'}]}}
    const feuer = [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]

    it('gilt für die Protokolle und Antworten der Regeln', () => {
        expect(mitWarntafel(graph, feuer)).toBe(true)
        expect(mitWarntafel(graph, BIS_SITUATION)).toBe(false)
        expect(mitWarntafel(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}])).toBe(true)
        expect(mitWarntafel(testgraph(), feuer)).toBe(false)
    })
})
