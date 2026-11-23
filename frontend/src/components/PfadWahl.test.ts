import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {antwortenAusPfad} from '../modell/szenarioentwurf'
import type {Befund, Wahl, Ziel} from '../modell/szenario'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import PfadWahl from './PfadWahl.vue'

const graph = testgraph()
const schwerste = schwersteErreichbare(graph)

/**
 * Mounts the path choice so that it follows its own updates.
 *
 * @param antworten the answers to start from
 * @param befunde the findings to show
 * @returns the mounted path choice
 */
function wahl(antworten: Record<string, Wahl>, befunde: Befund[] = []) {
    const ansicht = mount(PfadWahl, {
        props: {
            graph, schwerste, befunde, antworten, ziel: undefined as Ziel | undefined,
            'onUpdate:antworten': (wert: Record<string, Wahl>) => ansicht.setProps({antworten: wert}),
            'onUpdate:ziel': (wert: Ziel | undefined) => ansicht.setProps({ziel: wert}),
        },
        global: {plugins: [i18n]},
    })
    return ansicht
}

/**
 * Clicks the button whose text contains a word.
 *
 * @param ansicht the mounted component
 * @param text the word
 */
async function klick(ansicht: ReturnType<typeof wahl>, text: string): Promise<void> {
    await ansicht.findAll('button').find(b => b.text().includes(text))!.trigger('click')
}

describe('PfadWahl', () => {
    it('klickt sich bis zum Code durch und setzt das Ziel', async () => {
        const ansicht = wahl({})
        await klick(ansicht, 'Med')
        await klick(ansicht, '1. Hand')
        await ansicht.get('input[aria-label="Alter?"]').setValue('81')
        await klick(ansicht, 'Weiter')
        await klick(ansicht, 'Sturz')
        await klick(ansicht, 'Leicht')
        expect(ansicht.props('ziel')).toEqual({knoten: 'p.e1', code: '17A01'})
        expect(ansicht.props('antworten')['rd.alter']).toEqual({wert: '81'})
        expect(ansicht.text()).toContain('Code: 17A01 · RD4C.')
    })

    it('wählt ab einer Frage neu', async () => {
        const ansicht = wahl(antwortenAusPfad(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]))
        await ansicht.findAll('button').find(b => b.attributes('aria-label') === 'Ab Beschwerde? neu wählen')!.trigger('click')
        expect(Object.keys(ansicht.props('antworten'))).toEqual(['fachrichtung', 'hand', 'rd.alter'])
        expect(ansicht.props('ziel')).toBeUndefined()
    })

    it('springt über die Code-Suche zum Endpunkt', async () => {
        const ansicht = wahl({})
        await ansicht.get('input[type=search]').setValue('67B')
        await klick(ansicht, '67B01')
        expect(ansicht.props('ziel')).toEqual({knoten: 'fw.e', code: '67B01'})
        expect(ansicht.props('antworten')['fachrichtung']).toEqual({antwort: 'fw', label: 'Feuer'})
    })

    it('markiert Befunde und Antworten außerhalb des Pfads', async () => {
        const antworten = {...antwortenAusPfad(graph, BIS_SITUATION), 'weg.knoten': {antwort: 'x'}}
        const ansicht = wahl(antworten, [{art: 'fehler', knoten: 'weg.knoten', meldung: 'Knoten gibt es nicht mehr'}, {art: 'warnung', knoten: 'hand', meldung: 'Label geändert'}])
        expect(ansicht.text()).toContain('Antworten außerhalb des Pfads: 1')
        expect(ansicht.text()).toContain('Knoten gibt es nicht mehr')
        expect(ansicht.find('li.border-warnung').text()).toContain('Label geändert')
        await klick(ansicht, 'Diese Antworten entfernen')
        expect(ansicht.props('antworten')['weg.knoten']).toBeUndefined()
    })
})

describe('PfadWahl bei einem fremden Ziel', () => {
    it('sagt, wenn der Pfad zu einem anderen Code führt', () => {
        const ansicht = mount(PfadWahl, {
            props: {graph, schwerste, befunde: [], antworten: antwortenAusPfad(graph, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]), ziel: {knoten: 'p.e2', code: '17D01'}},
            global: {plugins: [i18n]},
        })
        expect(ansicht.text()).toContain('Der Pfad führt zu 17A01, nicht zu diesem Code.')
    })

    it('behält das Label, mit dem eine unveränderte Antwort geschrieben wurde', async () => {
        const antworten = {...antwortenAusPfad(graph, BIS_SITUATION), hand: {antwort: 'eins', label: 'Erste Hand (alt)'}}
        const ansicht = wahl(antworten)
        await klick(ansicht, 'Leicht')
        expect(ansicht.props('antworten')['hand']).toEqual({antwort: 'eins', label: 'Erste Hand (alt)'})
    })
})
