import {describe, expect, it} from 'vitest'
import {gefahrenzahlDeuten, gefahrenzahlenZu, stoffeSuchen, stoffeZu, type Stoff} from './gefahrstoffe'

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

    it('reads 90 and 99 as miscellaneous dangerous substances, not as a violent reaction', () => {
        expect(gefahrenzahlDeuten('90')).toEqual(['umweltgefährdender Stoff; verschiedene gefährliche Stoffe'])
        expect(gefahrenzahlDeuten('99')).toEqual(['verschiedene gefährliche erwärmte Stoffe'])
    })

    it('still reads a 9 after the first digit as a spontaneous violent reaction', () => {
        expect(gefahrenzahlDeuten('339')).toEqual(['stark entzündbar (Flüssigkeit oder Gas)', 'Gefahr einer spontanen heftigen Reaktion'])
    })

    it('intensifies a doubled digit and ignores the padding 0', () => {
        expect(gefahrenzahlDeuten('33')).toEqual(['stark entzündbar (Flüssigkeit oder Gas)'])
        expect(gefahrenzahlDeuten('886')).toEqual(['stark ätzend', 'giftig'])
        expect(gefahrenzahlDeuten('30')).toEqual(['entzündbar (Flüssigkeit oder Gas)'])
        expect(gefahrenzahlDeuten('80')).toEqual(['ätzend'])
    })

    it('gives the special combinations of ADR 5.3.2.3.2 their own meaning', () => {
        expect(gefahrenzahlDeuten('22')).toEqual(['tiefgekühlt verflüssigtes Gas, erstickend'])
        expect(gefahrenzahlDeuten('333')).toEqual(['pyrophorer flüssiger Stoff'])
        expect(gefahrenzahlDeuten('44')).toEqual(['entzündbarer fester Stoff, der sich bei erhöhter Temperatur in geschmolzenem Zustand befindet'])
        expect(gefahrenzahlDeuten('423')).toEqual(['fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet'])
        expect(gefahrenzahlDeuten('539')).toEqual(['entzündbares organisches Peroxid'])
        expect(gefahrenzahlDeuten('606')).toEqual(['ansteckungsgefährlicher Stoff'])
        expect(gefahrenzahlDeuten('842')).toEqual(['ätzender fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet'])
    })

    it('puts the water warning first before an X and uses the X wording where ADR has one', () => {
        expect(gefahrenzahlDeuten('X423')).toEqual([
            'reagiert gefährlich mit Wasser, kein Wasser verwenden',
            'fester Stoff, der mit Wasser reagiert und entzündbare Gase bildet',
        ])
        expect(gefahrenzahlDeuten('X462')).toEqual([
            'reagiert gefährlich mit Wasser, kein Wasser verwenden',
            'fester Stoff, der mit Wasser gefährlich reagiert und giftige Gase bildet',
        ])
        expect(gefahrenzahlDeuten('X88')).toEqual(['reagiert gefährlich mit Wasser, kein Wasser verwenden', 'stark ätzend'])
    })
})

describe('stoffeZu und stoffeSuchen', () => {
    it('findet nach Nummer und nach Namen, Anfänge zuerst', () => {
        expect(stoffeZu(STOFFE, '1203').map(s => s.bezeichnung)).toEqual(['Benzin oder Ottokraftstoffe'])
        expect(stoffeZu(STOFFE, '12')).toEqual([])
        expect(stoffeSuchen(STOFFE, 'chl').map(s => s.un)).toEqual(['1017'])
        expect(stoffeSuchen(STOFFE, 'was').map(s => s.un)).toEqual(['2014'])
        expect(stoffeSuchen(STOFFE, 's').map(s => s.un)).toEqual([])
    })
})

describe('gefahrenzahlenZu', () => {
    it('nennt jede gültige Gefahrenzahl einer UN-Nummer einmal', () => {
        const liste: Stoff[] = [...STOFFE, {un: '1203', gefahrenzahl: '33', klasse: '3', bezeichnung: 'Benzin, anders'}, {un: '1203', gefahrenzahl: '?', klasse: '3', bezeichnung: 'x'}]
        expect(gefahrenzahlenZu(liste, '1203')).toEqual(['33'])
        expect(gefahrenzahlenZu(liste, '9999')).toEqual([])
    })
})
