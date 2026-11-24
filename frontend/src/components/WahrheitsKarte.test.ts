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
        expect(ansicht.text()).toContain('Auf „Wo ist der Notfallort?“ nennst du: Werderstraße 20')
        expect(ansicht.text()).toContain('Deinen Namen (Mehmet Kaya) nennst du erst, wenn danach gefragt wird.')
        expect(ansicht.get('[aria-label="So sprichst du als Anrufer"] [role=status]').text()).toContain('Jetzt gefragt:')
        const beendet = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf: anrufMit('b', 'beendet')}, global: {plugins: [i18n]}})
        expect(beendet.text()).not.toContain('So sprichst du als Anrufer')
    })

    it('nennt die Antwort des Anrufers auf die offene Leitfrage aus der Lösung', () => {
        const graph = {...GRAPH, leitfragen: [{knoten: 'p.k0', fragen: [{id: 'a', frage: 'Atmet die Person?', antworten: [{label: 'Ja', nimmt: ['schwer-2']}, {label: 'Nein', behaelt: ['schwer-2']}, {label: 'Weiß nicht'}]}]}]}
        const anruf = anrufMit('l')
        anruf.eintraege.abfrage.pfad = BIS_SITUATION
        anruf.szenario = {...anruf.szenario, antworten: {...anruf.szenario.antworten, 'p.k0': {antwort: 'schwer-2'}}}
        const ansicht = mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Leitfrage: Atmet die Person? Nein')
        anruf.szenario = {...anruf.szenario, antworten: {...anruf.szenario.antworten, 'p.k0': {antwort: 'leicht'}}}
        const anders = mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}})
        expect(anders.text()).toContain('Leitfrage: Atmet die Person? Ja')
        anruf.szenario = {...anruf.szenario, antworten: {...anruf.szenario.antworten, 'p.k0': {}}}
        expect(mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}}).text()).toContain('Leitfrage: Atmet die Person? frei antworten, passend zur Lage')
        anruf.eintraege.leitfragen = [{knoten: 'p.k0', frage: 'a', antwort: 'Ja'}]
        expect(mount(WahrheitsKarte, {props: {graph, anruf}, global: {plugins: [i18n]}}).text()).not.toContain('Leitfrage:')
        anruf.eintraege.leitfragen = []
        expect(mount(WahrheitsKarte, {props: {graph, anruf: {...anruf, zustand: 'beendet'}}, global: {plugins: [i18n]}}).text()).not.toContain('Leitfrage:')
    })

    it('zeigt Notizen und Beschwerden im Leitfaden, nach dem Anruf darunter', () => {
        const laufend = anrufMit('n')
        laufend.szenario.rolle = {...laufend.szenario.rolle, beschwerden: ['Der Mundwinkel hängt.', 'Sie redet verwaschen.']}
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf: laufend}, global: {plugins: [i18n]}})
        const leitfaden = ansicht.get('[aria-label="So sprichst du als Anrufer"]')
        expect(leitfaden.text()).toContain('Was du weißt: Weint.')
        expect(leitfaden.findAll('li').filter(li => li.text().startsWith('Wenn gefragt:'))).toHaveLength(2)
        const vorbei = anrufMit('n', 'beendet')
        vorbei.szenario.rolle = {...vorbei.szenario.rolle, beschwerden: ['Der Mundwinkel hängt.']}
        const danach = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf: vorbei}, global: {plugins: [i18n]}})
        expect(danach.text()).toContain('Weint.')
        expect(danach.get('[aria-label="Beschwerden, die der Anrufer beschreiben sollte"]').text()).toBe('Der Mundwinkel hängt.')
    })
})

describe('WahrheitsKarte bei laufender Reanimation', () => {
    it('zeigt die Anfahrt und lässt die Kräfte vorzeitig eintreffen', async () => {
        const anruf = {...anrufMit('k'), eintreffenUm: Date.now() / 1000 + 90}
        const ansicht = mount(WahrheitsKarte, {props: {graph: GRAPH, anruf}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toMatch(/Kräfte treffen in 1:(29|30) ein/)
        await ansicht.findAll('button').find(b => b.text() === 'Jetzt eintreffen lassen')!.trigger('click')
        expect(ansicht.emitted('eintreffen')).toHaveLength(1)
        await ansicht.setProps({anruf: {...anruf, eintreffenUm: Date.now() / 1000 - 1}})
        expect(ansicht.text()).toContain('Kräfte sind eingetroffen')
    })
})
