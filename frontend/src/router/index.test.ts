import {afterEach, describe, expect, it, vi} from 'vitest'
import type {RouteLocationNormalized} from 'vue-router'
import {Abgelehnt, rolleVon} from '../api/uebung'
import {passendeRolle} from './index'

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
