import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {ref, shallowRef} from 'vue'
import {zustandMit} from '../modell/ausbilder.test-hilfe'
import {i18n} from '../i18n'
import AusbilderView from './AusbilderView.vue'

vi.mock('../composables/useUebung', () => ({useUebung: () => ({zustand: ref(zustandMit([])), erreichbar: ref(true), unbekannt: ref(false), absicht: vi.fn()})}))
vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(null), schwerste: shallowRef(new Map()), fehler: shallowRef('HTTP 500')})}))
vi.mock('../api/gebiete', () => ({ladeGebiete: vi.fn().mockResolvedValue({}), zufallsAdresse: vi.fn()}))

describe('AusbilderView ohne Abfragegraph', () => {
    it('meldet den Fehler und lässt den Pool pflegen', async () => {
        const ansicht = mount(AusbilderView, {props: {code: 'A-1'}, global: {plugins: [i18n], stubs: {RouterLink: true}}})
        expect(ansicht.get('[role=alert]').text()).toContain('HTTP 500')
        const reiter = (name: string) => ansicht.findAll('[role=tab]').find(tab => tab.text() === name)!
        await reiter('Pool').trigger('mousedown', {button: 0})
        await flushPromises()
        expect(reiter('Pool').attributes('aria-selected')).toBe('true')
        expect(ansicht.text()).toContain('Sturz p')
        await reiter('Live').trigger('mousedown', {button: 0})
        await flushPromises()
        expect(reiter('Live').attributes('aria-selected')).toBe('true')
    })
})
