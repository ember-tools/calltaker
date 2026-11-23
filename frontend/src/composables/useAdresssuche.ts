import {onBeforeUnmount, ref, shallowRef, watch, type Ref} from 'vue'
import {sucheAdressen} from '../api/adressen'
import {sucheOrte} from '../api/orte'
import type {Adressvorschlag, Ortsvorschlag} from '../modell/ort'

/** How long typing has to pause before a search is sent. */
export const PAUSE_MS = 250

/** Places are looked up from this many characters on. */
export const ORTE_AB = 3

/**
 * Suggests addresses and places for a text being typed.
 *
 * The address list and, from three characters on, the named places are asked side by side; both
 * live on this application's server. A failed place search leaves the addresses standing. A
 * search waits for a pause in typing, and newer text cancels the search still running. Text set
 * by picking a suggestion is not searched again.
 *
 * @param text the text being typed
 * @param ruhig whether to leave the text unsearched, as the trainer's read-only mirror does
 * @returns the address and place suggestions, and whether a search is running
 */
export function useAdresssuche(text: Ref<string>, ruhig: () => boolean = () => false) {
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
            const ortsuche = eingabe.trim().length >= ORTE_AB ? sucheOrte(eingabe, aktuell.signal).catch(() => []) : Promise.resolve([])
            const [gefunden, gefundeneOrte] = await Promise.all([sucheAdressen(eingabe, aktuell.signal), ortsuche])
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
        if (ruhig()) return
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
