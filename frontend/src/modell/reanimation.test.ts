import {describe, expect, it} from 'vitest'
import {reanimationFaellig} from './reanimation'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'

describe('reanimationFaellig', () => {
    const graph = testgraph()

    it('greift bei einem Stillstandscode', () => {
        expect(reanimationFaellig(graph, {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer-2'}]})).toBe(true)
        expect(reanimationFaellig(graph, {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}]})).toBe(false)
        expect(reanimationFaellig(graph, {pfad: BIS_SITUATION})).toBe(false)
    })

    it('greift, sobald keine Todeszeichen da sind, noch vor dem Code', () => {
        expect(reanimationFaellig(graph, {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]})).toBe(true)
        expect(reanimationFaellig(graph, {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'verwesung'}]})).toBe(false)
    })
})
