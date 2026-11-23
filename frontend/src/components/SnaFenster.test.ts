import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
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
