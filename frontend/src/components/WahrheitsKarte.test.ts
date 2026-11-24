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

describe('WahrheitsKarte mit Hinweisen', () => {
    it('lässt den Ausbilder korrigieren, ob ein Hinweis gegeben wurde', async () => {
        const graph = {...GRAPH, anleitungen: [{id: 'zugang', titel: 'Tür öffnen', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'}]}
        const anruf = anrufMit('a')
        const ansicht = mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}})
        const zeile = ansicht.findAll('ul li').find(li => li.text().startsWith('Tür öffnen'))!
        expect(zeile.text()).toContain('noch nicht erfasst')
        await zeile.get('button').trigger('click')
        expect(ansicht.emitted('korrigieren')?.[0]).toEqual(['zugang', true])
        await ansicht.setProps({anruf: {...anruf, korrektur: {zugang: true}}})
        expect(ansicht.findAll('ul li').find(li => li.text().startsWith('Tür öffnen'))!.text()).toContain('als nicht gegeben werten')
    })
})

describe('WahrheitsKarte bei einem unpassenden Hinweis', () => {
    it('nimmt einen falsch gegebenen Hinweis zurück und lässt die Korrektur rückgängig machen', async () => {
        const graph = {...GRAPH, anleitungen: [
            {id: 'bleiben', titel: 'Bleiben', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], schliesstAus: ['gehen'], quelle: 'Q'},
            {id: 'gehen', titel: 'Gehen', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'brand' as const}], quelle: 'Q'},
        ]}
        const anruf = anrufMit('a')
        anruf.eintraege.anleitung = {gegeben: ['gehen']}
        const ansicht = mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}})
        const zeile = () => ansicht.findAll('ul li').find(li => li.text().startsWith('Gehen'))!
        expect(zeile().classes()).toContain('font-semibold')
        await zeile().get('button').trigger('click')
        expect(ansicht.emitted('korrigieren')?.[0]).toEqual(['gehen', false])
        await ansicht.setProps({anruf: {...anruf, korrektur: {gehen: false}}})
        expect(zeile().text()).toContain('als gegeben werten')
        await zeile().get('button').trigger('click')
        expect(ansicht.emitted('korrigieren')?.[1]).toEqual(['gehen', true])
    })
})

describe('WahrheitsKarte zur Übergabe', () => {
    it('zeigt, wann übergeben wurde und was nachgetragen ist', () => {
        const anruf = anrufMit('a')
        const {ort, anrufer, betroffener, abfrage, hinweise} = structuredClone(anruf.eintraege)
        anruf.angenommenUm = 100
        anruf.eintraege = {...anruf.eintraege, uebergabe: true, uebergeben: {ort, anrufer, betroffener, abfrage, hinweise}, hinweise: 'neu', zeiten: {uebergabe: 165}}
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Übergeben nach 1:05')
        expect(ansicht.text()).toContain('Nachgetragen: Hinweise')
    })
})

describe('WahrheitsKarte als Sprechhilfe', () => {
    it('zeigt den Leitfaden und die gerade gestellte Frage, solange das Gespräch läuft', () => {
        const anruf = anrufMit('s')
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('So sprichst du als Anrufer')
        expect(ansicht.text()).toContain('„Hallo, hier ist Mehmet Kaya.“')
        expect(ansicht.get('[aria-label="So sprichst du als Anrufer"] [role=status]').text()).toContain('Jetzt gefragt:')
        const beendet = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf: anrufMit('b', 'beendet')}, global: {plugins: [i18n]}})
        expect(beendet.text()).not.toContain('So sprichst du als Anrufer')
    })
})
