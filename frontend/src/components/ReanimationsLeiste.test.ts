import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {nextTick, reactive} from 'vue'
import {i18n} from '../i18n'
import {leereEintraege} from '../modell/eintraege'
import {testgraph} from '../modell/testgraph.test-hilfe'
import ReanimationsLeiste from './ReanimationsLeiste.vue'

describe('ReanimationsLeiste', () => {
    const graph = testgraph()

    it('erscheint ohne Todeszeichen, bekommt den Fokus und startet den Takt', async () => {
        const eintraege = reactive(leereEintraege())
        const ansicht = mount(ReanimationsLeiste, {props: {graph, modelValue: eintraege}, global: {plugins: [i18n]}, attachTo: document.body})
        expect(ansicht.find('section').exists()).toBe(false)
        eintraege.abfrage = {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}
        await nextTick()
        await nextTick()
        expect(ansicht.text()).toContain('Telefonreanimation')
        expect(ansicht.text()).toContain('5 bis 6 Zentimeter')
        expect(document.activeElement?.textContent).toBe('Takt starten')
        await ansicht.get('button').trigger('click')
        expect(eintraege.reanimation.laeuft).toBe(true)
        expect(ansicht.emitted('sofort')).toBeTruthy()
        expect(ansicht.text()).toContain('1 Kompressionen')
        await ansicht.get('input[type=number]').setValue('130')
        expect(eintraege.reanimation.takt).toBe(120)
        await ansicht.get('input[type=number]').setValue('130')
        expect((ansicht.get('input[type=number]').element as HTMLInputElement).value).toBe('120')
        await ansicht.get('button').trigger('click')
        expect(eintraege.reanimation.laeuft).toBe(false)
        ansicht.unmount()
    })

    it('nimmt im Spiegel nicht den Fokus', async () => {
        const eintraege = reactive(leereEintraege())
        const ansicht = mount(ReanimationsLeiste, {props: {graph, modelValue: eintraege, ruhig: true}, global: {plugins: [i18n]}, attachTo: document.body})
        eintraege.abfrage = {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}
        await nextTick()
        await nextTick()
        expect(ansicht.find('section').exists()).toBe(true)
        expect(document.activeElement).toBe(document.body)
        ansicht.unmount()
    })
})

describe('ReanimationsLeiste nach dem Zurückgehen', () => {
    it('hält den Takt an, wenn die Reanimation nicht mehr fällig ist', async () => {
        const eintraege = reactive({...leereEintraege(), abfrage: {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}, reanimation: {laeuft: true, takt: 100}})
        const ansicht = mount(ReanimationsLeiste, {props: {graph: testgraph(), modelValue: eintraege}, global: {plugins: [i18n]}})
        eintraege.abfrage = {pfad: []}
        await nextTick()
        await nextTick()
        expect(eintraege.reanimation.laeuft).toBe(false)
        ansicht.unmount()
    })
})

describe('ReanimationsLeiste bis zum Eintreffen', () => {
    it('sagt, ob die Kräfte noch unterwegs oder schon da sind', async () => {
        const eintraege = reactive({...leereEintraege(), abfrage: {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}, zeiten: {reanimation: Date.now() / 1000}})
        const ansicht = mount(ReanimationsLeiste, {props: {graph: testgraph(), modelValue: eintraege, ruhig: true, eintreffenUm: Date.now() / 1000 + 60}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Kräfte unterwegs')
        await ansicht.setProps({eintreffenUm: Date.now() / 1000 - 1})
        expect(ansicht.text()).toContain('Kräfte vor Ort')
        ansicht.unmount()
    })

    it('zeigt die Schritte der Altersgruppe und lässt sie umschalten', async () => {
        const graph = testgraph()
        const eintraege = reactive(leereEintraege())
        eintraege.abfrage = {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}
        const ansicht = mount(ReanimationsLeiste, {props: {graph, modelValue: eintraege, ruhig: true}, global: {plugins: [i18n]}})
        await nextTick()
        expect(ansicht.text()).toContain('Schritte für: Erwachsener')
        expect(ansicht.text()).toContain('Alter unbekannt')
        expect(ansicht.text()).toContain('Entwurf nach den ERC-Leitlinien 2021')
        const knopf = (name: string) => ansicht.findAll('[role=group] button').find(b => b.text() === name)!
        await knopf('Säugling').trigger('click')
        expect(eintraege.reanimation.gruppe).toBe('saeugling')
        expect(knopf('Säugling').attributes('aria-pressed')).toBe('true')
        expect(ansicht.text()).toContain('zwei Finger')
        expect(ansicht.text()).not.toContain('Alter unbekannt')
        await knopf('Neugeborenes').trigger('click')
        expect(ansicht.text()).toContain('dreimal drücken, einmal beatmen')
        expect(ansicht.text()).toContain('3 : 1')
        expect(ansicht.find('input[type=number]').exists()).toBe(false)
    })

    it('nennt das Alter, aus dem es die Gruppe nimmt', async () => {
        const graph = testgraph()
        const eintraege = reactive(leereEintraege())
        eintraege.abfrage = {pfad: [{knoten: 'rd.alter', wert: '8 Monate'}, {knoten: 'rd.09.todeszeichen', antwort: 'keine'}]}
        const ansicht = mount(ReanimationsLeiste, {props: {graph, modelValue: eintraege, ruhig: true}, global: {plugins: [i18n]}})
        await nextTick()
        expect(ansicht.text()).toContain('Schritte für: Säugling, 8 Monate')
        expect(ansicht.text()).toContain('etwa 4 Zentimeter')
    })
})
