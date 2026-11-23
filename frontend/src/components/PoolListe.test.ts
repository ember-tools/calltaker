import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import {leererEntwurf} from '../modell/szenarioentwurf'
import type {Szenario} from '../modell/szenario'
import PoolListe from './PoolListe.vue'

const szenario = (id: string, titel: string): Szenario => ({...leererEntwurf(1), id, titel, ziel: {knoten: 'k', code: '17D01'}, anrufer: {name: 'A', rufnummerUnterdrueckt: false, rufnummer: '49301'}})

describe('PoolListe', () => {
    it('zeigt Code und Befunde und verschiebt', async () => {
        const ansicht = mount(PoolListe, {
            props: {pool: [szenario('a', 'Erstes'), szenario('b', 'Zweites')], befunde: {b: [{art: 'fehler', knoten: 'x', meldung: 'weg'}]}},
            global: {plugins: [i18n]},
        })
        expect(ansicht.text()).toContain('17D01')
        expect(ansicht.text()).toContain('zu korrigieren: 1')
        const hoch = ansicht.findAll('button').filter(b => b.attributes('aria-label')?.endsWith('nach oben'))
        expect(hoch[0]!.attributes('disabled')).toBeDefined()
        await hoch[1]!.trigger('click')
        expect(ansicht.emitted('verschieben')?.[0]).toEqual(['b', 0])
        await ansicht.findAll('button').find(b => b.text() === 'Bearbeiten')!.trigger('click')
        expect(ansicht.emitted('bearbeiten')?.[0]).toEqual(['a'])
    })
})
