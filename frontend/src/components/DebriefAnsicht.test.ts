import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import {BIS_SITUATION} from '../modell/testgraph.test-hilfe'
import {sichtVon} from '../modell/uebung'
import DebriefAnsicht from './DebriefAnsicht.vue'

describe('DebriefAnsicht', () => {
    it('zeigt Feld für Feld Erfasstes neben der Wahrheit, Zeiten, Fehlendes und die Abzweigung', () => {
        const anruf = anrufMit('a', 'beendet')
        anruf.eintraege.ort = {...anruf.eintraege.ort, adresse: {...anruf.szenario.ort.adresse}, koordinaten: [52.5663, 13.2122], geschoss: '3. OG'}
        anruf.eintraege.anrufer = {name: 'Mehmet Kaya', rufnummerBestaetigt: true, rueckrufnummer: '491761234567'}
        anruf.eintraege.abfrage = {pfad: [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]}
        anruf.eintraege.zeiten = {adresse: 1045, code: 1080}
        const ansicht = mount(DebriefAnsicht, {props: {graph: GRAPH, anruf: sichtVon(anruf), szenario: anruf.szenario}, global: {plugins: [i18n]}})
        const zeile = (feld: string) => ansicht.findAll('tbody tr').find(tr => tr.get('th').text() === feld)!
        expect(zeile('Adresse').text()).toContain('richtig')
        expect(zeile('Punkt').text()).toContain('0 m vom richtigen Punkt')
        expect(zeile('Geschoss').text()).toContain('falsch')
        expect(zeile('Code').text()).toContain('nah dran (gleiches Protokoll)')
        expect(zeile('Rückrufnummer').classes()).toContain('text-error')
        expect(ansicht.text()).toContain('Klingeln bis Annahme0:30')
        expect(ansicht.text()).toContain('Annahme bis Code0:50')
        expect(ansicht.text()).toContain('Abzweigung')
        expect(ansicht.text()).not.toContain('Beim Beenden fehlte')
    })
})

describe('DebriefAnsicht ohne fällige Hinweise', () => {
    it('zeigt keine leere Phase Anleitung', () => {
        const anruf = anrufMit('a', 'beendet')
        const ansicht = mount(DebriefAnsicht, {props: {graph: GRAPH, anruf: sichtVon(anruf), szenario: anruf.szenario}, global: {plugins: [i18n]}})
        expect(ansicht.find('section[aria-label="Anleitung"]').exists()).toBe(false)
        expect(ansicht.find('section[aria-label="Standort"]').exists()).toBe(true)
    })
})
