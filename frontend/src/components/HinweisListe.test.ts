import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {reactive} from 'vue'
import {i18n} from '../i18n'
import {leereEintraege} from '../modell/eintraege'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import HinweisListe from './HinweisListe.vue'

const graph = {...testgraph(), anleitungen: [
    {id: 'zugang', titel: 'Tür öffnen', saetze: ['Öffnen Sie die Haustür.', 'Licht an.'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'},
]}

describe('HinweisListe', () => {
    it('zeigt fällige Hinweise zum Vorlesen und hakt sie ab', async () => {
        const eintraege = reactive({...leereEintraege(), abfrage: {pfad: BIS_SITUATION}})
        const ansicht = mount(HinweisListe, {props: {graph, modelValue: eintraege}, global: {plugins: [i18n]}, attachTo: document.body})
        expect(ansicht.text()).toContain('Öffnen Sie die Haustür.')
        expect(ansicht.text()).toContain('Pflicht')
        ;(ansicht.vm as unknown as {fokussieren: () => void}).fokussieren()
        expect(document.activeElement?.getAttribute('type')).toBe('checkbox')
        await ansicht.get('input[type=checkbox]').setValue(true)
        expect(eintraege.anleitung.gegeben).toEqual(['zugang'])
        expect(ansicht.emitted('sofort')).toBeTruthy()
        expect(ansicht.text()).not.toContain('Öffnen Sie die Haustür.')
        ansicht.unmount()
    })

    it('zeigt nichts, solange kein Hinweis fällig ist', () => {
        const ansicht = mount(HinweisListe, {props: {graph, modelValue: leereEintraege()}, global: {plugins: [i18n]}})
        expect(ansicht.find('section').exists()).toBe(false)
    })
})

describe('HinweisListe nach dem Zurückgehen', () => {
    it('zeigt Haken, die nicht mehr fällig sind, und lässt sie zurücknehmen', async () => {
        const eintraege = reactive({...leereEintraege(), anleitung: {gegeben: ['zugang']}})
        const ansicht = mount(HinweisListe, {props: {graph, modelValue: eintraege}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Gegeben, aber nicht mehr fällig (1)')
        await ansicht.get('details input[type=checkbox]').setValue(false)
        expect(eintraege.anleitung.gegeben).toEqual([])
    })
})
