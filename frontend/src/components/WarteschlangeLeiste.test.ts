import {mount} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
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
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it('klingelt, solange ein Anruf wartet, und schweigt im Beispiel der Hilfe', () => {
        const tonquelle = vi.fn(function (this: object) {
            Object.assign(this, {
                currentTime: 0, destination: {},
                createOscillator: () => ({frequency: {}, connect: (ziel: object) => ziel, start: vi.fn(), stop: vi.fn()}),
                createGain: () => ({gain: {}, connect: (ziel: object) => ziel}),
                close: vi.fn(),
            })
        })
        vi.stubGlobal('AudioContext', tonquelle)
        const jetzt = Date.now() / 1000
        const zustand: TraineeZustand = {verbunden: {ausbilder: true, trainee: true}, engine: {gestartet: true, pausiert: false, automatischPausiert: false}, anrufe: [anruf('alt', jetzt - 5)]}
        mount(WarteschlangeLeiste, {props: {zustand, quiet: true}, global: {plugins: [i18n]}}).unmount()
        expect(tonquelle).not.toHaveBeenCalled()
        mount(WarteschlangeLeiste, {props: {zustand}, global: {plugins: [i18n]}}).unmount()
        expect(tonquelle).toHaveBeenCalled()
    })

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
