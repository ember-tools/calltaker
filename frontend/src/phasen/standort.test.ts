import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import {leererEntwurf} from '../modell/szenarioentwurf'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import {standort} from './standort'

describe('standort mit Warntafel', () => {
    it('vergleicht die UN-Nummer aus der Tafelfrage, wenn die Wahrheit eine Tafel hat', () => {
        const graph = testgraph()
        graph.knoten['p.tafel'] = {frage: 'Tafel?', eingabe: {art: 'warntafel', vorlage: '{wert}', platzhalter: 'oben/unten'}, ziel: 'p.k0'}
        const szenario = {...leererEntwurf(1), antworten: {'p.tafel': {wert: '33/1203'}}} as Szenario
        const eintraege = leereEintraege()
        const zeile = () => standort.bewerten(eintraege, szenario, graph).find(b => b.feld === 'bewertung.gefahrgut')
        expect(zeile()?.urteil).toBe('offen')
        eintraege.abfrage = {pfad: [...BIS_SITUATION, {knoten: 'p.tafel', wert: '33/1203'}]}
        expect(zeile()?.urteil).toBe('richtig')
        eintraege.abfrage = {pfad: [...BIS_SITUATION, {knoten: 'p.tafel', wert: '30/1202'}]}
        expect(zeile()?.urteil).toBe('falsch')
        expect(standort.bewerten(eintraege, leererEntwurf(1) as Szenario, graph).find(b => b.feld === 'bewertung.gefahrgut')).toBeUndefined()
    })
})
