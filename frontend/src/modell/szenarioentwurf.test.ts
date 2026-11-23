import {describe, expect, it} from 'vitest'
import {antwortenAusPfad, entwurfAus, fehltZumSpeichern, leererEntwurf, pfadAusAntworten, pfadZumEndpunkt, sucheEndpunkte, zielAusPfad} from './szenarioentwurf'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'

const graph = testgraph()

describe('szenarioentwurf', () => {
    it('macht aus einem Pfad Antworten und zurück', () => {
        const pfad = [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]
        const antworten = antwortenAusPfad(graph, pfad)
        expect(antworten['hand']).toEqual({antwort: 'eins', label: '1. Hand'})
        expect(antworten['rd.alter']).toEqual({wert: '81'})
        expect(pfadAusAntworten(graph, antworten)).toEqual(pfad)
    })

    it('hört dort auf, wo eine Antwort nicht mehr passt', () => {
        const antworten = antwortenAusPfad(graph, BIS_SITUATION)
        antworten['rd.wahl'] = {antwort: 'gibtesnicht'}
        expect(pfadAusAntworten(graph, antworten)).toEqual(BIS_SITUATION.slice(0, 3))
    })

    it('findet Endpunkte nach Code und Anlass', () => {
        expect(sucheEndpunkte(graph, '17d').map(e => e.code)).toEqual(['17D01'])
        expect(sucheEndpunkte(graph, 'brand 2').map(e => e.code)).toEqual(['67B01'])
        expect(sucheEndpunkte(graph, '')).toEqual([])
    })

    it('springt zu einem Endpunkt und behält die passende Eröffnung', () => {
        const endpunkt = {...graph.endpunkte[1]!, pfad: [{knoten: 'rd.wahl', antwort: 'sturz'}, {knoten: 'p.k0', antwort: 'schwer'}]}
        expect(pfadZumEndpunkt(graph, BIS_SITUATION, endpunkt)).toEqual([...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}])
    })

    it('ergänzt eine Eröffnung, wenn der bisherige Pfad woanders hinführt', () => {
        const endpunkt = {...graph.endpunkte[3]!, pfad: [{knoten: 'fw.grund', antwort: 'brand'}]}
        expect(pfadZumEndpunkt(graph, BIS_SITUATION, endpunkt)).toEqual([
            {knoten: 'fachrichtung', antwort: 'fw'},
            {knoten: 'hand', antwort: 'eins'},
            {knoten: 'fw.grund', antwort: 'brand'},
        ])
    })

    it('beginnt leer mit der Version des Graphen', () => {
        expect(leererEntwurf(2)).toMatchObject({abfrageVersion: 2, herkunft: 'vorbereitet', antworten: {}})
    })
})

describe('szenarioentwurf beim Speichern', () => {
    it('nimmt den Code erst, wenn der Pfad an einem Endpunkt endet', () => {
        expect(zielAusPfad(graph, BIS_SITUATION)).toBeUndefined()
        expect(zielAusPfad(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}])).toEqual({knoten: 'p.e2', code: '17D01'})
    })

    it('sagt, was zum Speichern fehlt', () => {
        const entwurf = leererEntwurf(1)
        expect(fehltZumSpeichern(entwurf)).toEqual(['editor.fehltTitel', 'editor.fehltName', 'editor.fehltNummer', 'editor.fehltCode'])
        entwurf.titel = 'Sturz'
        entwurf.anrufer = {name: 'A', rufnummerUnterdrueckt: true, rufnummer: '0301234', rueckrufnummer: ''}
        entwurf.ziel = {knoten: 'p.e2', code: '17D01'}
        expect(fehltZumSpeichern(entwurf)).toEqual(['editor.fehltNummer'])
        entwurf.anrufer.rueckrufnummer = '0176 1234567'
        expect(fehltZumSpeichern(entwurf)).toEqual([])
    })

    it('macht aus einem Szenario einen Entwurf mit allen Feldern', () => {
        const szenario = {...leererEntwurf(1), id: 'x', ziel: {knoten: 'p.e2', code: '17D01'}, anrufer: {name: 'A', rufnummerUnterdrueckt: false, rufnummer: '49301'}, betroffener: undefined}
        const entwurf = entwurfAus(szenario)
        expect(entwurf.anrufer.rueckrufnummer).toBe('')
        expect(entwurf.betroffener).toEqual({name: ''})
        entwurf.ort.adresse.strasse = 'anders'
        expect(szenario.ort.adresse.strasse).toBe('')
    })
})

describe('szenarioentwurf mit einer Abkürzung in ein Protokoll', () => {
    it('nimmt eine frühere Antwort nicht, wenn sie an der Wahl des Protokolls vorbeiführt', () => {
        const abkuerzung = testgraph()
        abkuerzung.knoten['hand'] = {...abkuerzung.knoten['hand']!, antworten: [...abkuerzung.knoten['hand']!.antworten!, {id: 'kurz', label: 'Abkürzung', ziel: 'p.k0', protokoll: 'rd.17'}]}
        const endpunkt = {...abkuerzung.endpunkte[1]!, pfad: [{knoten: 'rd.wahl', antwort: 'sturz'}, {knoten: 'p.k0', antwort: 'schwer'}]}
        const pfad = pfadZumEndpunkt(abkuerzung, [{knoten: 'fachrichtung', antwort: 'rd'}, {knoten: 'hand', antwort: 'kurz'}], endpunkt)
        expect(pfad.find(s => s.knoten === 'hand')).toEqual({knoten: 'hand', antwort: 'eins'})
        expect(pfad.at(-1)).toEqual({knoten: 'p.k0', antwort: 'schwer'})
    })
})
