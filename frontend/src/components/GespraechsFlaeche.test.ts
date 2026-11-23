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
