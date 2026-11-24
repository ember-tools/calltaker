import {flushPromises, mount} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {createMemoryHistory, createRouter} from 'vue-router'
import {Abgelehnt, anlegen, rolleVon} from '../api/uebung'
import {i18n} from '../i18n'
import StartView from './StartView.vue'

vi.mock('../api/uebung', async original => ({
    ...await original<typeof import('../api/uebung')>(),
    anlegen: vi.fn(),
    rolleVon: vi.fn(),
}))

/**
 * Mounts the start page with a router holding the exercise routes as stubs.
 *
 * @returns the page and its router
 */
async function seite() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            {path: '/', name: 'start', component: StartView},
            {path: '/a/:code', name: 'ausbilder', component: {render: () => null}},
            {path: '/t/:code', name: 'trainee', component: {render: () => null}},
            {path: '/hilfe', name: 'hilfe', component: {render: () => null}},
        ],
    })
    await router.push('/')
    return {ansicht: mount(StartView, {global: {plugins: [i18n, router]}}), router}
}

describe('StartView', () => {
    afterEach(() => vi.resetAllMocks())

    it('zeigt den Namen der Anwendung', async () => {
        const {ansicht} = await seite()
        expect(ansicht.text()).toContain('Calltaker')
    })

    it('legt eine Übung an und öffnet die Ausbilder-Ansicht', async () => {
        vi.mocked(anlegen).mockResolvedValue({ausbilderCode: 'A-ABCDEF', traineeCode: 'T-ABCDEF'})
        const {ansicht, router} = await seite()
        await ansicht.get('button[type=button]').trigger('click')
        await flushPromises()
        expect(router.currentRoute.value.fullPath).toBe('/a/A-ABCDEF')
    })

    it('tritt mit einem Code der passenden Rolle bei', async () => {
        vi.mocked(rolleVon).mockResolvedValue('trainee')
        const {ansicht, router} = await seite()
        await ansicht.get('input').setValue(' t-abcdef ')
        await ansicht.get('form').trigger('submit')
        await flushPromises()
        expect(rolleVon).toHaveBeenCalledWith('T-ABCDEF')
        expect(router.currentRoute.value.fullPath).toBe('/t/T-ABCDEF')
    })

    it('zeigt den Grund, wenn der Code unbekannt ist', async () => {
        vi.mocked(rolleVon).mockRejectedValue(new Abgelehnt(404, 'Diesen Code gibt es nicht.'))
        const {ansicht} = await seite()
        await ansicht.get('input').setValue('A-XXXXXX')
        await ansicht.get('form').trigger('submit')
        await flushPromises()
        expect(ansicht.get('[role=alert]').text()).toBe('Diesen Code gibt es nicht.')
    })
})

describe('StartView für Neue', () => {
    it('verweist auf die Hilfe', async () => {
        const {ansicht} = await seite()
        expect(ansicht.get('a[href="/hilfe"]').text()).toBe('Neu hier? Hilfe & Anleitung')
    })
})
