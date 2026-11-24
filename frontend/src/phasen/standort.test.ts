import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import {leererEntwurf} from '../modell/szenarioentwurf'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import {standort, wohnungOhneGeschoss} from './standort'

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

describe('standort in Wohnungen', () => {
    it('erinnert an Geschoss und Klingel, solange beides fehlt', () => {
        const graph = testgraph()
        const eintraege = leereEintraege()
        eintraege.ort.koordinaten = [52.5, 13.4]
        eintraege.ort.adresse = {strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde'}
        eintraege.abfrage = {pfad: BIS_SITUATION}
        const kontext = {graph, anruf: {id: 'a', zustand: 'gespraech' as const, klingeltSeit: 0, rufnummerUnterdrueckt: false}}
        expect(wohnungOhneGeschoss(graph, eintraege)).toBe(true)
        expect(standort.fehlend(eintraege, kontext)).toEqual(['fehlt.geschossKlingel'])
        eintraege.ort.klingel = 'Kaya'
        expect(standort.fehlend(eintraege, kontext)).toEqual([])
        eintraege.ort.klingel = ''
        eintraege.ort.geschoss = '2. OG'
        expect(wohnungOhneGeschoss(graph, eintraege)).toBe(false)
        eintraege.ort.geschoss = ''
        eintraege.ort.objekt = 'Rathaus'
        expect(wohnungOhneGeschoss(graph, eintraege)).toBe(false)
        eintraege.ort.objekt = ''
        eintraege.abfrage = {pfad: [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]}
        expect(wohnungOhneGeschoss(graph, eintraege)).toBe(false)
        expect(wohnungOhneGeschoss({...graph, wohnungsprotokolle: ['fw.brand']}, eintraege)).toBe(true)
    })

    it('vergleicht die Klingel und zeigt, ob das Haustier bei den Gefahren steht', () => {
        const szenario = {...leererEntwurf(1), ort: {...leererEntwurf(1).ort, klingel: 'Kaya', haustier: 'ein großer Hund'}} as Szenario
        const eintraege = leereEintraege()
        const urteil = (feld: string) => standort.bewerten(eintraege, szenario, testgraph()).find(b => b.feld === feld)?.urteil
        expect([urteil('bewertung.klingel'), urteil('bewertung.haustier')]).toEqual(['offen', 'hinweis'])
        eintraege.ort.klingel = 'M. Kaya'
        eintraege.ort.gefahren = 'Hund in der Wohnung'
        expect([urteil('bewertung.klingel'), urteil('bewertung.haustier')]).toEqual(['richtig', 'richtig'])
        const papagei = {...szenario, ort: {...szenario.ort, haustier: 'ein Papagei'}} as Szenario
        eintraege.ort.gefahren = 'Papagei'
        expect(standort.bewerten(eintraege, papagei, testgraph()).find(b => b.feld === 'bewertung.haustier')?.urteil).toBe('richtig')
    })
})
