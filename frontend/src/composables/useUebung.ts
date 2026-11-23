import {getCurrentInstance, onBeforeUnmount, readonly, ref, shallowRef} from 'vue'
import {Abgelehnt, holeZustand, sendeAbsicht} from '../api/uebung'
import type {Rolle, ZustandFuer} from '../modell/uebung'

/** How long to wait between polls, and after one, two, three or more failed polls. */
export const TAKT_MS = 1000
export const RUECKZUG_MS = [1000, 2000, 4000, 8000]

/**
 * Keeps the state of an exercise current by polling it, and sends intents.
 *
 * A poll carries the version already held, so the server answers with nothing when nothing
 * changed. After a failed poll the view counts as disconnected and polls again after 1, 2, 4 and
 * then every 8 seconds; the first successful poll brings the whole state. A code the server does
 * not know ends the polling for good, since no retry will bring the exercise back. An intent's
 * answer carries the new version, and the state is then fetched straight away with a poll sent
 * after the intent, instead of on the next tick.
 *
 * @param code the code of the exercise; the type parameter names the role it stands for
 * @returns the state, whether the server is reachable, whether the code is unknown, and a way to
 *     send intents
 */
export function useUebung<R extends Rolle>(code: string) {
    const zustand = shallowRef<ZustandFuer<R> | null>(null)
    const erreichbar = ref(true)
    const unbekannt = ref(false)
    const fehlschlaege = ref(0)
    let version = 0
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    let beendet = false
    let laeuft: Promise<void> | null = null

    async function abfragen(): Promise<void> {
        try {
            const stand = await holeZustand<ZustandFuer<R>>(code, version)
            if (stand) {
                version = stand.version
                zustand.value = stand.zustand
            }
            erreichbar.value = true
            fehlschlaege.value = 0
        } catch (fehler) {
            if (fehler instanceof Abgelehnt && fehler.status === 404) {
                unbekannt.value = true
                beenden()
                return
            }
            erreichbar.value = false
            fehlschlaege.value++
        }
    }

    function planen(): void {
        if (beendet) return
        const pause = fehlschlaege.value === 0 ? TAKT_MS : RUECKZUG_MS[Math.min(fehlschlaege.value, RUECKZUG_MS.length) - 1]!
        zeitgeber = setTimeout(() => void takt(), pause)
    }

    async function takt(): Promise<void> {
        clearTimeout(zeitgeber)
        laeuft ??= abfragen().finally(() => {
            laeuft = null
        })
        await laeuft
        clearTimeout(zeitgeber)
        planen()
    }

    async function absicht(art: string, daten: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
        const antwort = await sendeAbsicht(code, art, daten)
        if (antwort.version !== version) {
            await laeuft
            await takt()
        }
        return antwort.ergebnis
    }

    function beenden(): void {
        beendet = true
        clearTimeout(zeitgeber)
    }

    void takt()
    if (getCurrentInstance()) onBeforeUnmount(beenden)

    return {zustand: readonly(zustand), erreichbar: readonly(erreichbar), unbekannt: readonly(unbekannt), absicht, beenden}
}
