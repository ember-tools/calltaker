import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import {sichtVon} from '../modell/uebung'
import {gesamtVon, protokoll, zeileVon} from './uebersicht'

describe('uebersicht', () => {
    it('fasst beendete Anrufe zusammen und zählt, wie sie ausgingen', () => {
        const exakt = anrufMit('e', 'beendet')
        exakt.eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e2', code: '17D01'}}
        exakt.eintraege.zeiten = {code: 1090}
        const nah = anrufMit('n', 'beendet')
        nah.eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e1', code: '17A01'}}
        nah.eintraege.zeiten = {code: 1070}
        const zeilen = [exakt, nah].map(a => zeileVon(GRAPH, {anruf: sichtVon(a), szenario: a.szenario}))
        expect(zeilen.map(z => z.code?.stufe)).toEqual(['exakt', 'protokoll'])
        expect(gesamtVon([exakt, nah, anrufMit('x', 'aufgelegt')], zeilen)).toEqual({anrufe: 3, beendet: 2, aufgelegt: 1, codeExakt: 1, codeNah: 1, mittelBisCode: 50, mittelBisUebergabe: undefined})
    })

    it('legt ein Protokoll mit Wahrheit, Einträgen, Zeiten und Bewertung an', () => {
        const beendet = anrufMit('b', 'beendet')
        const datei = protokoll(GRAPH, [beendet, anrufMit('w', 'wartet')], new Date('2026-11-23T10:00:00Z'))
        expect(datei).toMatchObject({format: 'calltaker-protokoll', version: 1, erstellt: '2026-11-23T10:00:00.000Z', abfrageVersion: 1})
        expect(datei.anrufe[0]).toMatchObject({id: 'b', zeiten: {annahme: 30, gespraech: 70}, fehlend: ['fehlt.einsatzort', 'fehlt.code', 'fehlt.name', 'fehlt.rueckrufnummer']})
        expect(datei.anrufe[0]!.bewertung!.map(p => p.phase)).toEqual(['standort', 'abfrage', 'personalien', 'anleitung', 'reanimation', 'uebergabe'])
        expect(datei.anrufe[1]!.bewertung).toBeUndefined()
        expect(datei.anrufe[1]!.szenario.titel).toBe('Sturz w')
    })

    it('fasst Hinweise, Reanimation und Übergabe je Anruf zusammen', () => {
        const graph = {...GRAPH, anleitungen: [
            {id: 'zugang', titel: 'Tür öffnen', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'},
            {id: 'licht', titel: 'Licht', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'},
        ]}
        const anruf = anrufMit('h', 'beendet')
        anruf.eintraege.anleitung = {gegeben: ['zugang']}
        anruf.eintraege.zeiten = {uebergabe: 1060}
        anruf.eintraege.uebergeben = {ort: anruf.eintraege.ort, anrufer: anruf.eintraege.anrufer, betroffener: '', abfrage: {pfad: []}, hinweise: ''}
        const zeile = zeileVon(graph, {anruf: sichtVon(anruf), szenario: anruf.szenario})
        expect(zeile.anleitung).toMatchObject({ist: '1/2', urteil: 'offen'})
        expect(zeile.uebergabe).toMatchObject({feld: 'bewertung.uebergabe', ist: '0:30', urteil: 'falsch'})
        expect(zeile.reanimation).toBeUndefined()
        const korrigiert = zeileVon(graph, {anruf: {...sichtVon(anruf), korrektur: {licht: true}}, szenario: anruf.szenario})
        expect(korrigiert.anleitung).toMatchObject({ist: '2/2', urteil: 'richtig'})
        expect(gesamtVon([anruf], [zeile]).mittelBisUebergabe).toBe(30)
    })
})
