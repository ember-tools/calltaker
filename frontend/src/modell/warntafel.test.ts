import {describe, expect, it} from 'vitest'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'
import {tafelAusWert, tafelDerWahrheit, tafelImPfad, wertAusTafel} from './warntafel'

function mitTafelfrage() {
    const graph = testgraph()
    graph.knoten['p.tafel'] = {frage: 'Tafel?', eingabe: {art: 'warntafel', vorlage: '{wert}', platzhalter: 'oben/unten'}, ziel: 'p.k0'}
    return graph
}

describe('warntafel', () => {
    it('liest und schreibt die Antwort der Tafelfrage', () => {
        expect(tafelAusWert('33/1203')).toEqual({gefahrenzahl: '33', un: '1203'})
        expect(tafelAusWert('x423/1428')).toEqual({gefahrenzahl: 'X423', un: '1428'})
        expect(tafelAusWert('/0004')).toEqual({gefahrenzahl: '', un: '0004'})
        expect(tafelAusWert('')).toBeUndefined()
        expect(tafelAusWert('Benzin')).toBeUndefined()
        expect(wertAusTafel({gefahrenzahl: 'x423', un: '1428'})).toBe('X423/1428')
    })

    it('findet die Tafel im Pfad und in der Wahrheit', () => {
        const graph = mitTafelfrage()
        expect(tafelImPfad(graph, [...BIS_SITUATION, {knoten: 'p.tafel', wert: '33/1203'}])).toEqual({gefahrenzahl: '33', un: '1203'})
        expect(tafelImPfad(graph, BIS_SITUATION)).toBeUndefined()
        expect(tafelDerWahrheit(graph, {'p.tafel': {wert: '30/1202'}})).toEqual({gefahrenzahl: '30', un: '1202'})
        expect(tafelDerWahrheit(graph, {'p.tafel': {}})).toBeUndefined()
    })
})
