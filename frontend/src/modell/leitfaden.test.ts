import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from './ausbilder.test-hilfe'
import {leitfaden} from './leitfaden'

describe('leitfaden', () => {
    it('baut Stichpunkte aus dem Szenario, in Sprechreihenfolge', () => {
        const szenario = anrufMit('l').szenario
        szenario.antworten = {...szenario.antworten, 'eroeffnung.hand': {antwort: '3-hand-der-anrufer-meldet-fuer-andere'}, 'eroeffnung.vor-ort': {antwort: 'nein-war-nicht-vor-ort'}}
        szenario.betroffener = {name: 'Aylin Kaya'}
        const punkte = leitfaden(GRAPH, szenario)
        expect(punkte.map(p => p.schluessel)).toEqual(['leitfaden.einstieg', 'leitfaden.ort', 'leitfaden.hand.fuerAndere', 'leitfaden.vorOrt.nie', 'leitfaden.betroffen', 'leitfaden.rueckruf', 'leitfaden.stimmung.panisch'])
        expect(punkte[0]!.werte).toEqual({name: 'Mehmet Kaya', anlass: 'Sturz l'})
        expect(punkte[1]!.werte?.ort).toBe('Werderstraße 20, 13587 Hakenfelde')
        expect(punkte[4]!.werte?.person).toBe('Aylin Kaya, 81 Jahre')
    })

    it('nennt die Warntafel, oder dass keine lesbar ist', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'p.tafel': {frage: 'Tafel?', eingabe: {art: 'warntafel' as const, vorlage: '{wert}', platzhalter: ''}, ziel: 'p.k0'}}}
        const szenario = anrufMit('t').szenario
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {wert: '33/1203'}}}).find(p => p.schluessel === 'leitfaden.tafel')?.werte).toEqual({oben: '33', unten: '1203'})
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {}}}).some(p => p.schluessel === 'leitfaden.keineTafel')).toBe(true)
    })
})
