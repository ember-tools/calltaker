import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
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
