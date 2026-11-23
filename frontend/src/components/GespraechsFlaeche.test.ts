import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {ref} from 'vue'
import {i18n} from '../i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Ergebnis} from '../modell/abfrageweg'
import {leereEintraege, type Eintraege} from '../modell/eintraege'
import {testgraph} from '../modell/testgraph.test-hilfe'
import GespraechsFlaeche from './GespraechsFlaeche.vue'

function mitTodeszeichen(): Abfragegraph {
    const graph = testgraph()
    graph.knoten['hand'] = {frage: 'Hand?', antworten: [{id: 'eins', label: '1. Hand', ziel: 'rd.09.todeszeichen'}]}
    graph.knoten['rd.09.todeszeichen'] = {frage: 'Todeszeichen?', antworten: [{id: 'keine', label: 'Keine', ziel: 'rd.alter'}]}
    return graph
}

describe('GespraechsFlaeche', () => {
    it('gibt der Reanimation den Fokus vor der nächsten Frage', async () => {
        const eintraege = ref<Eintraege>({...leereEintraege(), ort: {...leereEintraege().ort, koordinaten: [52.5, 13.4] as [number, number]}, abfrage: {pfad: [{knoten: 'fachrichtung', antwort: 'rd'}, {knoten: 'hand', antwort: 'eins'}]}})
        const ansicht = mount(GespraechsFlaeche, {
            props: {graph: mitTodeszeichen(), schwerste: new Map<string, Ergebnis>(), anruf: {id: 'a', zustand: 'gespraech', klingeltSeit: 0, rufnummerUnterdrueckt: false}, 'modelValue': eintraege.value, 'onUpdate:modelValue': (neu: Eintraege) => { eintraege.value = neu }},
            global: {plugins: [i18n], stubs: {OrtWahl: true}},
            attachTo: document.body,
        })
        const kachel = ansicht.findAll('[data-antworten] button').find(b => b.text().includes('Keine'))!
        await kachel.trigger('click')
        await flushPromises()
        expect(ansicht.text()).toContain('Alter?')
        expect(document.activeElement?.textContent).toBe('Takt starten')
        ansicht.unmount()
    })
})

describe('GespraechsFlaeche bei der Übergabe', () => {
    it('übergibt per Knopf und markiert danach Nachträge', async () => {
        const start = leereEintraege()
        const eintraege = ref<Eintraege>({...start, ort: {...start.ort, koordinaten: [52.5, 13.4]}, abfrage: {pfad: [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]}})
        const ansicht = mount(GespraechsFlaeche, {
            props: {graph: testgraph(), schwerste: new Map<string, Ergebnis>(), anruf: {id: 'a', zustand: 'gespraech', klingeltSeit: 0, rufnummerUnterdrueckt: false}, 'modelValue': eintraege.value, 'onUpdate:modelValue': (neu: Eintraege) => { eintraege.value = neu }},
            global: {plugins: [i18n], stubs: {OrtWahl: true}},
        })
        expect(ansicht.text()).toContain('Übergabe jetzt fällig')
        const knopf = ansicht.findAll('button').find(b => b.text().includes('An Disposition übergeben'))!
        await knopf.trigger('click')
        expect(eintraege.value.uebergabe).toBe(true)
        expect(ansicht.emitted('sofort')).toBeTruthy()
        const {ort, anrufer, betroffener, abfrage, hinweise} = JSON.parse(JSON.stringify(eintraege.value)) as Eintraege
        await ansicht.setProps({modelValue: {...eintraege.value, uebergeben: {ort, anrufer, betroffener, abfrage, hinweise}, hinweise: 'später', zeiten: {uebergabe: 5}}})
        expect(ansicht.text()).toContain('Nachtrag')
        expect(ansicht.text()).not.toContain('Übergabe jetzt fällig')
    })
})

describe('GespraechsFlaeche ohne Übergabebereitschaft', () => {
    it('übergibt weder ohne Punkt noch ein zweites Mal', async () => {
        const eintraege = ref<Eintraege>({...leereEintraege(), abfrage: {pfad: [{knoten: 'fachrichtung', antwort: 'fw'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'fw.grund', antwort: 'brand'}]}})
        const ansicht = mount(GespraechsFlaeche, {
            props: {graph: testgraph(), schwerste: new Map<string, Ergebnis>(), anruf: {id: 'a', zustand: 'gespraech', klingeltSeit: 0, rufnummerUnterdrueckt: false}, 'modelValue': eintraege.value, 'onUpdate:modelValue': (neu: Eintraege) => { eintraege.value = neu }},
            global: {plugins: [i18n], stubs: {OrtWahl: true}},
        })
        const flaeche = ansicht.vm as unknown as {uebergeben: () => void}
        flaeche.uebergeben()
        expect(eintraege.value.uebergabe).toBeFalsy()
        expect(ansicht.emitted('sofort')).toBeFalsy()
        eintraege.value.ort.koordinaten = [52.5, 13.4]
        eintraege.value.uebergabe = true
        await ansicht.setProps({modelValue: eintraege.value})
        flaeche.uebergeben()
        expect(ansicht.emitted('sofort')).toBeFalsy()
        ansicht.unmount()
    })
})
