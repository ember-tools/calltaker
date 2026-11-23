import {describe, expect, it} from 'vitest'
import {anrufMit} from './ausbilder.test-hilfe'
import {sichtVon} from './uebung'

describe('sichtVon', () => {
    it('zeigt die Nummer, die der Trainee sieht, und keine Wahrheit', () => {
        const anruf = anrufMit('a')
        expect(sichtVon(anruf)).toMatchObject({id: 'a', rufnummer: '491761234567', rufnummerUnterdrueckt: false})
        expect(sichtVon(anruf)).not.toHaveProperty('szenario')
        anruf.szenario.anrufer = {name: 'X', rufnummerUnterdrueckt: true, rueckrufnummer: '4930123'}
        expect(sichtVon(anruf)).toMatchObject({rufnummer: undefined, rufnummerUnterdrueckt: true})
    })
})
