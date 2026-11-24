import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import type {Erzeugung} from '../modell/uebung'
import {testgraph} from '../modell/testgraph.test-hilfe'
import GeneratorPanel from './GeneratorPanel.vue'

vi.mock('../api/gebiete', () => ({ladeGebiete: vi.fn().mockResolvedValue({Neukölln: ['Britz', 'Neukölln']})}))

const ERZEUGUNG: Erzeugung = {gewichtRd: 80, gewichtBrand: 12, gewichtTh: 8, kategorie: '', protokoll: '', ortsteil: '', bezirk: '', anteilOrte: 30, anteilOhneAdresse: 5}

/**
 * Mounts the panel with an intent sender.
 *
 * @param absicht the intent sender
 * @returns the mounted panel
 */
function panel(absicht = vi.fn().mockResolvedValue({szenarioIds: ['a', 'b']})) {
    return {absicht, ansicht: mount(GeneratorPanel, {props: {erzeugung: ERZEUGUNG, autoGenerieren: true, absicht}, global: {plugins: [i18n]}})}
}

describe('GeneratorPanel', () => {
    it('generiert die gewünschte Anzahl und meldet sie', async () => {
        const {absicht, ansicht} = panel()
        await ansicht.get('input[max="20"]').setValue(2)
        await ansicht.findAll('button').find(b => b.text() === 'Generieren')!.trigger('click')
        await flushPromises()
        expect(absicht).toHaveBeenCalledWith('pool.generieren', {anzahl: 2})
        expect(ansicht.text()).toContain('2 Szenarien generiert.')
    })

    it('schickt geänderte Einstellungen und das Gebiet', async () => {
        const {absicht, ansicht} = panel()
        await ansicht.get('input[max="100"]').setValue(50)
        await ansicht.get('input[max="100"]').trigger('change')
        expect(absicht).toHaveBeenLastCalledWith('erzeugung.einstellen', {erzeugung: {...ERZEUGUNG, gewichtRd: 50}})
        await flushPromises()
        await ansicht.findAll('select').find(auswahl => auswahl.html().includes('o:Britz'))!.setValue('o:Britz')
        expect(absicht).toHaveBeenLastCalledWith('erzeugung.einstellen', {erzeugung: {...ERZEUGUNG, gewichtRd: 50, ortsteil: 'Britz'}})
    })

    it('behält Getipptes, wenn der Zustand ohne Änderung neu kommt', async () => {
        const {ansicht} = panel()
        const feld = () => ansicht.get('input[max="100"]').element as HTMLInputElement
        await ansicht.get('input[max="100"]').setValue(50)
        await ansicht.setProps({erzeugung: {...ERZEUGUNG}})
        expect(feld().value).toBe('50')
        await ansicht.setProps({erzeugung: {...ERZEUGUNG, gewichtRd: 60}})
        expect(feld().value).toBe('60')
    })

    it('schaltet die Auto-Generierung und zeigt Ablehnungen', async () => {
        const absicht = vi.fn().mockRejectedValue(new Error('Kein Code passt zu diesen Einstellungen.'))
        const {ansicht} = panel(absicht)
        await ansicht.get('input[type=checkbox]').setValue(false)
        expect(absicht).toHaveBeenCalledWith('engine.parameter', {parameter: {autoGenerieren: false}})
        await flushPromises()
        expect(ansicht.get('[role=alert]').text()).toBe('Kein Code passt zu diesen Einstellungen.')
    })
})

describe('GeneratorPanel mit Lagen', () => {
    it('bietet die Lagen je Fachrichtung an und schickt die gewählte ohne Kategorie', async () => {
        const absicht = vi.fn().mockResolvedValue({})
        const ansicht = mount(GeneratorPanel, {props: {erzeugung: {...ERZEUGUNG, kategorie: 'RD1'}, autoGenerieren: true, absicht, graph: testgraph()}, global: {plugins: [i18n]}})
        const auswahl = ansicht.findAll('select').find(s => s.html().includes('alle Lagen'))!
        expect(auswahl.findAll('optgroup').map(g => g.attributes('label'))).toEqual(['Med', 'Feuer'])
        expect(auswahl.text()).toContain('Sturz (3 Codes)')
        await auswahl.setValue('rd.17')
        expect(absicht).toHaveBeenLastCalledWith('erzeugung.einstellen', {erzeugung: {...ERZEUGUNG, kategorie: '', protokoll: 'rd.17'}})
    })
})
