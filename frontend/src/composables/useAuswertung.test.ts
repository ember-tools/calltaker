import {describe, expect, it} from 'vitest'
import {ref} from 'vue'
import {anrufMit, zustandMit} from '../modell/ausbilder.test-hilfe'
import type {Rolle, ZustandFuer} from '../modell/uebung'
import {useAuswertung} from './useAuswertung'

describe('useAuswertung für den Ausbilder', () => {
    it('nimmt nur beendete Anrufe, als Sicht des Trainees mit ihrer Wahrheit', () => {
        const zustand = ref<ZustandFuer<Rolle> | null>(zustandMit([anrufMit('b', 'beendet'), anrufMit('l'), anrufMit('a', 'aufgelegt')]))
        const {anrufe, ausgewertet} = useAuswertung(zustand, 'ausbilder')
        expect(anrufe.value).toHaveLength(3)
        expect(ausgewertet.value.map(a => a.anruf.id)).toEqual(['b'])
        expect(ausgewertet.value[0]!.anruf).not.toHaveProperty('szenario')
        expect(ausgewertet.value[0]!.szenario.titel).toBe('Sturz b')
    })
})
