import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {nextTick, ref} from 'vue'
import {leereEintraege} from '../modell/eintraege'
import type {AnrufSicht} from '../modell/uebung'
import {SENDEN_NACH_MS, useGespraech} from './useGespraech'

const anruf = (id: string, name = ''): AnrufSicht => ({
    id, zustand: 'gespraech', klingeltSeit: 0, rufnummerUnterdrueckt: false,
    eintraege: {...leereEintraege(), anrufer: {name, rufnummerBestaetigt: false, rueckrufnummer: ''}},
})

describe('useGespraech', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => vi.useRealTimers())

    it('übernimmt beim neuen Gespräch, was der Server hat, und danach nicht mehr', async () => {
        const aktuell = ref<AnrufSicht | undefined>(anruf('a', 'Server'))
        const {eintraege} = useGespraech(aktuell, vi.fn().mockResolvedValue({}))
        expect(eintraege.value.anrufer.name).toBe('Server')
        eintraege.value.anrufer.name = 'Getippt'
        aktuell.value = anruf('a', 'Alt')
        await nextTick()
        expect(eintraege.value.anrufer.name).toBe('Getippt')
        aktuell.value = anruf('b')
        await nextTick()
        expect(eintraege.value.anrufer.name).toBe('')
    })

    it('sendet nach einer Pause im Tippen, und auf Wunsch sofort', async () => {
        const absicht = vi.fn().mockResolvedValue({})
        const {eintraege, jetztSenden} = useGespraech(ref(anruf('a')), absicht)
        eintraege.value.hinweise = 'T'
        await nextTick()
        eintraege.value.hinweise = 'Tür'
        await nextTick()
        vi.advanceTimersByTime(SENDEN_NACH_MS)
        expect(absicht).toHaveBeenCalledTimes(1)
        expect(absicht.mock.calls[0]![1]).toMatchObject({anrufId: 'a', eintraege: {hinweise: 'Tür'}})
        await jetztSenden()
        expect(absicht).toHaveBeenCalledTimes(2)
    })

    it('schickt die erste Änderung nach dem Übernehmen', async () => {
        const absicht = vi.fn().mockResolvedValue({})
        const {eintraege} = useGespraech(ref(anruf('a', 'Server')), absicht)
        eintraege.value.hinweise = 'T'
        await nextTick()
        vi.advanceTimersByTime(SENDEN_NACH_MS)
        expect(absicht).toHaveBeenCalledTimes(1)
    })

    it('lässt keine ältere Sendung eine neuere überholen', async () => {
        let fertig: () => void = () => {}
        const absicht = vi.fn().mockImplementationOnce(() => new Promise<void>(los => {
            fertig = los
        })).mockResolvedValue({})
        const {eintraege, jetztSenden} = useGespraech(ref(anruf('a')), absicht)
        const erste = jetztSenden()
        eintraege.value.hinweise = 'neu'
        void jetztSenden()
        expect(absicht).toHaveBeenCalledTimes(1)
        fertig()
        await erste
        expect(absicht).toHaveBeenCalledTimes(2)
        expect(absicht.mock.calls[1]![1]).toMatchObject({eintraege: {hinweise: 'neu'}})
    })

    it('übernimmt Zeiten und Übergabestand aus der Antwort, ohne erneut zu senden', async () => {
        const absicht = vi.fn().mockImplementation((_: string, daten: {eintraege: {hinweise: string}}) => Promise.resolve({
            zeiten: {uebergabe: 42},
            uebergeben: {ort: leereEintraege().ort, anrufer: leereEintraege().anrufer, betroffener: '', abfrage: {pfad: []}, hinweise: daten.eintraege.hinweise},
        }))
        const {eintraege, jetztSenden} = useGespraech(ref(anruf('a')), absicht)
        eintraege.value.hinweise = 'vorher'
        eintraege.value.uebergabe = true
        await nextTick()
        await jetztSenden()
        await nextTick()
        expect(eintraege.value.zeiten.uebergabe).toBe(42)
        expect(eintraege.value.uebergeben?.hinweise).toBe('vorher')
        vi.advanceTimersByTime(SENDEN_NACH_MS * 3)
        await nextTick()
        expect(absicht).toHaveBeenCalledTimes(1)
        eintraege.value.hinweise = 'nachher'
        await nextTick()
        vi.advanceTimersByTime(SENDEN_NACH_MS)
        expect(absicht).toHaveBeenCalledTimes(2)
    })
})
