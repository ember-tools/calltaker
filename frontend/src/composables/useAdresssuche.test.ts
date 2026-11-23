import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {ref} from 'vue'
import {sucheAdressen} from '../api/adressen'
import {sucheOrte} from '../api/photon'
import {PAUSE_MS, useAdresssuche} from './useAdresssuche'

vi.mock('../api/adressen', () => ({sucheAdressen: vi.fn()}))
vi.mock('../api/photon', () => ({sucheOrte: vi.fn()}))

const adressen = vi.mocked(sucheAdressen)
const orte = vi.mocked(sucheOrte)
const adresse = (strasse: string) => ({beschriftung: strasse, strasse, hausnummer: '', plz: '', ortsteil: '', bezirk: ''})
const ort = {beschriftung: 'U Hermannplatz', name: 'U Hermannplatz', ortsteil: 'Neukölln', breite: 52.48, laenge: 13.42}

describe('useAdresssuche', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.resetAllMocks()
    })

    it('wartet eine Pause ab und fragt dann das Adressverzeichnis', async () => {
        adressen.mockResolvedValue([adresse('A'), adresse('B'), adresse('C')])
        const text = ref('')
        const suche = useAdresssuche(text)
        text.value = 'Kar'
        await vi.advanceTimersByTimeAsync(10)
        text.value = 'Karl'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        expect(adressen).toHaveBeenCalledTimes(1)
        expect(adressen.mock.calls[0]![0]).toBe('Karl')
        expect(suche.adressen.value).toHaveLength(3)
        expect(orte).not.toHaveBeenCalled()
    })

    it('fragt Photon nach Orten, wenn das Verzeichnis wenig findet', async () => {
        adressen.mockResolvedValue([])
        orte.mockResolvedValue([ort])
        const text = ref('')
        const suche = useAdresssuche(text)
        text.value = 'Hermannplatz'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        expect(suche.orte.value).toEqual([ort])
    })

    it('behält die Adressen, wenn Photon ausfällt', async () => {
        adressen.mockResolvedValue([adresse('Hermannstraße')])
        orte.mockRejectedValue(new TypeError('Failed to fetch'))
        const text = ref('')
        const suche = useAdresssuche(text)
        text.value = 'Hermann'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        expect(suche.adressen.value).toHaveLength(1)
        expect(suche.orte.value).toEqual([])
    })

    it('bricht eine ältere Suche ab, wenn weitergetippt wird', async () => {
        const signale: AbortSignal[] = []
        adressen.mockImplementation((_, signal) => {
            signale.push(signal)
            return new Promise(() => {})
        })
        const text = ref('')
        useAdresssuche(text)
        text.value = 'Karl'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        text.value = 'Karl-M'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        expect(signale[0]!.aborted).toBe(true)
        expect(signale[1]!.aborted).toBe(false)
    })
})

describe('useAdresssuche nach einer Auswahl', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
        vi.useRealTimers()
        vi.resetAllMocks()
    })

    it('sucht den übernommenen Text nicht noch einmal', async () => {
        adressen.mockResolvedValue([])
        orte.mockResolvedValue([ort])
        const text = ref('')
        const suche = useAdresssuche(text)
        suche.uebernommen('U Hermannplatz, Neukölln')
        text.value = 'U Hermannplatz, Neukölln'
        await vi.advanceTimersByTimeAsync(PAUSE_MS)
        expect(adressen).not.toHaveBeenCalled()
        expect(orte).not.toHaveBeenCalled()
    })
})
