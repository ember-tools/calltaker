import {afterEach, describe, expect, it, vi} from 'vitest'
import {NICHT_ERREICHBAR, anlegen, holeZustand} from './uebung'

describe('api/uebung', () => {
    afterEach(() => vi.unstubAllGlobals())

    it('meldet einen Netzausfall auf Deutsch', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
        await expect(anlegen()).rejects.toThrow(NICHT_ERREICHBAR)
    })

    it('gibt den Grund des Servers weiter', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail": "Diesen Code gibt es nicht."}', {status: 404})))
        await expect(holeZustand('A-XXXXXXXX', 0)).rejects.toMatchObject({status: 404, message: 'Diesen Code gibt es nicht.'})
    })

    it('liefert nichts, wenn sich nichts geändert hat', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, {status: 204})))
        await expect(holeZustand('A-XXXXXXXX', 3)).resolves.toBeNull()
    })
})
