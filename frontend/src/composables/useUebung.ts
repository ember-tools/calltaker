import {createPoller} from '@emberbox/ui'
import {computed, getCurrentInstance, onBeforeUnmount, readonly, ref, shallowRef} from 'vue'
import {Abgelehnt, holeZustand, sendeAbsicht} from '../api/uebung'
import type {Rolle, ZustandFuer} from '../modell/uebung'

/** How long to wait between polls while the tab is shown. */
export const TAKT_MS = 1000

/** The longest wait between polls while the server cannot be reached. */
export const MAX_BACKOFF_MS = 8000

/**
 * The wait between polls while the tab is hidden: slow enough to spare the server, fast enough that
 * a waiting call still rings soon. It must stay well below the backend's `ONLINE_FRIST` of eight
 * seconds, or a hidden role would flicker between connected and not connected on the other side.
 * Browsers stretch it to about a minute in tabs hidden for long.
 */
export const HIDDEN_INTERVAL_MS = 5000

/**
 * Keeps the state of an exercise current by polling it, and sends intents.
 *
 * A poll carries the version already held, so the server answers with nothing when nothing
 * changed. After a failed poll the view counts as disconnected and polls again after 2, 4 and then
 * every 8 seconds; the first successful poll brings the whole state. A code the server does not
 * know ends the polling for good, since no retry will bring the exercise back. An intent's answer
 * carries the new version, and the state is then fetched straight away with a poll sent after the
 * intent, instead of on the next tick. A hidden tab polls every five seconds.
 *
 * @param code the code of the exercise; the type parameter names the role it stands for
 * @returns the state, whether the server is reachable, whether the code is unknown, and a way to
 *     send intents
 */
export function useUebung<R extends Rolle>(code: string) {
    const zustand = shallowRef<ZustandFuer<R> | null>(null)
    const unbekannt = ref(false)
    const failed = ref(false)
    let version = 0

    const poller = createPoller(async () => {
        try {
            const stand = await holeZustand<ZustandFuer<R>>(code, version)
            if (stand) {
                version = stand.version
                zustand.value = stand.zustand
            }
        } catch (fehler) {
            if (!(fehler instanceof Abgelehnt && fehler.status === 404)) {
                failed.value = true
                throw fehler
            }
            unbekannt.value = true
            poller.stop()
        }
    }, {intervalMs: TAKT_MS, maxIntervalMs: MAX_BACKOFF_MS, hiddenIntervalMs: HIDDEN_INTERVAL_MS})

    async function absicht(art: string, daten: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
        const antwort = await sendeAbsicht(code, art, daten)
        if (antwort.version !== version) await poller.refresh()
        return antwort.ergebnis
    }

    const beenden = poller.stop
    poller.start()
    if (getCurrentInstance()) onBeforeUnmount(beenden)

    return {
        zustand: computed<ZustandFuer<R> | null>(() => zustand.value),
        erreichbar: computed(() => !failed.value || poller.connected.value),
        unbekannt: readonly(unbekannt),
        absicht,
        beenden,
    }
}
