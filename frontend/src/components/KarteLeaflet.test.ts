import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import L from 'leaflet'
import {i18n} from '../i18n'
import KarteLeaflet from './KarteLeaflet.vue'

/**
 * Mounts the map into the document, which Leaflet needs to measure.
 *
 * @param props the map's properties
 * @returns the mounted map
 */
function karte(props: Record<string, unknown>) {
    return mount(KarteLeaflet, {props: {beschriftung: 'Karte', ...props}, global: {plugins: [i18n]}, attachTo: document.body})
}

describe('KarteLeaflet', () => {
    it('lädt Kacheln aus dem eigenen Cache und nennt OpenStreetMap', () => {
        const ansicht = karte({})
        expect(ansicht.html()).toContain('OpenStreetMap-Mitwirkende')
        expect(ansicht.find('img.leaflet-tile').attributes('src')).toMatch(/^\/kacheln\/12\/\d+\/\d+\.png$/)
        ansicht.unmount()
    })

    it('zeichnet erfasste und wahre Punkte', async () => {
        const ansicht = karte({punkte: [{breite: 52.479, laenge: 13.438, art: 'wahrheit'}, {breite: 52.4791, laenge: 13.4381, art: 'erfasst'}]})
        expect(ansicht.findAll('path.leaflet-interactive')).toHaveLength(2)
        await ansicht.setProps({punkte: [{breite: 52.479, laenge: 13.438, art: 'erfasst'}]})
        expect(ansicht.findAll('path.leaflet-interactive')).toHaveLength(1)
        ansicht.unmount()
    })

    it('meldet einen gesetzten Punkt nur, wenn Setzen erlaubt ist', async () => {
        const gesperrt = karte({})
        await gesperrt.get('[role=region]').trigger('click', {clientX: 10, clientY: 10})
        expect(gesperrt.emitted('gesetzt')).toBeUndefined()
        gesperrt.unmount()
        const offen = karte({setzbar: true})
        await offen.get('[role=region]').trigger('click', {clientX: 10, clientY: 10})
        expect(offen.emitted('gesetzt')?.[0]).toHaveLength(2)
        offen.unmount()
    })
})

describe('KarteLeaflet mit mehreren Punkten', () => {
    it('zeigt mehrere Punkte zugleich und einen allein von nah', async () => {
        const {default: L} = await import('leaflet')
        const passen = vi.spyOn(L.Map.prototype, 'fitBounds')
        const zentrieren = vi.spyOn(L.Map.prototype, 'setView')
        const ansicht = karte({punkte: [{breite: 52.479, laenge: 13.438, art: 'wahrheit'}, {breite: 52.49, laenge: 13.45, art: 'erfasst'}]})
        expect(passen).toHaveBeenCalledTimes(1)
        zentrieren.mockClear()
        await ansicht.setProps({punkte: [{breite: 52.5, laenge: 13.4, art: 'erfasst'}]})
        expect(zentrieren.mock.calls[0]![1]).toBeGreaterThanOrEqual(16)
        ansicht.unmount()
        vi.restoreAllMocks()
    })

    it('zeichnet die Funkzelle gestrichelt und nicht anklickbar', async () => {
        const ansicht = karte({funkzelle: {mitte: [52.5, 13.4], radius: 900}})
        const kreis = ansicht.findAll('path').filter(p => p.attributes('stroke-dasharray') === '6 6')
        expect(kreis).toHaveLength(1)
        expect(kreis[0]!.classes()).not.toContain('leaflet-interactive')
        await ansicht.setProps({funkzelle: undefined})
        expect(ansicht.findAll('path').filter(p => p.attributes('stroke-dasharray') === '6 6')).toHaveLength(0)
        ansicht.unmount()
    })

    it('zeigt die Funkzelle ganz, mit den Punkten, und rückt nur bei einer neuen Zelle nach', async () => {
        const passen = vi.spyOn(L.Map.prototype, 'fitBounds')
        const zelle = {mitte: [52.5, 13.4] as [number, number], radius: 900}
        const ansicht = karte({funkzelle: zelle})
        expect(passen).toHaveBeenCalledTimes(1)
        await ansicht.setProps({funkzelle: {...zelle}})
        expect(passen).toHaveBeenCalledTimes(1)
        await ansicht.setProps({punkte: [{breite: 52.501, laenge: 13.401, art: 'wahrheit'}]})
        expect(passen).toHaveBeenCalledTimes(2)
        const grenzen = passen.mock.calls[1]![0] as L.LatLngBounds
        expect(grenzen.contains(L.latLng(52.5, 13.4).toBounds(1800))).toBe(true)
        passen.mockRestore()
        ansicht.unmount()
    })
})
