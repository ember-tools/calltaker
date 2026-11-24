import {describe, expect, it} from 'vitest'
import {leereEintraege, type Eintraege} from './eintraege'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'
import {nachtraege, uebergabestand} from './uebergabe'

const graph = testgraph()
const FEUER = [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]

function mit(pfad: Eintraege['abfrage']['pfad'], punkt = true): Eintraege {
    const eintraege = leereEintraege()
    eintraege.abfrage = {pfad}
    if (punkt) eintraege.ort.koordinaten = [52.5, 13.4]
    return eintraege
}

describe('uebergabestand', () => {
    it('braucht Punkt und Protokoll', () => {
        expect(uebergabestand(graph, mit(BIS_SITUATION, false))).toBe('gesperrt')
        expect(uebergabestand(graph, mit(BIS_SITUATION.slice(0, 3)))).toBe('gesperrt')
    })

    it('ist bei Brand mit Ort und Protokoll fällig, im Rettungsdienst erst mit Code', () => {
        expect(uebergabestand(graph, mit(FEUER))).toBe('faellig')
        expect(uebergabestand(graph, mit(BIS_SITUATION))).toBe('bereit')
        expect(uebergabestand(graph, mit([...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]))).toBe('faellig')
    })

    it('ist bei einer Reanimation fällig, sobald der Takt läuft, und danach erfolgt', () => {
        const rea = mit([{knoten: 'rd.09.todeszeichen', antwort: 'keine'}, ...BIS_SITUATION])
        expect(uebergabestand(graph, rea)).toBe('bereit')
        rea.reanimation.laeuft = true
        expect(uebergabestand(graph, rea)).toBe('faellig')
        expect(uebergabestand(graph, mit([...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer-2'}]))).toBe('faellig')
        rea.uebergabe = true
        expect(uebergabestand(graph, rea)).toBe('erfolgt')
    })
})

describe('nachtraege', () => {
    it('nennt, was sich seit der Übergabe geändert hat', () => {
        const eintraege = mit([...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}])
        expect(nachtraege(graph, eintraege).size).toBe(0)
        const {ort, anrufer, betroffener, abfrage, hinweise} = structuredClone(eintraege)
        eintraege.uebergeben = {ort, anrufer, betroffener, abfrage, hinweise}
        expect([...nachtraege(graph, eintraege)]).toEqual([])
        eintraege.hinweise = 'Hund im Haus'
        eintraege.abfrage = {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}]}
        expect([...nachtraege(graph, eintraege)].sort()).toEqual(['code', 'hinweise'])
    })
})
