import {afterEach, describe, expect, it, vi} from 'vitest'
import {createMemoryHistory, type RouteLocationNormalized} from 'vue-router'
import {Abgelehnt, rolleVon} from '../api/uebung'
import {createAppRouter, passendeRolle, reloadOnStaleChunk} from './index'

vi.mock('../api/uebung', async original => ({
    ...await original<typeof import('../api/uebung')>(),
    rolleVon: vi.fn(),
}))

const ziel = (rolle: string, code: string, name = rolle) => ({name, params: {code}, meta: {rolle}}) as unknown as RouteLocationNormalized

describe('passendeRolle', () => {
    afterEach(() => vi.resetAllMocks())

    it('lässt einen Code in die Ansicht seiner Rolle', async () => {
        vi.mocked(rolleVon).mockResolvedValue('ausbilder')
        await expect(passendeRolle(ziel('ausbilder', 'A-ABCDEFGH'))).resolves.toBe(true)
    })

    it('schickt einen Trainee-Code in die Trainee-Ansicht', async () => {
        vi.mocked(rolleVon).mockResolvedValue('trainee')
        await expect(passendeRolle(ziel('ausbilder', 'T-ABCDEFGH'))).resolves.toEqual({name: 'trainee', params: {code: 'T-ABCDEFGH'}})
    })

    it('schickt einen Trainee-Code vom Debrief des Ausbilders in die Trainee-Ansicht', async () => {
        vi.mocked(rolleVon).mockResolvedValue('trainee')
        await expect(passendeRolle(ziel('ausbilder', 'T-ABCDEFGH', 'ausbilder-debrief'))).resolves.toEqual({name: 'trainee', params: {code: 'T-ABCDEFGH'}})
        vi.mocked(rolleVon).mockResolvedValue('trainee')
        await expect(passendeRolle(ziel('trainee', 'T-ABCDEFGH', 'trainee-uebersicht'))).resolves.toBe(true)
    })

    it('öffnet die Ansicht, wenn der Code unbekannt ist', async () => {
        vi.mocked(rolleVon).mockRejectedValue(new Abgelehnt(404, 'Diesen Code gibt es nicht.'))
        await expect(passendeRolle(ziel('trainee', 'T-XXXXXXXX'))).resolves.toBe(true)
    })
})

describe('createAppRouter', () => {
    it('marks only the start and help pages as public', () => {
        const router = createAppRouter(createMemoryHistory())
        const isPublic = (path: string) => router.resolve(path).meta.public === true
        expect(isPublic('/')).toBe(true)
        expect(isPublic('/hilfe')).toBe(true)
        expect(isPublic('/a/A-ABCDEFGH')).toBe(false)
        expect(isPublic('/t/T-ABCDEFGH/uebersicht')).toBe(false)
    })
})

describe('reloadOnStaleChunk', () => {
    afterEach(() => vi.unstubAllGlobals())

    it('loads the target anew when a view cannot be loaded, and ignores other errors', async () => {
        const assign = vi.fn()
        vi.stubGlobal('location', {...window.location, assign})
        const router = createAppRouter(createMemoryHistory())
        router.addRoute({path: '/stale', component: () => Promise.reject(new TypeError('Failed to fetch dynamically imported module: /assets/x.js'))})
        router.addRoute({path: '/broken', component: () => Promise.reject(new Error('something else'))})
        reloadOnStaleChunk(router)
        await router.push('/stale').catch(() => undefined)
        await router.push('/broken').catch(() => undefined)
        expect(assign).toHaveBeenCalledTimes(1)
        expect(assign).toHaveBeenCalledWith('/stale')
    })

    it('does not load a page again that is already at the target', async () => {
        const assign = vi.fn()
        vi.stubGlobal('location', {...window.location, pathname: '/stale', search: '', hash: '', assign})
        const router = createAppRouter(createMemoryHistory())
        router.addRoute({path: '/stale', component: () => Promise.reject(new TypeError('Failed to fetch dynamically imported module: /assets/x.js'))})
        reloadOnStaleChunk(router)
        await router.push('/stale').catch(() => undefined)
        expect(assign).not.toHaveBeenCalled()
    })
})
