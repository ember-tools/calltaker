import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {nextTick} from 'vue'
import {i18n} from '../i18n'
import {schwersteErreichbare} from '../modell/abfrageweg'
import type {Abfrageeintrag} from '../modell/eintraege'
import {eingrenzungsgraph} from '../modell/eingrenzung.test-hilfe'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import SnaFenster from './SnaFenster.vue'

const graph = testgraph()
const schwerste = schwersteErreichbare(graph)

/**
 * Mounts the window with a questioning that follows its own updates.
 *
 * @param abfrage the questioning to start from
 * @param gesperrt whether the location is still missing
 * @returns the mounted window
 */
function fenster(abfrage: Abfrageeintrag, gesperrt = false) {
    const ansicht = mount(SnaFenster, {
        props: {graph, schwerste, gesperrt, modelValue: abfrage, 'onUpdate:modelValue': (wert: Abfrageeintrag) => ansicht.setProps({modelValue: wert})},
        global: {plugins: [i18n]},
    })
    return ansicht
}

/**
 * The questioning the window holds now.
 *
 * @param ansicht the mounted window
 * @returns its questioning
 */
const stand = (ansicht: ReturnType<typeof fenster>) => ansicht.props('modelValue') as Abfrageeintrag

describe('SnaFenster', () => {
    it('beginnt erst, wenn der Einsatzort steht, oder auf Wunsch', async () => {
        const ansicht = fenster({pfad: []}, true)
        expect(ansicht.text()).toContain('Zuerst den Einsatzort festhalten.')
        await ansicht.findAll('button').find(b => b.text() === 'Abfrage trotzdem beginnen')!.trigger('click')
        expect(ansicht.text()).toContain('Grund?')
    })

    it('geht durch Auswahl, Weiche und Eingabe bis zum Code', async () => {
        const ansicht = fenster({pfad: []})
        await ansicht.findAll('button').find(b => b.text().includes('Med'))!.trigger('click')
        await ansicht.findAll('button').find(b => b.text().includes('1. Hand'))!.trigger('click')
        expect(ansicht.text()).toContain('Alter?')
        await ansicht.get('form input').setValue('81')
        await ansicht.get('form').trigger('submit')
        await ansicht.findAll('button').find(b => b.text().includes('Sturz'))!.trigger('click')
        expect(ansicht.text()).toContain('17E01')
        await ansicht.findAll('button').find(b => b.text().includes('Leicht'))!.trigger('click')
        expect(stand(ansicht).pfad.at(-1)).toEqual({knoten: 'p.k0', antwort: 'leicht'})
        expect(ansicht.text()).toContain('Abfrage abgeschlossen: 17A01 · RD4C.')
    })

    it('geht einen Schritt zurück', async () => {
        const ansicht = fenster({pfad: BIS_SITUATION})
        await ansicht.findAll('button').find(b => b.text() === 'Zurück')!.trigger('click')
        expect(stand(ansicht).pfad).toHaveLength(3)
    })

    it('bricht mit Begründung ab und behält das Zwischenergebnis als Code', async () => {
        const ansicht = fenster({pfad: BIS_SITUATION})
        await ansicht.findAll('button').find(b => b.text() === 'Abbruch mit Begründung')!.trigger('click')
        await ansicht.get('form input').setValue('Anrufer legt auf')
        await ansicht.get('form').trigger('submit')
        expect(stand(ansicht).abbruch).toEqual({grund: 'Anrufer legt auf', ergebnis: {knoten: 'p.e3', code: '17E01'}})
        expect(ansicht.emitted('sofort')).toBeTruthy()
    })

    it('wertet auf einen dringenderen Code auf', async () => {
        const ansicht = fenster({pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]})
        await ansicht.findAll('button').find(b => b.text() === 'Aufwertung')!.trigger('click')
        await ansicht.findAll('button').find(b => b.text().startsWith('17D01'))!.trigger('click')
        expect(stand(ansicht).aufwertung).toEqual({knoten: 'p.e2', code: '17D01'})
    })

    it('zeigt die Hinweise der Frage als Erste Hilfe', async () => {
        const ansicht = fenster({pfad: BIS_SITUATION})
        await ansicht.findAll('button').find(b => b.text() === 'Erste Hilfe')!.trigger('click')
        expect(ansicht.text()).toContain('Nicht bewegen lassen.')
    })
})

describe('SnaFenster mit der Tastatur', () => {
    it('lässt Frage um Frage mit Ziffern beantworten', async () => {
        const ansicht = mount(SnaFenster, {
            props: {graph, schwerste, gesperrt: false, modelValue: {pfad: []}, 'onUpdate:modelValue': (wert: Abfrageeintrag) => ansicht.setProps({modelValue: wert})},
            global: {plugins: [i18n]},
            attachTo: document.body,
        })
        ;(ansicht.vm as unknown as {fokussieren: () => void}).fokussieren()
        await (document.activeElement as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', {key: '0', bubbles: true}))
        await nextTick()
        await nextTick()
        document.activeElement!.dispatchEvent(new KeyboardEvent('keydown', {key: '0', bubbles: true}))
        await nextTick()
        await nextTick()
        expect((ansicht.props('modelValue') as Abfrageeintrag).pfad).toEqual([{knoten: 'fachrichtung', antwort: 'rd'}, {knoten: 'hand', antwort: 'eins'}])
        expect(document.activeElement?.tagName).toBe('INPUT')
        ansicht.unmount()
    })

    it('bietet den Abbruch erst an, wenn es ein Zwischenergebnis gibt', () => {
        const vorher = fenster({pfad: BIS_SITUATION.slice(0, 2)})
        expect(vorher.findAll('button').find(b => b.text() === 'Abbruch mit Begründung')!.attributes('disabled')).toBeDefined()
        const nachher = fenster({pfad: BIS_SITUATION})
        expect(nachher.findAll('button').find(b => b.text() === 'Abbruch mit Begründung')!.attributes('disabled')).toBeUndefined()
    })
})

describe('SnaFenster mit Eingrenzung', () => {
    it('ordnet die Beschwerden nach der Lage und beantwortet die Altersfrage selbst', async () => {
        const eng = eingrenzungsgraph()
        const ansicht = mount(SnaFenster, {
            props: {graph: eng, schwerste: schwersteErreichbare(eng), gesperrt: false, modelValue: {pfad: [{knoten: 'reaktion', antwort: 'nicht'}, {knoten: 'alter', wert: '81'}, {knoten: 'geschlecht', antwort: 'mann'}]}, 'onUpdate:modelValue': (wert: Abfrageeintrag) => ansicht.setProps({modelValue: wert})},
            global: {plugins: [i18n]},
        })
        const kacheln = ansicht.findAll('[data-antworten] button').map(b => b.text())
        expect(kacheln[0]).toContain('Bewusstlos')
        expect(ansicht.text()).toContain('Weitere Antworten (1)')
        await ansicht.findAll('button').find(b => b.text().includes('Krampf'))!.trigger('click')
        expect((ansicht.props('modelValue') as Abfrageeintrag).pfad.at(-1)).toEqual({knoten: 'altersfrage', antwort: 'erwachsen', automatisch: true})
        expect(ansicht.text()).toContain('(automatisch)')
        await ansicht.findAll('button').find(b => b.text() === 'Zurück')!.trigger('click')
        expect((ansicht.props('modelValue') as Abfrageeintrag).pfad).toHaveLength(3)
    })
})

describe('SnaFenster bei der Frage nach der Warntafel', () => {
    it('nimmt die Tafel auf und erlaubt „keine Tafel“', async () => {
        vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({herkunft: {}, stoffe: []})))))
        const mitTafel = testgraph()
        mitTafel.knoten['rd.wahl'] = {frage: 'Beschwerde?', antworten: [{id: 'sturz', label: 'Sturz', ziel: 'p.tafel', protokoll: 'rd.17', nr: '17'}]}
        mitTafel.knoten['p.tafel'] = {frage: 'Warntafel?', eingabe: {art: 'warntafel', vorlage: '{wert}', platzhalter: 'oben/unten', leer: {label: 'Keine Tafel', aussage: ''}}, ziel: 'p.k0'}
        const ansicht = mount(SnaFenster, {
            props: {graph: mitTafel, schwerste: schwersteErreichbare(mitTafel), gesperrt: false, modelValue: {pfad: BIS_SITUATION}, 'onUpdate:modelValue': (wert: Abfrageeintrag) => ansicht.setProps({modelValue: wert})},
            global: {plugins: [i18n]},
        })
        expect(ansicht.text()).toContain('Warntafel?')
        const weiter = () => ansicht.findAll('button').find(b => b.text() === 'Weiter')!
        expect(weiter().attributes('disabled')).toBeDefined()
        await ansicht.get('input[aria-label="Gefahrenzahl (oben)"]').setValue('33')
        await ansicht.get('input[aria-label="UN-Nummer (unten)"]').setValue('1203')
        await weiter().trigger('submit')
        expect((ansicht.props('modelValue') as Abfrageeintrag).pfad.at(-1)).toEqual({knoten: 'p.tafel', wert: '33/1203'})
        expect(ansicht.text()).toContain('Situation?')
        vi.unstubAllGlobals()
    })

    it('bietet Leitfragen neben den Kacheln an und blendet ausgeschlossene Kacheln ab', async () => {
        const mitLeitfragen = {...graph, leitfragen: [{knoten: 'p.k0', fragen: [{id: 'a', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['schwer-2']}, {label: 'Nein', behaelt: ['schwer-2']}]}]}]}
        const ansicht = mount(SnaFenster, {
            props: {graph: mitLeitfragen, schwerste, gesperrt: false, modelValue: {pfad: BIS_SITUATION}, leitfragen: [], 'onUpdate:leitfragen': (wert: unknown) => ansicht.setProps({leitfragen: wert as never})},
            global: {plugins: [i18n]},
        })
        expect(ansicht.get('aside').text()).toContain('Atmet die Person?')
        expect(ansicht.findAll('[data-antworten] .opacity-40')).toHaveLength(0)
        await ansicht.get('aside').findAll('button').find(b => b.text().startsWith('Ja'))!.trigger('click')
        expect(ansicht.emitted('sofort')).toBeTruthy()
        expect(ansicht.findAll('[data-antworten] .opacity-40')).toHaveLength(1)
        expect(ansicht.findAll('[data-antworten] .ring-3')).toHaveLength(2)
        expect(ansicht.findAll('[data-vorschlag]').map(b => b.text())).toEqual(['0Leicht', '1Schwer'])
        const ohne = mount(SnaFenster, {props: {graph, schwerste, gesperrt: false, modelValue: {pfad: BIS_SITUATION}}, global: {plugins: [i18n]}})
        expect(ohne.find('aside').exists()).toBe(false)
    })

    it('lässt Alt und Ziffer auf einer Kachel die Leitfrage beantworten, nicht die Kachel wählen', async () => {
        const mitLeitfragen = {...graph, leitfragen: [{knoten: 'p.k0', fragen: [{id: 'a', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['schwer-2']}, {label: 'Nein', behaelt: ['schwer-2']}]}]}]}
        const ansicht = mount(SnaFenster, {
            props: {graph: mitLeitfragen, schwerste, gesperrt: false, modelValue: {pfad: BIS_SITUATION}, leitfragen: [], 'onUpdate:leitfragen': (wert: unknown) => ansicht.setProps({leitfragen: wert as never}), 'onUpdate:modelValue': (wert: Abfrageeintrag) => ansicht.setProps({modelValue: wert})},
            global: {plugins: [i18n]},
            attachTo: document.body,
        })
        const kachel = ansicht.get('[data-antworten] button')
        ;(kachel.element as HTMLElement).focus()
        vi.useFakeTimers()
        kachel.element.dispatchEvent(new KeyboardEvent('keydown', {key: '1', code: 'Digit1', altKey: true, bubbles: true}))
        vi.advanceTimersByTime(700)
        vi.useRealTimers()
        await nextTick()
        expect(ansicht.props('modelValue')).toEqual({pfad: BIS_SITUATION})
        expect(ansicht.props('leitfragen')).toEqual([{knoten: 'p.k0', frage: 'a', antwort: 'Ja'}])
        expect(document.activeElement).toBe(kachel.element)
        ansicht.unmount()
    })

    it('legt den Fokus auch bei Leitfragen auf die erste Kachel', async () => {
        const mitLeitfragen = {...graph, leitfragen: [{knoten: 'p.k0', fragen: [{id: 'a', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['schwer-2']}, {label: 'Nein', behaelt: ['schwer-2']}]}]}]}
        const ansicht = mount(SnaFenster, {props: {graph: mitLeitfragen, schwerste, gesperrt: false, modelValue: {pfad: BIS_SITUATION}, leitfragen: []}, global: {plugins: [i18n]}, attachTo: document.body})
        ;(ansicht.vm as unknown as {fokussieren: () => void}).fokussieren()
        expect(document.activeElement).toBe(ansicht.get('[data-antworten] button').element)
        ansicht.unmount()
    })
})
