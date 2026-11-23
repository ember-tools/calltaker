import {mount} from '@vue/test-utils'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import SnaKacheln from './SnaKacheln.vue'

const antworten = Array.from({length: 12}, (_, nummer) => ({id: `a${nummer}`, label: `Antwort ${nummer}`, ziel: 'x'}))

/**
 * Mounts the tiles with the given answers.
 *
 * @param anzahl how many answers
 * @returns the mounted tiles
 */
function kacheln(anzahl = 12) {
    return mount(SnaKacheln, {props: {antworten: antworten.slice(0, anzahl), zusaetze: new Map([['a1', '17D01 · RD2NC.']])}, global: {plugins: [i18n]}})
}

describe('SnaKacheln', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => vi.useRealTimers())

    it('wählt mit einer Ziffer, wenn keine zweite folgen kann', async () => {
        const ansicht = kacheln(5)
        await ansicht.findAll('button')[0]!.trigger('keydown', {key: '3'})
        expect(ansicht.emitted('waehlen')?.[0]).toEqual(['a3'])
    })

    it('setzt zwei Ziffern zu einer Nummer zusammen', async () => {
        const ansicht = kacheln()
        const kachel = ansicht.findAll('button')[0]!
        await kachel.trigger('keydown', {key: '1'})
        await kachel.trigger('keydown', {key: '1'})
        expect(ansicht.emitted('waehlen')?.[0]).toEqual(['a11'])
    })

    it('wählt nach einer Pause die einstellige Nummer', async () => {
        const ansicht = kacheln()
        await ansicht.findAll('button')[0]!.trigger('keydown', {key: '1'})
        expect(ansicht.emitted('waehlen')).toBeUndefined()
        vi.advanceTimersByTime(600)
        expect(ansicht.emitted('waehlen')?.[0]).toEqual(['a1'])
    })

    it('sucht in vielen Antworten und wählt den einzigen Treffer mit Enter', async () => {
        const ansicht = kacheln()
        const suche = ansicht.get('input')
        await suche.setValue('Antwort 7')
        expect(ansicht.findAll('button')).toHaveLength(1)
        await suche.trigger('keydown', {key: 'Enter'})
        expect(ansicht.emitted('waehlen')?.[0]).toEqual(['a7'])
    })

    it('zeigt, was gleich lautende Antworten unterscheidet', () => {
        expect(kacheln().text()).toContain('17D01 · RD2NC.')
    })
})

describe('SnaKacheln bei falschen Nummern', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => vi.useRealTimers())

    it('vergisst eine Nummer ohne Kachel und nimmt danach die nächste', async () => {
        const ansicht = kacheln(5)
        const kachel = ansicht.findAll('button')[0]!
        await kachel.trigger('keydown', {key: '7'})
        await kachel.trigger('keydown', {key: '2'})
        expect(ansicht.emitted('waehlen')).toEqual([['a2']])
    })

    it('vergisst auch eine zweistellige Nummer ohne Kachel', async () => {
        const ansicht = kacheln()
        const kachel = ansicht.findAll('button')[0]!
        await kachel.trigger('keydown', {key: '1'})
        await kachel.trigger('keydown', {key: '5'})
        await kachel.trigger('keydown', {key: '4'})
        expect(ansicht.emitted('waehlen')).toEqual([['a4']])
    })
})
