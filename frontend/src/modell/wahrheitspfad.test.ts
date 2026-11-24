import {describe, expect, it} from 'vitest'
import {antwortenAusPfad} from './szenarioentwurf'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'
import {vergleichePfad} from './wahrheitspfad'

const graph = testgraph()
const wahrheit = antwortenAusPfad(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}])

describe('vergleichePfad', () => {
    it('markiert Gleiches, die aktuelle Frage und Offenes', () => {
        const vergleich = vergleichePfad(graph, wahrheit, BIS_SITUATION.slice(0, 2))
        expect(vergleich.schritte.map(s => s.stand)).toEqual(['gleich', 'gleich', 'hier', 'offen', 'offen'])
        expect(vergleich.abzweigung).toBeUndefined()
    })

    it('zeigt abweichende Antworten und wo der Trainee abgezweigt ist', () => {
        const vergleich = vergleichePfad(graph, wahrheit, [...BIS_SITUATION.slice(0, 2), {knoten: 'rd.alter', wert: '50'}, ...BIS_SITUATION.slice(3), {knoten: 'p.k0', antwort: 'leicht'}])
        expect(vergleich.schritte[2]).toMatchObject({stand: 'anders', soll: '81', ist: '50'})
        expect(vergleich.schritte[4]).toMatchObject({stand: 'anders', soll: 'Schwer', ist: 'Leicht'})
        expect(vergleich.abzweigung).toEqual({knoten: 'rd.alter', frage: 'Alter?', ist: '50'})
    })

    it('zeigt eine Frage abseits des Pfads mit der Antwort des Szenarios, wenn es eine hat', () => {
        const vergleich = vergleichePfad(graph, {...wahrheit, 'fw.grund': {antwort: 'brand'}}, [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}])
        expect(vergleich.abzweigung).toMatchObject({knoten: 'fachrichtung', ist: 'Feuer'})
        expect(vergleich.abseits).toEqual({knoten: 'fw.grund', frage: 'Warum?', soll: 'Brand'})
    })
})

describe('vergleichePfad mit automatischen Schritten', () => {
    it('merkt, welche Schritte die Abfrage selbst genommen hat', () => {
        const vergleich = vergleichePfad(graph, wahrheit, [...BIS_SITUATION.slice(0, 3), {...BIS_SITUATION[3]!, automatisch: true}])
        expect(vergleich.schritte[3]).toMatchObject({stand: 'gleich', automatisch: true})
        expect(vergleich.schritte[2]!.automatisch).toBeUndefined()
    })

    it('wertet ein geschätztes Alter als gleich, wenn die Zahl stimmt', () => {
        const graph = {...testgraph(), meta: {...testgraph().meta, person: {alter_knoten: 'rd.alter', geschlecht_knoten: 'x', geschlecht: {}}}}
        const antworten = antwortenAusPfad(graph, [...BIS_SITUATION.map(s => (s.knoten === 'rd.alter' ? {knoten: 'rd.alter', wert: 'etwa 80'} : s))])
        const gleich = vergleichePfad(graph, antworten, BIS_SITUATION.map(s => (s.knoten === 'rd.alter' ? {knoten: 'rd.alter', wert: '80'} : s)))
        expect(gleich.schritte.find(s => s.knoten === 'rd.alter')?.stand).toBe('gleich')
        const anders = vergleichePfad(graph, antworten, BIS_SITUATION.map(s => (s.knoten === 'rd.alter' ? {knoten: 'rd.alter', wert: '60'} : s)))
        expect(anders.schritte.find(s => s.knoten === 'rd.alter')?.stand).toBe('anders')
        const ohneZahl = vergleichePfad(graph, antworten, BIS_SITUATION.map(s => (s.knoten === 'rd.alter' ? {knoten: 'rd.alter', wert: 'alt'} : s)))
        expect(ohneZahl.schritte.find(s => s.knoten === 'rd.alter')?.stand).toBe('anders')
    })
})
