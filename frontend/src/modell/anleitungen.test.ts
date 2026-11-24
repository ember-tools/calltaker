import {describe, expect, it} from 'vitest'
import type {Anleitung} from './abfragegraph'
import {faellige} from './anleitungen'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'

/**
 * The test graph with a small catalogue.
 *
 * @param anleitungen the catalogue
 * @returns the graph
 */
function mit(...anleitungen: Anleitung[]) {
    return {...testgraph(), anleitungen}
}

const anleitung = (id: string, wenn: Anleitung['wenn'], felder: Partial<Anleitung> = {}): Anleitung => ({id, titel: id, saetze: ['S'], wenn, quelle: 'Q', ...felder})

describe('faellige', () => {
    it('nimmt Hinweise nach Fachrichtung, Protokoll, Antwort und Kategorie', () => {
        const graph = mit(
            anleitung('fach', [{fachrichtung: 'rd'}]),
            anleitung('protokoll', [{protokolle: ['rd.17']}]),
            anleitung('antwort', [{antworten: [{knoten: 'p.k0', antwort: 'schwer'}]}]),
            anleitung('kategorie', [{kategorien: ['RD1NC REA']}]),
            anleitung('feuer', [{fachrichtung: 'brand'}]),
        )
        expect(faellige(graph, BIS_SITUATION.slice(0, 2)).map(a => a.id)).toEqual(['fach'])
        expect(faellige(graph, BIS_SITUATION).map(a => a.id)).toEqual(['fach', 'protokoll'])
        expect(faellige(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}], 'RD1NC REA.').map(a => a.id)).toEqual(['fach', 'protokoll', 'antwort', 'kategorie'])
    })

    it('verlangt alle Bedingungen eines Satzes und lässt Pflichthinweise vorgehen', () => {
        const graph = mit(
            anleitung('beides', [{fachrichtung: 'rd', antworten: [{knoten: 'p.k0', antwort: 'leicht'}]}]),
            anleitung('pflicht', [{fachrichtung: 'rd'}], {pflicht: true}),
        )
        expect(faellige(graph, BIS_SITUATION).map(a => a.id)).toEqual(['pflicht'])
        expect(faellige(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]).map(a => a.id)).toEqual(['pflicht', 'beides'])
    })

    it('lässt aus, was ein anderer fälliger Hinweis ausschließt', () => {
        const graph = mit(
            anleitung('bleiben', [{fachrichtung: 'rd'}], {schliesstAus: ['verlassen']}),
            anleitung('verlassen', [{fachrichtung: 'rd'}]),
        )
        expect(faellige(graph, BIS_SITUATION).map(a => a.id)).toEqual(['bleiben'])
    })
})

describe('faellige mit Ausschlüssen im Satz', () => {
    it('lässt einen Hinweis weg, wenn eine verbotene Antwort gegeben ist', () => {
        const graph = mit(anleitung('vorort', [{fachrichtung: 'rd', nicht: [{knoten: 'hand', antwort: 'eins'}]}]))
        expect(faellige(graph, BIS_SITUATION.slice(0, 1)).map(a => a.id)).toEqual(['vorort'])
        expect(faellige(graph, BIS_SITUATION.slice(0, 2))).toEqual([])
    })
})

describe('faellige ohne Anrufer vor Ort', () => {
    it('lässt Hinweise weg, die jemanden vor Ort brauchen', () => {
        const graph = mit(anleitung('vorort', [{fachrichtung: 'rd'}]), anleitung('immer', [{fachrichtung: 'rd'}], {auchOhneVorOrt: true}))
        graph.meta = {...graph.meta, abwesend: [{knoten: 'hand', antwort: 'eins'}]}
        expect(faellige(graph, BIS_SITUATION.slice(0, 1)).map(a => a.id)).toEqual(['vorort', 'immer'])
        expect(faellige(graph, BIS_SITUATION.slice(0, 2)).map(a => a.id)).toEqual(['immer'])
    })
})

describe('faellige mit ausgeschlossenen Kategorien', () => {
    it('lässt Hinweise weg, wenn das Ergebnis eine ausgeschlossene Kategorie hat', () => {
        const graph = mit(anleitung('nachher', [{fachrichtung: 'rd', nichtKategorien: ['RD1NC REA']}]))
        expect(faellige(graph, BIS_SITUATION).map(a => a.id)).toEqual(['nachher'])
        expect(faellige(graph, BIS_SITUATION, 'RD1NC REA.').map(a => a.id)).toEqual([])
        expect(faellige(graph, BIS_SITUATION, 'RD2NC.').map(a => a.id)).toEqual(['nachher'])
    })
})
