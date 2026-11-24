import {describe, expect, it} from 'vitest'
import {leereEintraege} from './eintraege'
import {reanimationFaellig, wartetAufKraefte} from './reanimation'
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

describe('wartetAufKraefte', () => {
    it('hält am Telefon, solange die Reanimation läuft und die Kräfte nicht da sind', () => {
        const eintraege = leereEintraege()
        expect(wartetAufKraefte(eintraege, undefined, 100)).toBe(false)
        eintraege.zeiten = {reanimation: 50}
        expect(wartetAufKraefte(eintraege, undefined, 100)).toBe(true)
        expect(wartetAufKraefte(eintraege, 150, 100)).toBe(true)
        expect(wartetAufKraefte(eintraege, 150, 150)).toBe(false)
    })
})
