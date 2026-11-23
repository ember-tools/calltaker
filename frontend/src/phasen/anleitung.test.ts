import {describe, expect, it} from 'vitest'
import type {Anleitung} from '../modell/abfragegraph'
import {leereEintraege} from '../modell/eintraege'
import {antwortenAusPfad, leererEntwurf} from '../modell/szenarioentwurf'
import type {Szenario} from '../modell/szenario'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import {anleitung} from './anleitung'

const katalog: Anleitung[] = [
    {id: 'zugang', titel: 'Tür öffnen', saetze: ['Öffnen Sie die Tür.'], pflicht: true, wenn: [{fachrichtung: 'rd'}], quelle: 'Q'},
    {id: 'bleiben', titel: 'Bleiben', saetze: ['Bleiben Sie.'], pflicht: true, wenn: [{antworten: [{knoten: 'p.k0', antwort: 'schwer'}]}], schliesstAus: ['gehen'], quelle: 'Q'},
    {id: 'gehen', titel: 'Gehen', saetze: ['Gehen Sie.'], pflicht: true, wenn: [{antworten: [{knoten: 'p.k0', antwort: 'leicht'}]}], quelle: 'Q'},
    {id: 'nett', titel: 'Freundlich', saetze: ['Bleiben Sie ruhig.'], wenn: [{fachrichtung: 'rd'}], quelle: 'Q'},
]
const graph = {...testgraph(), anleitungen: katalog}
const kontext = {graph, anruf: {id: 'a', zustand: 'gespraech' as const, klingeltSeit: 0, rufnummerUnterdrueckt: false}}

describe('anleitung', () => {
    it('ist erst aktiv, wenn ein Hinweis fällig ist, und nennt fehlende Pflichthinweise', () => {
        const eintraege = leereEintraege()
        expect(anleitung.aktiv(eintraege, kontext)).toBe(false)
        eintraege.abfrage.pfad = BIS_SITUATION
        expect(anleitung.fehlend(eintraege, kontext)).toEqual(['fehlt.anleitung'])
        eintraege.anleitung.gegeben = ['zugang']
        expect(anleitung.fehlend(eintraege, kontext)).toEqual([])
    })

    it('vergleicht mit den Pflichthinweisen der Wahrheit und wertet ausgeschlossene als falsch', () => {
        const szenario: Szenario = {...leererEntwurf(1), id: 's', titel: 'S', ziel: {knoten: 'p.e2', code: '17D01'}, anrufer: {name: 'A', rufnummerUnterdrueckt: false, rufnummer: '49301'},
            antworten: antwortenAusPfad(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}])}
        const eintraege = leereEintraege()
        eintraege.anleitung.gegeben = ['zugang', 'gehen']
        const urteile = anleitung.bewerten(eintraege, szenario, graph).map(b => [b.beschriftung, b.urteil])
        expect(urteile).toEqual([['Tür öffnen', 'richtig'], ['Bleiben', 'offen'], ['Gehen', 'falsch']])
    })
})
