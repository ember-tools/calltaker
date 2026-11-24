import {describe, expect, it} from 'vitest'
import {leereEintraege} from './eintraege'
import {altersgruppe, gruppeAusAlter, reanimationFaellig, wartetAufKraefte, wirksameGruppe} from './reanimation'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'

describe('reanimationFaellig', () => {
    const graph = testgraph()

    it('greift bei einem Stillstandscode', () => {
        expect(reanimationFaellig(graph, {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer-2'}]})).toBe(true)
        expect(reanimationFaellig(graph, {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}]})).toBe(false)
        expect(reanimationFaellig(graph, {pfad: BIS_SITUATION})).toBe(false)
    })

    it('greift, sobald keine Todeszeichen da sind, noch vor dem Code', () => {
        expect(reanimationFaellig(graph, {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]})).toBe(true)
        expect(reanimationFaellig(graph, {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'verwesung'}]})).toBe(false)
    })
})

describe('wartetAufKraefte', () => {
    it('hält am Telefon, solange die Reanimation läuft und die Kräfte nicht da sind', () => {
        const eintraege = leereEintraege()
        expect(wartetAufKraefte(eintraege, undefined, 100)).toBe(false)
        eintraege.zeiten = {reanimation: 50}
        expect(wartetAufKraefte(eintraege, undefined, 100)).toBe(true)
        expect(wartetAufKraefte(eintraege, 150, 100)).toBe(true)
        expect(wartetAufKraefte(eintraege, 150, 150)).toBe(false)
    })
})

describe('altersgruppe', () => {
    const alter = (wert: string) => ({knoten: 'rd.alter', wert})
    const k6 = (antwort: string) => ({knoten: 'rd.09.k6', antwort})

    it('nimmt die Altersantworten des Stillstandsprotokolls', () => {
        expect(altersgruppe([k6('bei-patientenalter-bis-30-tage')]).gruppe).toBe('saeugling')
        expect(altersgruppe([{knoten: 'rd.hauptbeschwerde', antwort: 'schwangerschaft-geburt-fehlgeburt'}, k6('bei-patientenalter-bis-30-tage')]).gruppe).toBe('neugeborenes')
        expect(altersgruppe([k6('bei-patientenalter-bis-12-jahre')]).gruppe).toBe('kind')
        expect(altersgruppe([alter('70'), k6('bei-patientenalter-aelter-12-jahre')])).toEqual({gruppe: 'erwachsener', sicher: true, alter: '70'})
        expect(altersgruppe([alter('8 Monate'), k6('bei-patientenalter-bis-12-jahre')]).gruppe).toBe('saeugling')
        expect(altersgruppe([], 'RD1NC NNAD.').gruppe).toBe('saeugling')
        expect(altersgruppe([{knoten: 'rd.24.k1', antwort: 'x'}], 'RD1NC NNAD.').gruppe).toBe('neugeborenes')
    })

    it('liest sonst das getippte Alter', () => {
        expect(altersgruppe([alter('8 Monate')]).gruppe).toBe('saeugling')
        expect(altersgruppe([alter('3 Tage')]).gruppe).toBe('saeugling')
        expect(altersgruppe([{knoten: 'rd.hauptbeschwerde', antwort: 'schwangerschaft-geburt-fehlgeburt'}, alter('3 Tage')]).gruppe).toBe('neugeborenes')
        expect(altersgruppe([alter('12')]).gruppe).toBe('kind')
        expect(altersgruppe([alter('13')]).gruppe).toBe('erwachsener')
        expect(altersgruppe([alter('0')]).gruppe).toBe('saeugling')
    })

    it('nimmt bei unbekanntem Alter die Erwachsenenschritte und sagt, dass es offen ist', () => {
        expect(altersgruppe([{knoten: 'rd.alter'}])).toEqual({gruppe: 'erwachsener', sicher: false, alter: undefined})
        expect(altersgruppe([k6('bei-patientenalter-unbekannt')]).sicher).toBe(false)
    })

    it('zählt Wochen und Monate über die Grenzen richtig', () => {
        expect(gruppeAusAlter('2 Wochen', true)).toBe('neugeborenes')
        expect(gruppeAusAlter('6 Wochen', true)).toBe('saeugling')
        expect(gruppeAusAlter('18 Monate', false)).toBe('kind')
        expect(gruppeAusAlter('1 Jahr 3 Monate', false)).toBe('kind')
        expect(gruppeAusAlter('0 Jahre 5 Monate', false)).toBe('saeugling')
        expect(gruppeAusAlter('14 Jahre', false)).toBe('erwachsener')
        expect(gruppeAusAlter('unbekannt', false)).toBeUndefined()
    })

    it('lässt die Wahl des Trainees vorgehen', () => {
        const eintraege = leereEintraege()
        eintraege.abfrage = {pfad: [alter('70')]}
        expect(wirksameGruppe(testgraph(), eintraege)).toMatchObject({gruppe: 'erwachsener', gewaehlt: false})
        eintraege.reanimation = {...eintraege.reanimation, gruppe: 'kind'}
        expect(wirksameGruppe(testgraph(), eintraege)).toMatchObject({gruppe: 'kind', gewaehlt: true, sicher: true})
    })
})
