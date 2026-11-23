import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import type {Eintraege} from '../modell/eintraege'
import {antwortenAusPfad} from '../modell/szenarioentwurf'
import {BIS_SITUATION} from '../modell/testgraph.test-hilfe'
import {sichtVon, type Anruf} from '../modell/uebung'
import {reanimationBewerten, STANDARDZIELE, uebergabeBewerten} from './zeitbewertung'

const FEUER = [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]

function mitWahrheit(anruf: Anruf, pfad: Eintraege['abfrage']['pfad'], knoten: string, code: string): Anruf {
    anruf.szenario = {...anruf.szenario, antworten: antwortenAusPfad(GRAPH, pfad), ziel: {knoten, code}}
    return anruf
}

const urteile = (bewertungen: {feld: string, urteil: string, ist: string}[]) => bewertungen.map(b => [b.feld, b.urteil, b.ist])

describe('reanimationBewerten', () => {
    const stillstand = () => mitWahrheit(anrufMit('r', 'beendet'), [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer-2'}], 'p.e3', '17E01')

    it('misst den Start gegen die Zielzeit, wenn die Wahrheit ihn verlangt', () => {
        const anruf = stillstand()
        expect(urteile(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.reanimation', 'falsch', '']])
        anruf.eintraege.zeiten = {reanimation: 1030 + 90}
        expect(urteile(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.reanimation', 'richtig', '1:30']])
        expect(urteile(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, {...STANDARDZIELE, reanimation: 60}))).toEqual([['bewertung.reanimation', 'teilweise', '1:30']])
    })

    it('lässt den Start offen, solange das Gespräch läuft', () => {
        const anruf = stillstand()
        anruf.zustand = 'gespraech'
        expect(urteile(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.reanimation', 'offen', '']])
    })

    it('nennt einen Start ohne Stillstand als Hinweis', () => {
        const anruf = anrufMit('n', 'beendet')
        expect(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE)).toEqual([])
        anruf.eintraege.zeiten = {reanimation: 1040}
        expect(urteile(reanimationBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.reanimationUnnoetig', 'hinweis', '0:10']])
    })
})

describe('uebergabeBewerten', () => {
    it('zählt ohne Übergabe das Gesprächsende und misst Brand gegen die Zielzeit', () => {
        const anruf = mitWahrheit(anrufMit('f', 'beendet'), FEUER, 'fw.e', '67B01')
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([
            ['bewertung.uebergabeOhne', 'hinweis', ''],
            ['bewertung.uebergabe', 'teilweise', '1:10'],
        ])
        anruf.eintraege.zeiten = {uebergabe: 1030 + 45}
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.uebergabe', 'richtig', '0:45']])
    })

    it('rügt, was bei der Übergabe fehlte, und nennt einen verschärften Code', () => {
        const anruf = anrufMit('m', 'beendet')
        const leicht = {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]}
        anruf.eintraege.zeiten = {uebergabe: 1060}
        anruf.eintraege.uebergeben = {ort: anruf.eintraege.ort, anrufer: anruf.eintraege.anrufer, betroffener: '', abfrage: {pfad: BIS_SITUATION}, hinweise: ''}
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([
            ['bewertung.uebergabe', 'hinweis', '0:30'],
            ['bewertung.uebergabeOhnePunkt', 'falsch', ''],
            ['bewertung.uebergabeOhneCode', 'falsch', ''],
        ])
        anruf.eintraege.uebergeben = {...anruf.eintraege.uebergeben, ort: {...anruf.eintraege.ort, koordinaten: [52.5, 13.4]}, abfrage: leicht}
        anruf.eintraege.abfrage = {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}]}
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([
            ['bewertung.uebergabe', 'hinweis', '0:30'],
            ['bewertung.verschaerft', 'hinweis', '17A01 → 17D01'],
        ])
    })

    it('erwartet bei einer Reanimation die Übergabe kurz nach ihrem Start', () => {
        const anruf = mitWahrheit(anrufMit('r', 'beendet'), [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer-2'}], 'p.e3', '17E01')
        anruf.eintraege.zeiten = {reanimation: 1030 + 60, uebergabe: 1030 + 80}
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.uebergabe', 'richtig', '1:20']])
        anruf.eintraege.zeiten = {reanimation: 1030 + 60, uebergabe: 1030 + 100}
        expect(urteile(uebergabeBewerten(GRAPH, sichtVon(anruf), anruf.szenario, STANDARDZIELE))).toEqual([['bewertung.uebergabe', 'teilweise', '1:40']])
    })
})
