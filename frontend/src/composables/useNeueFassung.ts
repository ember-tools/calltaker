import {getCurrentInstance, onBeforeUnmount, ref} from 'vue'

/** How often an open page asks which build the server serves. */
export const PRUEFEN_ALLE_MS = 60_000

/**
 * Whether the server serves a newer build than this page runs. The page asks for the build's
 * `fassung.json` now and then, and whenever it comes back into view; a page left open across a
 * deploy would otherwise keep running the old frontend against the new server.
 *
 * @returns true once a different build is served
 */
export function useNeueFassung() {
    const neu = ref(false)

    async function pruefen(): Promise<void> {
        if (neu.value) return
        try {
            const antwort = await fetch('/fassung.json', {cache: 'no-store'})
            if (!antwort.ok) return
            const {gebaut} = await antwort.json() as {gebaut?: string}
            neu.value = Boolean(gebaut) && gebaut !== __GEBAUT__
        } catch {
            neu.value = false
        }
    }

    function sichtbar(): void {
        if (document.visibilityState === 'visible') void pruefen()
    }

    const zeitgeber = setInterval(() => void pruefen(), PRUEFEN_ALLE_MS)
    document.addEventListener('visibilitychange', sichtbar)
    void pruefen()
    if (getCurrentInstance()) {
        onBeforeUnmount(() => {
            clearInterval(zeitgeber)
            document.removeEventListener('visibilitychange', sichtbar)
        })
    }
    return neu
}
