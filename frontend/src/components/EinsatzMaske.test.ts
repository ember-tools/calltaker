import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import {leereEintraege, type Eintraege} from '../modell/eintraege'
import type {AnrufSicht} from '../modell/uebung'
import EinsatzMaske from './EinsatzMaske.vue'

vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))

const anruf: AnrufSicht = {id: 'a', zustand: 'gespraech', klingeltSeit: 0, rufnummer: '493068532207', rufnummerUnterdrueckt: false}

/**
 * Mounts the form for a call.
 *
 * @param fuer the call
 * @returns the mounted form and its entries
 */
function maske(fuer: AnrufSicht = anruf) {
    const eintraege: Eintraege = leereEintraege()
    const ansicht = mount(EinsatzMaske, {props: {anruf: fuer, modelValue: eintraege}, global: {plugins: [i18n]}, attachTo: document.body})
    return {ansicht, eintraege}
}

describe('EinsatzMaske', () => {
    it('zeigt die Nummer und bestätigt sie mit einem Klick', async () => {
        const {ansicht, eintraege} = maske()
        expect(ansicht.html()).toContain('030 68532207')
        await ansicht.findAll('button').find(b => b.text() === 'Nummer bestätigt')!.trigger('click')
        expect(eintraege.anrufer.rufnummerBestaetigt).toBe(true)
        expect(ansicht.emitted('sofort')).toBeTruthy()
        ansicht.unmount()
    })

    it('fragt bei unterdrückter Nummer gleich nach der Rückrufnummer', () => {
        const {ansicht} = maske({...anruf, rufnummer: undefined, rufnummerUnterdrueckt: true})
        expect(ansicht.text()).not.toContain('Nummer bestätigt')
        expect(ansicht.text()).toContain('Rückrufnummer')
        ansicht.unmount()
    })

    it('trägt Name und Hinweise ein', async () => {
        const {ansicht, eintraege} = maske()
        const felder = ansicht.findAll('input')
        await felder[0]!.setValue('Ayşe Yılmaz')
        await ansicht.get('textarea').setValue('Tür offen')
        expect(eintraege.anrufer.name).toBe('Ayşe Yılmaz')
        expect(eintraege.hinweise).toBe('Tür offen')
        ansicht.unmount()
    })
})

describe('EinsatzMaske bei der Rückrufnummer', () => {
    it('übernimmt beim Bestätigen die angezeigte Nummer und nimmt es bei einer anderen zurück', async () => {
        const {ansicht, eintraege} = maske()
        await ansicht.findAll('button').find(b => b.text() === 'Nummer bestätigt')!.trigger('click')
        expect(ansicht.props('modelValue').anrufer).toMatchObject({rufnummerBestaetigt: true, rueckrufnummer: '493068532207'})
        await ansicht.findAll('button').find(b => b.text() === 'Andere Rückrufnummer')!.trigger('click')
        expect(ansicht.props('modelValue').anrufer).toMatchObject({rufnummerBestaetigt: false, rueckrufnummer: ''})
        expect(eintraege).toBeDefined()
        ansicht.unmount()
    })

    it('setzt den Fokus beim Annehmen in die Adresssuche', () => {
        const {ansicht} = maske()
        expect(document.activeElement?.getAttribute('role')).toBe('combobox')
        ansicht.unmount()
    })
})
