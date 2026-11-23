import {flushPromises, mount} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import WarntafelFeld from './WarntafelFeld.vue'

describe('WarntafelFeld', () => {
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it('zeigt Stoff und Gefahren zur Nummer und füllt die Tafel über den Namen', async () => {
        vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({herkunft: {}, stoffe: [
            {un: '1428', gefahrenzahl: 'X423', klasse: '4.3', bezeichnung: 'Natrium'},
            {un: '1203', gefahrenzahl: '33', klasse: '3', bezeichnung: 'Benzin'},
        ]})))))
        const ansicht = mount(WarntafelFeld, {props: {'modelValue': {un: '1428', gefahrenzahl: 'X423'}, 'onUpdate:modelValue': (wert: unknown) => ansicht.setProps({modelValue: wert as {un: string, gefahrenzahl: string}})}, global: {plugins: [i18n]}})
        await flushPromises()
        expect(ansicht.text()).toContain('Natrium')
        expect(ansicht.text()).toContain('kein Wasser')
        await ansicht.findAll('input').at(2)!.setValue('benz')
        await ansicht.get('ul.list-none button').trigger('click')
        expect(ansicht.props('modelValue')).toEqual({un: '1203', gefahrenzahl: '33'})
    })
})
