import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from './ausbilder.test-hilfe'
import {lageText, leitfaden} from './leitfaden'

describe('leitfaden', () => {
    it('baut Stichpunkte aus dem Szenario, in Sprechreihenfolge', () => {
        const szenario = anrufMit('l').szenario
        szenario.antworten = {...szenario.antworten, 'eroeffnung.hand': {antwort: '3-hand-der-anrufer-meldet-fuer-andere'}, 'eroeffnung.vor-ort': {antwort: 'nein-war-nicht-vor-ort'}}
        szenario.betroffener = {name: 'Aylin Kaya'}
        szenario.ort.haustier = 'ein Hund'
        const punkte = leitfaden(GRAPH, szenario)
        expect(punkte.map(p => p.schluessel)).toEqual(['leitfaden.ort', 'leitfaden.lage', 'leitfaden.name', 'leitfaden.hand.fuerAndere', 'leitfaden.vorOrt.nie', 'leitfaden.wohnung', 'leitfaden.haustier', 'leitfaden.betroffen', 'leitfaden.rueckruf', 'leitfaden.stimmung.panisch'])
        expect(punkte[0]!.werte?.ort).toBe('Werderstraße 20, 13587 Hakenfelde')
        expect(punkte[1]!.werte).toEqual({anlass: 'Sturz: Schwer'})
        expect(punkte[2]!.werte).toEqual({name: 'Mehmet Kaya'})
        expect(punkte[5]!.werte).toEqual({geschoss: '2. OG', klingel: 'Kaya'})
        expect(punkte[7]!.werte?.person).toBe('Aylin Kaya, 81 Jahre')
    })

    it('nennt die Warntafel, oder dass keine lesbar ist', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'p.tafel': {frage: 'Tafel?', eingabe: {art: 'warntafel' as const, vorlage: '{wert}', platzhalter: ''}, ziel: 'p.k0'}}}
        const szenario = anrufMit('t').szenario
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {wert: '33/1203'}}}).find(p => p.schluessel === 'leitfaden.tafel')?.werte).toEqual({oben: '33', unten: '1203'})
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {}}}).some(p => p.schluessel === 'leitfaden.keineTafel')).toBe(true)
    })

    it('lässt einen Anrufer ohne Adresse die Umgebung beschreiben statt den Ort zu nennen', () => {
        const szenario = anrufMit('d').szenario
        szenario.ort = {...szenario.ort, adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: 'Neukölln'}, objekt: 'Volkspark Hasenheide (Park)', geschoss: '', klingel: '',
            ohneAdresse: {wo: 'ein Park', umgebung: [{name: 'U Hermannplatz', art: 'Bahnhof', richtung: 'Nordosten', meter: 250}]}}
        const punkte = leitfaden(GRAPH, szenario)
        expect(punkte.map(p => p.schluessel)).toContain('leitfaden.ohneAdresse')
        expect(punkte.map(p => p.schluessel)).not.toContain('leitfaden.ort')
        expect(punkte.find(p => p.schluessel === 'leitfaden.umgebung')?.werte).toEqual({name: 'U Hermannplatz', art: 'Bahnhof', richtung: 'Nordosten', meter: '250'})
    })

    it('beschreibt die Lage auch bei Codes ohne lesbaren Anlass mit Worten statt mit dem Code', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'p.e2': {...GRAPH.knoten['p.e2']!, anlass: '17D01'}}}
        const szenario = {...anrufMit('c').szenario, ziel: {knoten: 'p.e2', code: '17D01'}}
        expect(lageText(graph, szenario)).toBe('Sturz: Schwer')
        const mitAnlass = {...GRAPH, knoten: {...GRAPH.knoten, 'p.e2': {...GRAPH.knoten['p.e2']!, anlass: 'Sturz mit Kopfverletzung'}}}
        expect(lageText(mitAnlass, szenario)).toBe('Sturz mit Kopfverletzung')
    })

    it('nennt das Geschlecht als Adjektiv', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'rd.geschlecht': {frage: 'Geschlecht?', antworten: [{id: 'mann', label: 'Mann', ziel: 'x', geschlecht: 'm' as const}, {id: 'frau', label: 'Frau', ziel: 'x', geschlecht: 'w' as const}]}}}
        const szenario = {...anrufMit('g').szenario, betroffener: {name: 'Murat Yıldız'}}
        szenario.antworten = {...szenario.antworten, 'rd.alter': {wert: '88'}, 'rd.geschlecht': {antwort: 'mann', label: 'Mann'}}
        expect(leitfaden(graph, szenario).find(p => p.schluessel === 'leitfaden.betroffen')?.werte?.person).toBe('Murat Yıldız, 88 Jahre, männlich')
    })
})
