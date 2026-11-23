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

describe('AdressSuche mit ungefähren Treffern', () => {
    it('zeigt ähnlich geschriebene Straßen nach den Orten und markiert sie', async () => {
        vi.useFakeTimers()
        vi.mocked(sucheAdressen).mockResolvedValue([
            {beschriftung: 'Siegmarstraße 25, 12683 Biesdorf', strasse: 'Siegmarstraße', hausnummer: '25', plz: '12683', ortsteil: 'Biesdorf', bezirk: 'Marzahn-Hellersdorf', breite: 52.5, laenge: 13.5, ungefaehr: true},
        ])
        vi.mocked(sucheOrte).mockResolvedValue([{beschriftung: 'Siegmar-Kita (Kita), Biesdorf', name: 'Siegmar-Kita', art: 'Kita', ortsteil: 'Biesdorf', breite: 52.5, laenge: 13.5}])
        const ansicht = mount(AdressSuche, {props: {beschriftung: 'Ort'}, global: {plugins: [i18n]}})
        await ansicht.get('input').setValue('Siegmartstrase 25')
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        vi.useRealTimers()
        const optionen = ansicht.findAll('[role=option]').map(o => o.text())
        expect(optionen[0]).toContain('Siegmar-Kita')
        expect(optionen[1]).toMatch(/^ähnlich\s*Siegmarstraße 25, 12683 Biesdorf$/)
    })
})

describe('AdressSuche in der Reihenfolge der Vorschläge', () => {
    it('bietet Türen, dann Orte, dann Straßen, dann Ähnliches an', async () => {
        vi.useFakeTimers()
        const adresse = (strasse: string, hausnummer: string, ungefaehr = false) => ({beschriftung: `${strasse} ${hausnummer}`.trim(), strasse, hausnummer, plz: '', ortsteil: '', bezirk: '', ungefaehr})
        vi.mocked(sucheAdressen).mockResolvedValue([adresse('Hermannstraße', ''), adresse('Hermannplatz', '1'), adresse('Herrmannweg', '', true)])
        vi.mocked(sucheOrte).mockResolvedValue([{beschriftung: 'Hermannplatz (Bahnhof), Neukölln', name: 'Hermannplatz', art: 'Bahnhof', ortsteil: 'Neukölln', breite: 52.48, laenge: 13.42}])
        const ansicht = mount(AdressSuche, {props: {beschriftung: 'Ort'}, global: {plugins: [i18n]}})
        await ansicht.get('input').setValue('Herman')
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        vi.useRealTimers()
        const optionen = ansicht.findAll('[role=option]').map(o => o.text())
        expect(optionen[0]).toBe('Hermannplatz 1')
        expect(optionen[1]).toContain('Hermannplatz (Bahnhof)')
        expect(optionen[2]).toBe('Hermannstraße')
        expect(optionen[3]).toMatch(/^ähnlich/)
    })
})
