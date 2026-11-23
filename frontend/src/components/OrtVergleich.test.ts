import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import {anrufMit} from '../modell/ausbilder.test-hilfe'
import OrtVergleich from './OrtVergleich.vue'

vi.mock('./KarteLeaflet.vue', () => ({default: {props: ['punkte', 'beschriftung'], template: '<div data-karte>{{ punkte.map(p => p.art).join(",") }}</div>'}}))

describe('OrtVergleich', () => {
    it('zeigt wahren und erfassten Punkt mit dem Abstand', async () => {
        const anruf = anrufMit('a')
        const ansicht = mount(OrtVergleich, {props: {anruf}, global: {plugins: [i18n]}})
        expect(ansicht.get('[data-karte]').text()).toBe('wahrheit')
        expect(ansicht.text()).toContain('Noch kein erfasster Punkt')
        const mitPunkt = anrufMit('a')
        mitPunkt.eintraege.ort.koordinaten = [52.5672, 13.2122]
        await ansicht.setProps({anruf: mitPunkt})
        expect(ansicht.get('[data-karte]').text()).toBe('wahrheit,erfasst')
        expect(ansicht.text()).toContain('100 m vom wahren Punkt')
    })
})
