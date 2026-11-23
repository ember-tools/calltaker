import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import {anrufMit} from '../modell/ausbilder.test-hilfe'
import ProtokollListe from './ProtokollListe.vue'

describe('ProtokollListe', () => {
    it('zeigt den neuesten Anruf zuerst und was aus jedem wurde', async () => {
        const anrufe = [anrufMit('b', 'beendet'), anrufMit('l'), anrufMit('w', 'wartet'), anrufMit('a', 'aufgelegt')]
        const ansicht = mount(ProtokollListe, {props: {anrufe, gewaehlt: 'l', code: 'A-1'}, global: {plugins: [i18n], stubs: {RouterLink: {props: ['to'], template: '<a :data-ziel="JSON.stringify(to)"><slot/></a>'}}}})
        const zeilen = ansicht.findAll('li').map(li => li.text())
        expect(zeilen[0]).toContain('aufgelegt nach 1:40')
        expect(zeilen[1]).toContain('wartet')
        expect(zeilen[2]).toContain('angenommen nach 0:30 · läuft')
        expect(zeilen[3]).toContain('angenommen nach 0:30 · Gespräch 1:10')
        expect(ansicht.get('[aria-pressed=true]').text()).toContain('Sturz l')
        await ansicht.findAll('button')[3]!.trigger('click')
        expect(ansicht.emitted('waehlen')?.[0]).toEqual(['b'])
        const debriefs = ansicht.findAll('li a')
        expect(debriefs).toHaveLength(1)
        expect(JSON.parse(debriefs[0]!.attributes('data-ziel')!)).toEqual({name: 'ausbilder-debrief', params: {code: 'A-1', anrufId: 'b'}})
    })
})
