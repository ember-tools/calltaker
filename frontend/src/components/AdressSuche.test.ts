import {flushPromises, mount} from '@vue/test-utils'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {sucheAdressen} from '../api/adressen'
import {sucheOrte} from '../api/orte'
import {PAUSE_MS} from '../composables/useAdresssuche'
import {i18n} from '../i18n'
import AdressSuche from './AdressSuche.vue'

vi.mock('../api/adressen', () => ({sucheAdressen: vi.fn()}))
vi.mock('../api/orte', () => ({sucheOrte: vi.fn()}))

const tuer = {beschriftung: 'Karl-Marx-Straße 92, 12043 Neukölln', strasse: 'Karl-Marx-Straße', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln', bezirk: 'Neukölln', breite: 52.4793, laenge: 13.4385}
const ort = {beschriftung: 'U Hermannplatz, Neukölln', name: 'U Hermannplatz', art: 'Bahnhof', ortsteil: 'Neukölln', breite: 52.48, laenge: 13.42}

describe('AdressSuche', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.resetAllMocks()
    })

    it('wählt mit Pfeiltaste und Enter eine Adresse', async () => {
        vi.mocked(sucheAdressen).mockResolvedValue([tuer])
        vi.mocked(sucheOrte).mockResolvedValue([ort])
        const ansicht = mount(AdressSuche, {props: {beschriftung: 'Einsatzort'}, global: {plugins: [i18n]}})
        const feld = ansicht.get('input')
        await feld.setValue('Karl-Marx-Str 92')
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        await flushPromises()
        expect(ansicht.findAll('[role=option]')).toHaveLength(2)
        expect(ansicht.text()).toContain('© OpenStreetMap-Mitwirkende, ODbL')
        await feld.trigger('keydown', {key: 'ArrowDown'})
        await feld.trigger('keydown', {key: 'Enter'})
        expect(ansicht.emitted('adresse')?.[0]).toEqual([tuer])
        expect((feld.element as HTMLInputElement).value).toBe(tuer.beschriftung)
    })

    it('meldet einen gewählten Ort', async () => {
        vi.mocked(sucheAdressen).mockResolvedValue([])
        vi.mocked(sucheOrte).mockResolvedValue([ort])
        const ansicht = mount(AdressSuche, {props: {beschriftung: 'Einsatzort'}, global: {plugins: [i18n]}})
        await ansicht.get('input').setValue('Hermannplatz')
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        await flushPromises()
        await ansicht.get('[role=option]').trigger('mousedown')
        expect(ansicht.emitted('ort')?.[0]).toEqual([ort])
    })
})
