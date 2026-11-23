import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {ladeGebiete, zufallsAdresse} from '../api/gebiete'
import {i18n} from '../i18n'
import ZufallsAdresse from './ZufallsAdresse.vue'

vi.mock('../api/gebiete', () => ({ladeGebiete: vi.fn(), zufallsAdresse: vi.fn()}))

const ADRESSE = {beschriftung: '', strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau', breite: 52.56, laenge: 13.21}

describe('ZufallsAdresse', () => {
    it('zieht im gewählten Gebiet und meldet, wenn es keine Adresse gibt', async () => {
        vi.mocked(ladeGebiete).mockResolvedValue({Spandau: ['Hakenfelde', 'Spandau']})
        vi.mocked(zufallsAdresse).mockResolvedValueOnce(ADRESSE).mockResolvedValueOnce(undefined)
        const ansicht = mount(ZufallsAdresse, {global: {plugins: [i18n]}})
        await flushPromises()
        expect(ansicht.text()).toContain('ganzer Bezirk Spandau')
        await ansicht.get('select').setValue('b:Spandau')
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(zufallsAdresse).toHaveBeenCalledWith({bezirk: 'Spandau', ortsteil: ''})
        expect(ansicht.emitted('adresse')?.[0]).toEqual([ADRESSE])
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(ansicht.get('[role=alert]').text()).toBe('Im gewählten Gebiet gibt es keine Adresse.')
    })

    it('sagt, wenn das Verzeichnis fehlt oder der Server nicht antwortet', async () => {
        vi.mocked(ladeGebiete).mockResolvedValue({})
        vi.mocked(zufallsAdresse).mockResolvedValueOnce(undefined).mockRejectedValueOnce(new TypeError('Failed to fetch'))
        const ansicht = mount(ZufallsAdresse, {global: {plugins: [i18n]}})
        await flushPromises()
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(ansicht.get('[role=alert]').text()).toContain('nicht geladen')
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(ansicht.get('[role=alert]').text()).toBe('Der Server ist nicht erreichbar.')
    })
})
