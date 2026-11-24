import {flushPromises, mount, RouterLinkStub} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {shallowRef} from 'vue'
import {i18n} from '../i18n'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {testgraph} from '../modell/testgraph.test-hilfe'
import HilfeView from './HilfeView.vue'

const GRAPH = {...testgraph(), anleitungen: [{id: 'zugang', titel: 'Tür öffnen', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'}]}

vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(GRAPH), schwerste: shallowRef(schwersteErreichbare(GRAPH)), fehler: shallowRef(null)})}))
vi.mock('../components/KarteLeaflet.vue', () => ({default: {template: '<div/>'}}))
vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))

describe('HilfeView', () => {
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it('zeigt jeden Baustein als nicht bedienbares Beispiel', async () => {
        vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({herkunft: {}, stoffe: []})))))
        const ansicht = mount(HilfeView, {global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        await flushPromises()
        const abschnitte = ansicht.findAll('section[aria-label]').map(s => s.attributes('aria-label'))
        expect(abschnitte).toEqual(expect.arrayContaining(['Was ist der Calltaker?', 'Erste Schritte', 'Als Trainee', 'Als Ausbilder', 'Debrief und Übersicht', 'Tipps']))
        const beispiele = ansicht.findAll('figure [inert]')
        expect(beispiele).toHaveLength(8)
        expect(beispiele.every(b => b.element.children.length > 0)).toBe(true)
        for (const titel of ['Einsatzmaske', 'SNA-Fenster', 'Hinweise an den Anrufer', 'Telefonreanimation', 'Wahrheit']) {
            expect(ansicht.find(`figure [aria-label^="${titel}"]`).exists(), titel).toBe(true)
        }
        expect(ansicht.text()).toContain('Kräfte unterwegs')
        expect(ansicht.text()).toContain('Tasten')
    })

    it('setzt den Seitentitel und gibt ihn beim Verlassen zurück', () => {
        document.title = 'Calltaker'
        const ansicht = mount(HilfeView, {global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        expect(document.title).toBe('Hilfe · Calltaker')
        ansicht.unmount()
        expect(document.title).toBe('Calltaker')
    })
})
