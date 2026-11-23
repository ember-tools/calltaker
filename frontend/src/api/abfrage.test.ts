import {afterEach, describe, expect, it, vi} from 'vitest'
import {ladeAbfrage} from './abfrage'

describe('ladeAbfrage', () => {
    afterEach(() => vi.unstubAllGlobals())

    it('liefert den Graphen des Servers', async () => {
        const graph = {meta: {version: 1, wurzel: 'fachrichtung'}, knoten: {}, endpunkte: []}
        const abruf = vi.fn().mockResolvedValue(new Response(JSON.stringify(graph)))
        vi.stubGlobal('fetch', abruf)
        await expect(ladeAbfrage()).resolves.toEqual(graph)
        expect(abruf).toHaveBeenCalledWith('/api/abfrage')
    })

    it('meldet einen Fehler des Servers', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', {status: 500})))
        await expect(ladeAbfrage()).rejects.toThrow('HTTP 500')
    })
})
