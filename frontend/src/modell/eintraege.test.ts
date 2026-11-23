import {describe, expect, it} from 'vitest'
import {leereEintraege, mitKorrektur} from './eintraege'

describe('mitKorrektur', () => {
    it('setzt und nimmt gegebene Hinweise nach dem Ausbilder', () => {
        const eintraege = {...leereEintraege(), anleitung: {gegeben: ['a', 'b']}}
        expect(mitKorrektur(eintraege, {b: false, c: true}).anleitung.gegeben).toEqual(['a', 'c'])
        expect(mitKorrektur(eintraege).anleitung.gegeben).toEqual(['a', 'b'])
    })
})
