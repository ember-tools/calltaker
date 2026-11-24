import {describe, expect, it} from 'vitest'
import {lagen} from './lagen'
import {testgraph} from './testgraph.test-hilfe'

describe('lagen', () => {
    it('nennt die Protokolle je Fachrichtung so, wie die Abfrage sie anbietet, mit ihrer Zahl an Codes', () => {
        const graph = testgraph()
        graph.endpunkte = graph.endpunkte.map(e => ({...e, fachrichtung: e.protokoll === 'rd.17' ? 'rd' : 'fw'}))
        const gruppen = lagen(graph)
        expect(gruppen.map(g => g.name)).toEqual(['Med', 'Feuer'])
        expect(gruppen[0]!.lagen).toEqual([{protokoll: 'rd.17', name: 'Sturz', anzahl: 3}])
        expect(gruppen[1]!.lagen).toEqual([{protokoll: 'fw.brand', name: 'Brand', anzahl: 1}])
    })
})
