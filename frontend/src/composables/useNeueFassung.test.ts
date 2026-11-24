import {flushPromises} from '@vue/test-utils'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {PRUEFEN_ALLE_MS, useNeueFassung} from './useNeueFassung'

const antwort = (gebaut: string) => Promise.resolve(new Response(JSON.stringify({gebaut})))

describe('useNeueFassung', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.unstubAllGlobals()
    })

    it('merkt, wenn der Server einen anderen Bau ausliefert', async () => {
        const holen = vi.fn(() => antwort(__GEBAUT__))
        vi.stubGlobal('fetch', holen)
        const neu = useNeueFassung()
        await flushPromises()
        expect(neu.value).toBe(false)
        holen.mockImplementation(() => antwort('2099-01-01T00:00:00Z'))
        vi.advanceTimersByTime(PRUEFEN_ALLE_MS)
        await flushPromises()
        expect(neu.value).toBe(true)
        expect(holen).toHaveBeenCalledWith('/fassung.json', {cache: 'no-store'})
    })

    it('bleibt still, wenn es keine Fassungsdatei gibt', async () => {
        vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('', {status: 404}))))
        const neu = useNeueFassung()
        await flushPromises()
        expect(neu.value).toBe(false)
    })
})
