import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {Abgelehnt, holeZustand, sendeAbsicht} from '../api/uebung'
import {RUECKZUG_MS, TAKT_MS, useUebung} from './useUebung'

vi.mock('../api/uebung', async original => ({
    ...await original<typeof import('../api/uebung')>(),
    holeZustand: vi.fn(),
    sendeAbsicht: vi.fn(),
}))

const hole = vi.mocked(holeZustand)
const sende = vi.mocked(sendeAbsicht)

describe('useUebung', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.resetAllMocks()
    })

    it('fragt mit der gehaltenen Version und behält den Zustand ohne Änderung', async () => {
        hole.mockResolvedValueOnce({version: 3, zustand: {anrufe: []}}).mockResolvedValue(null)
        const uebung = useUebung<'trainee'>('T-ABCDEF')
        await vi.advanceTimersByTimeAsync(0)
        expect(hole).toHaveBeenLastCalledWith('T-ABCDEF', 0)
        await vi.advanceTimersByTimeAsync(TAKT_MS)
        expect(hole).toHaveBeenLastCalledWith('T-ABCDEF', 3)
        expect(uebung.zustand.value).toEqual({anrufe: []})
        uebung.beenden()
    })

    it('meldet einen Ausfall und fragt mit wachsendem Abstand weiter', async () => {
        hole.mockRejectedValue(new Error('weg'))
        const uebung = useUebung<'trainee'>('T-ABCDEF')
        await vi.advanceTimersByTimeAsync(0)
        expect(uebung.erreichbar.value).toBe(false)
        for (const [i, pause] of RUECKZUG_MS.entries()) {
            await vi.advanceTimersByTimeAsync(pause - 1)
            expect(hole).toHaveBeenCalledTimes(i + 1)
            await vi.advanceTimersByTimeAsync(1)
            expect(hole).toHaveBeenCalledTimes(i + 2)
        }
        hole.mockResolvedValue({version: 1, zustand: {anrufe: []}})
        await vi.advanceTimersByTimeAsync(RUECKZUG_MS.at(-1)!)
        expect(uebung.erreichbar.value).toBe(true)
        uebung.beenden()
    })

    it('holt nach einer Absicht sofort den neuen Zustand', async () => {
        hole.mockResolvedValueOnce({version: 1, zustand: {pool: []}}).mockResolvedValueOnce({version: 2, zustand: {pool: ['x']}})
        sende.mockResolvedValue({version: 2, ergebnis: {szenarioId: 'a'}})
        const uebung = useUebung<'ausbilder'>('A-ABCDEF')
        await vi.advanceTimersByTimeAsync(0)
        const ergebnis = await uebung.absicht('pool.hinzufuegen', {szenario: {}})
        expect(ergebnis).toEqual({szenarioId: 'a'})
        expect(sende).toHaveBeenCalledWith('A-ABCDEF', 'pool.hinzufuegen', {szenario: {}})
        expect(hole).toHaveBeenCalledTimes(2)
        expect(uebung.zustand.value).toEqual({pool: ['x']})
        uebung.beenden()
    })

    it('fragt nach dem Beenden nicht mehr', async () => {
        hole.mockResolvedValue(null)
        const uebung = useUebung<'trainee'>('T-ABCDEF')
        await vi.advanceTimersByTimeAsync(0)
        uebung.beenden()
        await vi.advanceTimersByTimeAsync(10 * TAKT_MS)
        expect(hole).toHaveBeenCalledTimes(1)
    })
})

describe('useUebung bei Absichten und unbekannten Codes', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.resetAllMocks()
    })

    it('holt nach einer Absicht neu, auch wenn gerade eine ältere Abfrage läuft', async () => {
        let alteAbfrageFertig: (wert: null) => void = () => {}
        hole.mockResolvedValueOnce({version: 1, zustand: {pool: []}})
            .mockReturnValueOnce(new Promise(fertig => {
                alteAbfrageFertig = fertig
            }))
            .mockResolvedValueOnce({version: 2, zustand: {pool: ['x']}})
        sende.mockResolvedValue({version: 2, ergebnis: {}})
        const uebung = useUebung<'ausbilder'>('A-ABCDEFGH')
        await vi.advanceTimersByTimeAsync(0)
        await vi.advanceTimersByTimeAsync(TAKT_MS)
        const absicht = uebung.absicht('pool.hinzufuegen')
        alteAbfrageFertig(null)
        await absicht
        expect(hole).toHaveBeenCalledTimes(3)
        expect(uebung.zustand.value).toEqual({pool: ['x']})
        uebung.beenden()
    })

    it('hört bei einem unbekannten Code auf zu fragen', async () => {
        hole.mockRejectedValue(new Abgelehnt(404, 'Diesen Code gibt es nicht.'))
        const uebung = useUebung<'trainee'>('T-XXXXXXXX')
        await vi.advanceTimersByTimeAsync(0)
        expect(uebung.unbekannt.value).toBe(true)
        expect(uebung.erreichbar.value).toBe(true)
        await vi.advanceTimersByTimeAsync(20 * TAKT_MS)
        expect(hole).toHaveBeenCalledTimes(1)
    })
})
