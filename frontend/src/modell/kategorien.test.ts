import {describe, expect, it} from 'vitest'
import {kategorievorschlaege, passendeCodes} from './kategorien'
import {testgraph} from './testgraph.test-hilfe'

describe('kategorievorschlaege', () => {
    it('schlägt Stufen, erste Wörter und ganze Kategorien mit ihrer Zahl an Codes vor', () => {
        const vorschlaege = kategorievorschlaege(testgraph())
        expect(vorschlaege.map(v => v.wert)).toEqual(['BRAND', 'RD1', 'RD2', 'RD4', 'RD1NC', 'RD2NC', 'RD4C', 'BRAND 2', 'RD1NC REA.', 'RD2NC.', 'RD4C.'])
        expect(vorschlaege.find(v => v.wert === 'RD1')?.anzahl).toBe(1)
    })

    it('zählt, was ein getippter Filter übrig lässt', () => {
        expect(passendeCodes(testgraph(), 'rd')).toBe(3)
        expect(passendeCodes(testgraph(), 'XYZ')).toBe(0)
    })
})
