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
            {un: '1993', gefahrenzahl: '30', klasse: '3', bezeichnung: 'Entzündbarer flüssiger Stoff'},
            {un: '1993', gefahrenzahl: '33', klasse: '3', bezeichnung: 'Entzündbarer flüssiger Stoff'},
        ]})))))
        const ansicht = mount(WarntafelFeld, {props: {'modelValue': {un: '1428', gefahrenzahl: 'X423'}, 'onUpdate:modelValue': (wert: unknown) => ansicht.setProps({modelValue: wert as {un: string, gefahrenzahl: string}})}, global: {plugins: [i18n]}})
        await flushPromises()
        expect(ansicht.text()).toContain('Natrium')
        expect(ansicht.text()).toContain('kein Wasser')
        await ansicht.get('[role=combobox]').setValue('benz')
        await ansicht.get('[role=option]').trigger('mousedown')
        expect(ansicht.props('modelValue')).toEqual({un: '1203', gefahrenzahl: '33'})
    })
})

describe('WarntafelFeld mit UN-Nummer', () => {
    it('ergänzt eine eindeutige Gefahrenzahl und bietet mehrere zur Wahl an', async () => {
        const ansicht = mount(WarntafelFeld, {props: {'modelValue': {un: '', gefahrenzahl: ''}, 'onUpdate:modelValue': (wert: unknown) => ansicht.setProps({modelValue: wert as {un: string, gefahrenzahl: string}})}, global: {plugins: [i18n]}})
        await flushPromises()
        const un = ansicht.get('input[aria-label="UN-Nummer (unten)"]')
        await un.setValue('1203')
        expect(ansicht.props('modelValue')).toEqual({un: '1203', gefahrenzahl: '33'})
        await un.setValue('1993')
        expect(ansicht.props('modelValue')).toEqual({un: '1993', gefahrenzahl: ''})
        await ansicht.findAll('button').find(b => b.text() === '30')!.trigger('click')
        expect(ansicht.props('modelValue')).toEqual({un: '1993', gefahrenzahl: '30'})
        await ansicht.get('input[aria-label="Gefahrenzahl (oben)"]').setValue('X423')
        await un.setValue('1203')
        expect(ansicht.props('modelValue')).toEqual({un: '1203', gefahrenzahl: 'X423'})
    })
})

describe('WarntafelFeld mit Stoffnamen', () => {
    it('vervollständigt den Namen per Tastatur', async () => {
        const ansicht = mount(WarntafelFeld, {props: {'modelValue': {un: '', gefahrenzahl: ''}, 'onUpdate:modelValue': (wert: unknown) => ansicht.setProps({modelValue: wert as {un: string, gefahrenzahl: string}})}, global: {plugins: [i18n]}})
        await flushPromises()
        const feld = ansicht.get('[role=combobox]')
        await feld.setValue('ent')
        expect(feld.attributes('aria-expanded')).toBe('true')
        expect(ansicht.findAll('[role=option]').length).toBe(2)
        await feld.trigger('keydown', {key: 'ArrowDown'})
        expect(feld.attributes('aria-activedescendant')).toBe('warntafel-stoff-1')
        await feld.trigger('keydown', {key: 'Enter'})
        expect(ansicht.props('modelValue')).toEqual({un: '1993', gefahrenzahl: '33'})
        expect(ansicht.find('[role=listbox]').exists()).toBe(false)
    })
})
