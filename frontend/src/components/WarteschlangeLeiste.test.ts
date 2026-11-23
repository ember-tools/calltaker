import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import type {TraineeZustand} from '../modell/uebung'
import WarteschlangeLeiste from './WarteschlangeLeiste.vue'

const anruf = (id: string, seit: number) => ({id, zustand: 'wartet' as const, klingeltSeit: seit, rufnummer: '491761234567', rufnummerUnterdrueckt: false})

/**
 * Mounts the bar for a state.
 *
 * @param zustand the trainee's state
 * @returns the mounted bar
 */
const leiste = (zustand: TraineeZustand) => mount(WarteschlangeLeiste, {props: {zustand}, global: {plugins: [i18n]}})

describe('WarteschlangeLeiste', () => {
    it('bietet vor dem Start nur Bereit an', async () => {
        const ansicht = leiste({verbunden: {ausbilder: true, trainee: true}, engine: {gestartet: false, pausiert: false, automatischPausiert: false}, anrufe: []})
        await ansicht.findAll('button').find(b => b.text() === 'Bereit')!.trigger('click')
        expect(ansicht.emitted('bereit')).toHaveLength(1)
    })

    it('lässt nur den am längsten wartenden Anruf annehmen', async () => {
        const jetzt = Date.now() / 1000
        const ansicht = leiste({verbunden: {ausbilder: true, trainee: true}, engine: {gestartet: true, pausiert: false, automatischPausiert: false}, anrufe: [anruf('alt', jetzt - 42), {...anruf('neu', jetzt - 8), rufnummer: undefined, rufnummerUnterdrueckt: true}]})
        const annehmen = ansicht.findAll('button').filter(b => b.text() === 'Annehmen')
        expect(annehmen).toHaveLength(1)
        await annehmen[0]!.trigger('click')
        expect(ansicht.emitted('annehmen')?.[0]).toEqual(['alt'])
        expect(ansicht.text()).toContain('0176 1234567')
        expect(ansicht.text()).toContain('unterdrückt')
        expect(ansicht.text()).toContain('0:42')
    })

    it('hält die Wartezeit während einer Pause an', () => {
        const jetzt = Date.now() / 1000
        const ansicht = leiste({verbunden: {ausbilder: false, trainee: true}, engine: {gestartet: true, pausiert: true, automatischPausiert: true, pausiertSeit: jetzt - 100}, anrufe: [anruf('alt', jetzt - 130)]})
        expect(ansicht.text()).toContain('0:30')
        expect(ansicht.text()).toContain('bis beide Seiten verbunden sind')
    })
})
