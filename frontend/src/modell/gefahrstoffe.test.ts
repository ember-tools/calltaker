import {describe, expect, it} from 'vitest'
import {gefahrenzahlDeuten, stoffeSuchen, stoffeZu, type Stoff} from './gefahrstoffe'

const STOFFE: Stoff[] = [
    {un: '1203', gefahrenzahl: '33', klasse: '3', bezeichnung: 'Benzin oder Ottokraftstoffe'},
    {un: '1428', gefahrenzahl: 'X423', klasse: '4.3', bezeichnung: 'Natrium'},
    {un: '1017', gefahrenzahl: '268', klasse: '2', bezeichnung: 'Chlor'},
    {un: '2014', gefahrenzahl: '58', klasse: '5.1', bezeichnung: 'Wasserstoffperoxid, wässerige Lösung'},
]

describe('gefahrenzahlDeuten', () => {
    it('liest jede Ziffer, verstärkt verdoppelte und warnt bei X vor Wasser', () => {
        expect(gefahrenzahlDeuten('33')).toEqual(['stark entzündbar (Flüssigkeit oder Gas)'])
        expect(gefahrenzahlDeuten('268')).toEqual(['Gas, Druck oder chemische Reaktion', 'giftig', 'ätzend'])
        expect(gefahrenzahlDeuten('x423')[0]).toContain('kein Wasser')
        expect(gefahrenzahlDeuten('30')).toEqual(['entzündbar (Flüssigkeit oder Gas)'])
        expect(gefahrenzahlDeuten('abc')).toEqual([])
        expect(gefahrenzahlDeuten('223')).toEqual(['tiefgekühlt verflüssigtes Gas', 'entzündbar (Flüssigkeit oder Gas)'])
    })
})

describe('stoffeZu und stoffeSuchen', () => {
    it('findet nach Nummer und nach Namen, Anfänge zuerst', () => {
        expect(stoffeZu(STOFFE, '1203').map(s => s.bezeichnung)).toEqual(['Benzin oder Ottokraftstoffe'])
        expect(stoffeZu(STOFFE, '12')).toEqual([])
        expect(stoffeSuchen(STOFFE, 'chl').map(s => s.un)).toEqual(['1017'])
        expect(stoffeSuchen(STOFFE, 'was').map(s => s.un)).toEqual(['2014'])
        expect(stoffeSuchen(STOFFE, 'st').map(s => s.un)).toEqual([])
    })
})
