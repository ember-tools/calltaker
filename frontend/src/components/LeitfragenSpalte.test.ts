import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {computed, defineComponent, h, nextTick, ref} from 'vue'
import {i18n} from '../i18n'
import type {Antwort} from '../modell/abfragegraph'
import type {Leitfrageneintrag} from '../modell/eintraege'
import {leitstand, type Knotenleitfragen} from '../modell/leitfragen'
import LeitfragenSpalte from './LeitfragenSpalte.vue'

const ANTWORTEN: Antwort[] = [{id: 'leicht', label: 'Leicht', ziel: 'a'}, {id: 'schwer', label: 'Schwer', ziel: 'b'}, {id: 'rea', label: 'Reanimation', ziel: 'c'}]
const EINTRAG: Knotenleitfragen = {
    knoten: 'p.k0',
    fragen: [
        {id: 'strom', frage: 'Strom im Spiel?', sicherheit: true, hinweis: 'Nicht ins Wasser treten.', antworten: [{label: 'Ja'}, {label: 'Nein'}]},
        {id: 'atmet', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['rea']}, {label: 'Nein', behaelt: ['rea']}]},
        {id: 'blut', frage: 'Blutet es stark?', antworten: [{label: 'Ja', behaelt: ['schwer']}, {label: 'Nein', behaelt: ['leicht']}]},
    ],
}

/**
 * Mounts the column the way the questioning window does: the state is worked out from the
 * answers, which follow the column's own updates.
 *
 * @param anfang the answers given so far
 * @param ruhig whether it is the trainer's mirror
 * @returns the mounted holder, its answers, and what it emitted
 */
function spalte(anfang: Leitfrageneintrag[] = [], ruhig = false) {
    const gegeben = ref<Leitfrageneintrag[]>(anfang)
    const gewaehlt: string[] = []
    let sofort = 0
    const halter = defineComponent(() => {
        const stand = computed(() => leitstand(EINTRAG, ANTWORTEN.map(a => a.id), gegeben.value))
        return () => h(LeitfragenSpalte, {
            eintrag: EINTRAG, antworten: ANTWORTEN, stand: stand.value, ruhig, modelValue: gegeben.value,
            'onUpdate:modelValue': (wert: Leitfrageneintrag[]) => { gegeben.value = wert },
            onSofort: () => { sofort++ },
            onWaehlen: (id: string) => { gewaehlt.push(id) },
        })
    })
    const ansicht = mount(halter, {global: {plugins: [i18n]}, attachTo: document.body})
    return {ansicht, gegeben, gewaehlt, sofort: () => sofort}
}

const knopf = (ansicht: ReturnType<typeof spalte>['ansicht'], text: string) => ansicht.findAll('button').find(b => b.text().startsWith(text))!

describe('LeitfragenSpalte', () => {
    it('stellt die Sicherheitsfrage zuerst und rot, dann die übrigen bis zum Vorschlag', async () => {
        const {ansicht, gegeben, gewaehlt, sofort} = spalte([{knoten: 'anderswo', frage: 'x', antwort: 'Ja'}])
        expect(ansicht.get('[role=status]').text()).toBe('Strom im Spiel?')
        expect(ansicht.get('[role=img]').attributes('aria-label')).toBe('Sicherheitsfrage')
        expect(ansicht.text()).toContain('Nicht ins Wasser treten.')
        expect(knopf(ansicht, 'Nein').attributes('aria-keyshortcuts')).toBe('Alt+2')
        await knopf(ansicht, 'Nein').trigger('click')
        expect(ansicht.get('[role=status]').text()).toBe('Atmet die Person?')
        await knopf(ansicht, 'Ja').trigger('click')
        await knopf(ansicht, 'Ja').trigger('click')
        await nextTick()
        expect(ansicht.get('[role=status]').text()).toBe('Vorschlag: eine dieser Kacheln')
        expect(document.activeElement?.textContent).toContain('Schwer')
        await ansicht.get('[data-vorschlag]').trigger('click')
        expect(gewaehlt).toEqual(['schwer'])
        expect(gegeben.value).toEqual([
            {knoten: 'anderswo', frage: 'x', antwort: 'Ja'},
            {knoten: 'p.k0', frage: 'strom', antwort: 'Nein'},
            {knoten: 'p.k0', frage: 'atmet', antwort: 'Ja'},
            {knoten: 'p.k0', frage: 'blut', antwort: 'Ja'},
        ])
        expect(sofort()).toBe(3)
        ansicht.unmount()
    })

    it('rückt den Fokus auf die nächste Frage vor', async () => {
        const {ansicht} = spalte()
        await knopf(ansicht, 'Nein').trigger('click')
        await nextTick()
        expect(document.activeElement?.getAttribute('aria-keyshortcuts')).toBe('Alt+1')
        expect(document.activeElement?.textContent).toContain('Ja')
        ansicht.unmount()
    })

    it('lässt eine frühere Antwort ändern und neu beginnen', async () => {
        const {ansicht, gegeben} = spalte([{knoten: 'p.k0', frage: 'strom', antwort: 'Nein'}, {knoten: 'p.k0', frage: 'atmet', antwort: 'Ja'}])
        expect(ansicht.get('[role=status]').text()).toBe('Blutet es stark?')
        await ansicht.get('button[aria-label="Antwort auf „Atmet die Person?“ ändern"]').trigger('click')
        expect(gegeben.value).toEqual([{knoten: 'p.k0', frage: 'strom', antwort: 'Nein'}])
        await knopf(ansicht, 'Neu beginnen').trigger('click')
        expect(gegeben.value).toEqual([])
        ansicht.unmount()
    })

    it('antwortet mit Alt und Ziffer, aber nicht in Textfeldern, mit AltGr, wiederholt oder im Spiegel', async () => {
        const {ansicht, gegeben} = spalte()
        const feld = document.createElement('input')
        document.body.append(feld)
        feld.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit2', altKey: true, bubbles: true}))
        window.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit2', altKey: true, ctrlKey: true}))
        window.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit2', altKey: true, repeat: true}))
        window.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit2'}))
        expect(gegeben.value).toEqual([])
        window.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit2', altKey: true}))
        await nextTick()
        expect(gegeben.value).toEqual([{knoten: 'p.k0', frage: 'strom', antwort: 'Nein'}])
        feld.remove()
        ansicht.unmount()
        const spiegel = spalte([], true)
        window.dispatchEvent(new KeyboardEvent('keydown', {code: 'Digit1', altKey: true}))
        expect(spiegel.gegeben.value).toEqual([])
        spiegel.ansicht.unmount()
    })
})
