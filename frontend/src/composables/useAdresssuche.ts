import {onBeforeUnmount, ref, shallowRef, watch, type Ref} from 'vue'
import {sucheAdressen} from '../api/adressen'
import {sucheOrte} from '../api/photon'
import type {Adressvorschlag, Ortsvorschlag} from '../modell/ort'

/** How long typing has to pause before a search is sent. */
export const PAUSE_MS = 250

/** Fewer address suggestions than this, and places are looked up as well. */
export const ORTE_UNTER = 3

/**
 * Suggests addresses and places for a text being typed.
 *
 * The address list is asked first. Only when it offers fewer than three suggestions, and the text
 * has at least three characters, is Photon asked for places without a house number. A search
 * waits for a pause in typing, and newer text cancels the search still running. Text set by
 * picking a suggestion is not searched again, so a picked place costs no second Photon request.
 *
 * @param text the text being typed
 * @returns the address and place suggestions, and whether a search is running
 */
export function useAdresssuche(text: Ref<string>) {
    const adressen = shallowRef<Adressvorschlag[]>([])
    const orte = shallowRef<Ortsvorschlag[]>([])
    const sucht = ref(false)
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    let abbruch: AbortController | undefined
    let gewaehlt: string | null = null

    async function suchen(eingabe: string): Promise<void> {
        abbruch?.abort()
        const aktuell = new AbortController()
        abbruch = aktuell
        sucht.value = true
        try {
            const gefunden = await sucheAdressen(eingabe, aktuell.signal)
            const ortsuche = gefunden.length < ORTE_UNTER && eingabe.trim().length >= 3
            const gefundeneOrte = ortsuche ? await sucheOrte(eingabe, aktuell.signal).catch(() => []) : []
            if (aktuell.signal.aborted) return
            adressen.value = gefunden
            orte.value = gefundeneOrte
        } catch {
            if (!aktuell.signal.aborted) {
                adressen.value = []
                orte.value = []
            }
        } finally {
            if (abbruch === aktuell) sucht.value = false
        }
    }

    watch(text, eingabe => {
        clearTimeout(zeitgeber)
        if (eingabe === gewaehlt) return
        gewaehlt = null
        if (eingabe.trim().length < 2) {
            abbruch?.abort()
            adressen.value = []
            orte.value = []
            return
        }
        zeitgeber = setTimeout(() => void suchen(eingabe), PAUSE_MS)
    })

    onBeforeUnmount(() => {
        clearTimeout(zeitgeber)
        abbruch?.abort()
    })

    /**
     * Marks text set by picking a suggestion, which is not searched again.
     *
     * @param wert the text the pick sets
     */
    function uebernommen(wert: string): void {
        gewaehlt = wert
        abbruch?.abort()
        adressen.value = []
        orte.value = []
    }

    return {adressen, orte, sucht, uebernommen}
}
