import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import {anrufMit, zustandMit} from '../modell/ausbilder.test-hilfe'
import AusbilderSchlange from './AusbilderSchlange.vue'

describe('AusbilderSchlange', () => {
    it('pausiert, lässt auflegen und ein Szenario sofort klingeln', async () => {
        const absicht = vi.fn().mockResolvedValue({})
        const ansicht = mount(AusbilderSchlange, {props: {zustand: zustandMit([anrufMit('g'), anrufMit('w', 'wartet')]), absicht}, global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Im Gespräch: Sturz g')
        await ansicht.findAll('button').find(b => b.text() === 'Pausieren')!.trigger('click')
        expect(absicht).toHaveBeenCalledWith('engine.pausieren', {an: true})
        await ansicht.findAll('button').find(b => b.text() === 'Auflegen lassen')!.trigger('click')
        expect(absicht).toHaveBeenCalledWith('anruf.auflegen', {anrufId: 'w'})
        await ansicht.get('select').setValue('sp')
        await ansicht.findAll('button').find(b => b.text() === 'Klingeln')!.trigger('click')
        expect(absicht).toHaveBeenCalledWith('engine.sofort', {szenarioId: 'sp'})
    })

    it('setzt fort, behält die Wahl bei einer Ablehnung und zeigt den Grund', async () => {
        const absicht = vi.fn().mockRejectedValue(new Error('Die Warteschlange ist voll.'))
        const zustand = zustandMit([])
        zustand.engine = {...zustand.engine, pausiert: true, manuellPausiert: true}
        const ansicht = mount(AusbilderSchlange, {props: {zustand, absicht}, global: {plugins: [i18n]}})
        await ansicht.findAll('button').find(b => b.text() === 'Fortsetzen')!.trigger('click')
        expect(absicht).toHaveBeenCalledWith('engine.pausieren', {an: false})
        await ansicht.get('select').setValue('sp')
        await ansicht.findAll('button').find(b => b.text() === 'Klingeln')!.trigger('click')
        await new Promise(r => setTimeout(r, 0))
        expect(ansicht.get('[role=alert]').text()).toBe('Die Warteschlange ist voll.')
        expect((ansicht.get('select').element as HTMLSelectElement).value).toBe('sp')
    })
})
