import {describe, expect, it} from 'vitest'
import {anzeigen, gleich, normalisieren} from './rufnummer'

describe('rufnummer', () => {
    it.each([
        ['0176 1234567', '491761234567'],
        ['+49 176 1234567', '491761234567'],
        ['0049-176-1234567', '491761234567'],
        ['030 / 685 322 07', '493068532207'],
        ['+49 (0)30 68532207', '493068532207'],
        ['+49 030 68532207', '493068532207'],
    ])('normalisiert %s', (eingabe, ziffern) => {
        expect(normalisieren(eingabe)).toBe(ziffern)
    })

    it.each([
        ['493068532207', '030 68532207'],
        ['491761234567', '0176 1234567'],
        ['4940123456', '040123456'],
        ['43123456', '+43123456'],
        ['', ''],
    ])('zeigt %s an', (ziffern, anzeige) => {
        expect(anzeigen(ziffern)).toBe(anzeige)
    })

    it('vergleicht unabhängig von der Schreibweise', () => {
        expect(gleich('0176 1234567', '+491761234567')).toBe(true)
        expect(gleich('+49 (0)30 68532207', '030 68532207')).toBe(true)
        expect(gleich('0176 1234567', '0176 1234568')).toBe(false)
    })
})
