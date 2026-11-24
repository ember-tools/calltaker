import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {nextTick, ref} from 'vue'
import {useTaktgeber} from './useTaktgeber'

describe('useTaktgeber', () => {
    beforeEach(() => {
        vi.useFakeTimers()
    })
    afterEach(() => {
        vi.useRealTimers()
        vi.unstubAllGlobals()
    })

    it('zählt im Takt, solange er läuft, und beginnt nach dem Anhalten von vorn', async () => {
        const laeuft = ref(false)
        const takt = ref(100)
        const {schlaege} = useTaktgeber(() => laeuft.value, () => takt.value, () => true)
        laeuft.value = true
        await nextTick()
        expect(schlaege.value).toBe(1)
        vi.advanceTimersByTime(6000)
        expect(schlaege.value).toBe(11)
        laeuft.value = false
        await nextTick()
        vi.advanceTimersByTime(6000)
        expect(schlaege.value).toBe(11)
        takt.value = 120
        laeuft.value = true
        await nextTick()
        vi.advanceTimersByTime(6000)
        expect(schlaege.value).toBe(13)
    })

    it('lässt beim Neugeborenen jeden vierten Schlag als Beatmung aus', async () => {
        const laeuft = ref(false)
        const {schlaege, beatmung} = useTaktgeber(() => laeuft.value, () => 120, () => true, () => 4)
        laeuft.value = true
        await nextTick()
        vi.advanceTimersByTime(1500)
        expect(schlaege.value).toBe(3)
        expect(beatmung.value).toBe(true)
        vi.advanceTimersByTime(500)
        expect(beatmung.value).toBe(false)
        vi.advanceTimersByTime(57500)
        expect(schlaege.value).toBe(90)
    })

    it('beginnt den Zyklus neu, wenn die Gruppe zur Beatmung wechselt', async () => {
        const laeuft = ref(false)
        const alle = ref(0)
        const {beatmung} = useTaktgeber(() => laeuft.value, () => 120, () => true, () => alle.value)
        laeuft.value = true
        await nextTick()
        vi.advanceTimersByTime(2500)
        alle.value = 4
        await nextTick()
        vi.advanceTimersByTime(1500)
        expect(beatmung.value).toBe(false)
        vi.advanceTimersByTime(500)
        expect(beatmung.value).toBe(true)
    })

    it('holt verpasste Schläge nicht im Schwall nach', async () => {
        const laeuft = ref(false)
        const {schlaege} = useTaktgeber(() => laeuft.value, () => 100, () => true)
        laeuft.value = true
        await nextTick()
        const jetzt = performance.now()
        vi.spyOn(performance, 'now').mockReturnValue(jetzt + 60000)
        vi.advanceTimersByTime(600)
        expect(schlaege.value).toBeLessThanOrEqual(3)
        vi.restoreAllMocks()
    })

    it('klickt hörbar nur, wenn er nicht stumm ist', async () => {
        const gestartet = vi.fn()
        const knoten = () => ({connect: (ziel: unknown) => ziel, frequency: {value: 0}, gain: {setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn()}, start: gestartet, stop: vi.fn()})
        vi.stubGlobal('AudioContext', class {
            currentTime = 0
            destination = {}
            createOscillator = knoten
            createGain = knoten
            resume = () => Promise.resolve()
            close = () => Promise.resolve()
        })
        const laeuft = ref(false)
        const stumm = ref(false)
        useTaktgeber(() => laeuft.value, () => 100, () => stumm.value)
        window.dispatchEvent(new KeyboardEvent('keydown'))
        laeuft.value = true
        await nextTick()
        vi.advanceTimersByTime(600)
        expect(gestartet).toHaveBeenCalledTimes(2)
        stumm.value = true
        vi.advanceTimersByTime(600)
        expect(gestartet).toHaveBeenCalledTimes(2)
    })
})
