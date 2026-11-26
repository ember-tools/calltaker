import {flushPromises, mount, RouterLinkStub} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {shallowRef} from 'vue'
import {i18n} from '../i18n'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {testgraph} from '../modell/testgraph.test-hilfe'
import {HELP_TOPICS} from '../helpTopics'
import HelpTopicView from './HelpTopicView.vue'
import HilfeView from './HilfeView.vue'

const GRAPH = {...testgraph(), anleitungen: [{id: 'zugang', titel: 'Tür öffnen', saetze: ['S'], pflicht: true, wenn: [{fachrichtung: 'rd' as const}], quelle: 'Q'}]}

vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(GRAPH), schwerste: shallowRef(schwersteErreichbare(GRAPH)), fehler: shallowRef(null)})}))
vi.mock('../components/KarteLeaflet.vue', () => ({default: {template: '<div/>'}}))
vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))

describe('help center', () => {
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it('lists every topic on the overview', async () => {
        const overview = mount(HilfeView, {global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        await flushPromises()
        expect(overview.find('section[aria-label]').attributes('aria-label')).toBe('Was ist der Calltaker?')
        expect(overview.findAll('li h2').map(heading => heading.text())).toHaveLength(HELP_TOPICS.length)
        expect(overview.text()).toContain('Den Anrufer spielen')
    })

    it('shows every building block across the topics as an example that cannot be used', async () => {
        vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({herkunft: {}, stoffe: []})))))
        const pages: ReturnType<typeof mount>[] = []
        for (const topic of HELP_TOPICS) {
            const page = mount(HelpTopicView, {props: {slug: topic.slug}, global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
            await flushPromises()
            pages.push(page)
        }
        const sections = pages.flatMap(page => page.findAll('section[aria-label]').map(s => s.attributes('aria-label')))
        expect(sections).toEqual(expect.arrayContaining(['Warteschlange', 'Einsatzmaske', 'Leitfragen', 'Live: Spiegel und Lösungskarte', 'Pool und Generator']))
        expect(pages.every(page => page.findAll('section[aria-label] > h2').every(heading => heading.text() !== page.find('h1').text()))).toBe(true)
        const examples = pages.flatMap(page => page.findAll('figure [inert]'))
        expect(examples).toHaveLength(8)
        expect(examples.every(example => example.element.children.length > 0)).toBe(true)
        const find = (selector: string) => pages.map(page => page.find(selector)).find(found => found.exists())
        for (const title of ['Einsatzmaske', 'SNA-Fenster', 'Hinweise an den Anrufer', 'Telefonreanimation', 'Lösung']) {
            expect(find(`figure [aria-label^="${title}"]`)?.exists(), title).toBe(true)
        }
        expect(find('figure [aria-label="So sprichst du als Anrufer"]')?.text()).toContain('Du bist selbst betroffen.')
        const text = pages.map(page => page.text()).join('\n')
        for (const expected of [
            'Neugeborenes, Säugling, Kind und Erwachsener', 'Den Anrufer spielen', 'Wenn gefragt', 'Belastende Lagen bleiben ausgeschlossen',
            'liegt der Kreis dort, wo der Anrufer ist', 'weichst du aus, bis der Calltaker nachhakt', 'warnt die Seite vor Teilen, die nicht zusammenpassen',
            'Wer sich sicher ist, wählt die Kachel direkt.', 'den Weg über sie', 'Antworten mit Alt und der Ziffer', 'wenn die Lösung keine Antwort vorgibt',
            'Alt+ZifferLeitfrage beantworten', 'Kräfte unterwegs', 'Tasten',
        ]) {
            expect(text, expected).toContain(expected)
        }
    })

    it('names the topic in the title and leads on to the next one', async () => {
        const page = mount(HelpTopicView, {props: {slug: 'notrufabfrage'}, global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        await vi.waitFor(() => expect(document.title).toBe('Notrufabfrage – Hilfe – Calltaker'))
        expect(page.text()).toContain('Weiter: Telefonreanimation')
    })

    it('sets the overview title', async () => {
        mount(HilfeView, {global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        await vi.waitFor(() => expect(document.title).toBe('Hilfe – Calltaker'))
    })
})
