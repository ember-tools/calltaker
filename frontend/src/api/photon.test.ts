import {afterEach, describe, expect, it, vi} from 'vitest'
import {sucheOrte} from './photon'

/**
 * A Photon feature as GeoJSON delivers it, with its point as (longitude, latitude).
 *
 * @param name the place's name
 * @param eigenschaften further properties
 * @returns the feature
 */
const feature = (name: string, eigenschaften: Record<string, string> = {}) => ({
    geometry: {coordinates: [13.4246, 52.4797]},
    properties: {name, state: 'Berlin', district: 'Neukölln', ...eigenschaften},
})

describe('sucheOrte', () => {
    afterEach(() => vi.unstubAllGlobals())

    it('liefert Orte in Berlin ohne Hausnummer, mit gedrehtem Punkt', async () => {
        const abruf = vi.fn().mockResolvedValue(new Response(JSON.stringify({features: [
            feature('U Hermannplatz'),
            feature('Karl-Marx-Straße 92', {housenumber: '92'}),
            feature('Schönefeld', {state: 'Brandenburg'}),
        ]})))
        vi.stubGlobal('fetch', abruf)
        const orte = await sucheOrte('Hermannplatz', new AbortController().signal)
        expect(orte).toEqual([{beschriftung: 'U Hermannplatz, Neukölln', name: 'U Hermannplatz', ortsteil: 'Neukölln', breite: 52.4797, laenge: 13.4246}])
        const adresse = new URL(abruf.mock.calls[0]![0] as string)
        expect(adresse.origin + adresse.pathname).toBe('https://photon.komoot.io/api/')
        expect(adresse.searchParams.get('bbox')).toBe('13.08,52.33,13.77,52.68')
        expect(adresse.searchParams.get('lang')).toBe('de')
    })

    it('fragt dieselbe Suche nur einmal', async () => {
        const abruf = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({features: [feature('Tempelhofer Feld')]}))))
        vi.stubGlobal('fetch', abruf)
        await sucheOrte('Tempelhofer Feld', new AbortController().signal)
        await sucheOrte('tempelhofer feld ', new AbortController().signal)
        expect(abruf).toHaveBeenCalledTimes(1)
    })
})
