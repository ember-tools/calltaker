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
        expect(gesamtVon([exakt, nah, anrufMit('x', 'aufgelegt')], zeilen)).toEqual({anrufe: 3, beendet: 2, aufgelegt: 1, codeExakt: 1, codeNah: 1, mittelBisCode: 50})
    })

    it('legt ein Protokoll mit Wahrheit, Einträgen, Zeiten und Bewertung an', () => {
        const beendet = anrufMit('b', 'beendet')
        const datei = protokoll(GRAPH, [beendet, anrufMit('w', 'wartet')], new Date('2026-11-23T10:00:00Z'))
        expect(datei).toMatchObject({format: 'calltaker-protokoll', version: 1, erstellt: '2026-11-23T10:00:00.000Z', abfrageVersion: 1})
        expect(datei.anrufe[0]).toMatchObject({id: 'b', zeiten: {annahme: 30, gespraech: 70}, fehlend: ['fehlt.einsatzort', 'fehlt.code', 'fehlt.name', 'fehlt.rueckrufnummer']})
        expect(datei.anrufe[0]!.bewertung!.map(p => p.phase)).toEqual(['standort', 'abfrage', 'personalien'])
        expect(datei.anrufe[1]!.bewertung).toBeUndefined()
        expect(datei.anrufe[1]!.szenario.titel).toBe('Sturz w')
    })
})
