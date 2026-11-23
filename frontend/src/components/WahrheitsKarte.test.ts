import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import {BIS_SITUATION} from '../modell/testgraph.test-hilfe'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import WahrheitsKarte from './WahrheitsKarte.vue'

describe('WahrheitsKarte', () => {
    it('zeigt die ganze Wahrheit von Anfang an und markiert die aktuelle Frage', () => {
        const anruf = anrufMit('a')
        anruf.eintraege.abfrage.pfad = BIS_SITUATION.slice(0, 2)
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('17D01')
        expect(ansicht.text()).toContain('Weint.')
        expect(ansicht.text()).toContain('erreichbar unter 030 12345678')
        expect(ansicht.text()).toContain('Werderstraße 20, 13587 Hakenfelde')
        expect(ansicht.findAll('ol li')).toHaveLength(5)
        expect(ansicht.get('[aria-current=step]').text()).toContain('Alter?')
        expect(ansicht.text()).toContain('noch nicht erfasst')
    })

    it('markiert Abweichungen der Einträge und des Pfads rot', () => {
        const anruf = anrufMit('a')
        anruf.eintraege.abfrage.pfad = [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]
        anruf.eintraege.anrufer = {name: 'Kaya', rufnummerBestaetigt: true, rueckrufnummer: '491761234567'}
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.get('ol li.text-fehler').text()).toContain('Trainee: Leicht')
        expect(ansicht.text()).toContain('Abzweigung')
        const nummer = ansicht.findAll('ul li').find(li => li.text().startsWith('Rückrufnummer'))!
        expect(nummer.classes()).toContain('text-fehler')
        expect(nummer.text()).toContain('richtig: 030 12345678')
        expect(ansicht.findAll('ul li').find(li => li.text().startsWith('Name'))!.classes()).toContain('text-ok')
    })
})
