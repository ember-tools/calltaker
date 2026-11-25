import {describe, expect, it} from 'vitest'
import {deutscheBuchstaben, nameGleich, phonetik, vergleich, vergleichsform} from './vergleich'

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

describe('vergleich von Namen', () => {
    it('schreibt fremde Buchstaben deutsch', () => {
        expect(deutscheBuchstaben('Yılmaz Şahin Łukasz Øster Gül René')).toBe('yilmaz sahin lukasz oster guel rene')
    })

    it('liest lautgleiche Namen gleich', () => {
        expect(phonetik('Meier')).toBe(phonetik('Mayer'))
        expect(phonetik('Yılmaz')).toBe(phonetik('Yilmas'))
        expect(phonetik('Müller')).toBe(phonetik('Mueller'))
        expect(phonetik('Schmidt')).not.toBe(phonetik('Schneider'))
    })

    it('nimmt den ganzen Namen, den Nachnamen oder einen lautgleichen an', () => {
        expect(nameGleich('Leyla Yilmaz', 'Leyla Yılmaz')).toBe(true)
        expect(nameGleich('Yilmaz', 'Leyla Yılmaz')).toBe(true)
        expect(nameGleich('Frau Jilmas', 'Leyla Yılmaz')).toBe(true)
        expect(nameGleich('Meyer', 'Ines Maier')).toBe(true)
        expect(nameGleich('Leyla Kaya', 'Leyla Yılmaz')).toBe(false)
    })
})
