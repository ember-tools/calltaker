import {describe, expect, it} from 'vitest'
import {vergleich, vergleichsform} from './vergleich'

describe('vergleich', () => {
    it('liest Schreibweisen von Straßen gleich', () => {
        const formen = ['Karl-Marx-Straße', 'Karl-Marx-Str.', 'karl marx str', 'Karl-Marx-Strasse'].map(vergleichsform)
        expect(new Set(formen).size).toBe(1)
        expect(vergleichsform('Stralauer Allee')).toBe('stralauerallee')
    })

    it('lässt Leeres offen und urteilt sonst nach dem Test', () => {
        expect(vergleich('f', 'a', '  ', () => true).urteil).toBe('offen')
        expect(vergleich('f', 'a', 'b', ist => ist === 'a').urteil).toBe('falsch')
        expect(vergleich('f', 'a', 'a', ist => ist === 'a').urteil).toBe('richtig')
    })
})
