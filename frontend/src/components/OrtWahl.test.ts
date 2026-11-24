import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import type {Ortsangabe} from '../modell/ort'
import AdressSuche from './AdressSuche.vue'
import OrtWahl from './OrtWahl.vue'

vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))

const leer: Ortsangabe = {adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: ''}, objekt: ''}

describe('OrtWahl', () => {
    it('übernimmt eine gewählte Adresse mit ihrem Punkt', async () => {
        const ansicht = mount(OrtWahl, {props: {modelValue: leer}, global: {plugins: [i18n]}, attachTo: document.body})
        ansicht.getComponent(AdressSuche).vm.$emit('adresse', {beschriftung: '', strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau', breite: 52.56, laenge: 13.21})
        expect(ansicht.emitted('update:modelValue')?.[0]?.[0]).toMatchObject({adresse: {strasse: 'Werderstraße'}, koordinaten: [52.56, 13.21]})
        ansicht.unmount()
    })

    it('setzt den Punkt per Klick in die Karte', async () => {
        const ansicht = mount(OrtWahl, {props: {modelValue: leer}, global: {plugins: [i18n]}, attachTo: document.body})
        await ansicht.get('[role=region]').trigger('click', {clientX: 20, clientY: 20})
        const neu = ansicht.emitted('update:modelValue')?.[0]?.[0] as Ortsangabe
        expect(neu.koordinaten).toHaveLength(2)
        expect(neu.adresse).toEqual(leer.adresse)
        ansicht.unmount()
    })
})

describe('OrtWahl von Hand', () => {
    it('nimmt eine getippte Adresse in die Felder auf', async () => {
        const ansicht = mount(OrtWahl, {props: {modelValue: leer}, global: {plugins: [i18n]}, attachTo: document.body})
        const strasse = ansicht.findAll('input')[1]!
        await strasse.setValue('Werderstraße')
        expect(ansicht.emitted('update:modelValue')?.[0]?.[0]).toMatchObject({adresse: {strasse: 'Werderstraße'}})
        ansicht.unmount()
    })
})

describe('OrtWahl mit großer Karte', () => {
    it('vergrößert und verkleinert die Karte', async () => {
        const ansicht = mount(OrtWahl, {props: {modelValue: {adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: ''}, objekt: ''}}, global: {plugins: [i18n]}})
        const knopf = ansicht.findAll('button').find(b => b.text() === 'Karte vergrößern')!
        await knopf.trigger('click')
        expect(ansicht.find('.h-96').exists()).toBe(true)
        expect(knopf.text()).toBe('Karte verkleinern')
        ansicht.unmount()
    })
})

describe('OrtWahl mit Funkzelle', () => {
    it('nennt die Genauigkeit der Funkzelle in Kilometern', () => {
        const ohne = mount(OrtWahl, {props: {modelValue: leer}, global: {plugins: [i18n]}, attachTo: document.body})
        expect(ohne.text()).not.toContain('Funkzelle')
        ohne.unmount()
        const mit = mount(OrtWahl, {props: {modelValue: leer, funkzelle: {mitte: [52.5, 13.4], radius: 1200}}, global: {plugins: [i18n]}, attachTo: document.body})
        expect(mit.text()).toContain('Genauigkeit etwa 1,2 km')
        mit.unmount()
    })
})
