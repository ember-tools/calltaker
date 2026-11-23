import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {ref, shallowRef} from 'vue'
import {i18n} from '../i18n'
import {anrufMit, GRAPH, zustandMit} from '../modell/ausbilder.test-hilfe'
import UebersichtView from './UebersichtView.vue'

const exakt = anrufMit('e', 'beendet')
exakt.eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e2', code: '17D01'}}
exakt.eintraege.zeiten = {code: 1090}

vi.mock('../composables/useUebung', () => ({useUebung: () => ({zustand: ref(zustandMit([exakt, anrufMit('x', 'aufgelegt')])), erreichbar: ref(true), unbekannt: ref(false), absicht: vi.fn()})}))
vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(GRAPH), schwerste: shallowRef(new Map()), fehler: shallowRef(null)})}))

describe('UebersichtView', () => {
    it('zeigt die Übung in Zahlen und lädt dem Ausbilder das Protokoll herunter', async () => {
        const erzeugt: Blob[] = []
        URL.createObjectURL = vi.fn((blob: Blob) => {
            erzeugt.push(blob)
            return 'blob:protokoll'
        })
        URL.revokeObjectURL = vi.fn()
        const klick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
        const ansicht = mount(UebersichtView, {props: {code: 'A-1', rolle: 'ausbilder'}, global: {plugins: [i18n], stubs: {RouterLink: {props: ['to'], template: '<a><slot/></a>'}}}})
        await flushPromises()
        expect(ansicht.text()).toContain('1 / 1')
        expect(ansicht.text()).toContain('60 s')
        expect(ansicht.get('tbody').text()).toContain('Sturz e')
        expect(ansicht.get('tbody').text()).toContain('exakt')
        await ansicht.findAll('button').find(b => b.text() === 'Protokoll herunterladen')!.trigger('click')
        expect(klick).toHaveBeenCalled()
        const inhalt = JSON.parse(await erzeugt[0]!.text())
        expect(inhalt.format).toBe('calltaker-protokoll')
        expect(inhalt.anrufe).toHaveLength(2)
        klick.mockRestore()
    })
})

describe('UebersichtView für den Trainee', () => {
    it('bietet dem Trainee keinen Protokoll-Download an', async () => {
        const ansicht = mount(UebersichtView, {props: {code: 'T-1', rolle: 'trainee'}, global: {plugins: [i18n], stubs: {RouterLink: true}}})
        await flushPromises()
        expect(ansicht.findAll('button').some(b => b.text() === 'Protokoll herunterladen')).toBe(false)
    })
})
