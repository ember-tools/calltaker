import {getCurrentInstance, onBeforeUnmount, ref} from 'vue'

/**
 * The present in seconds, as the server counts, ticking once a second for counting waits.
 *
 * @returns the present
 */
export function useUhr() {
    const jetzt = ref(Date.now() / 1000)
    const zeitgeber = setInterval(() => {
        jetzt.value = Date.now() / 1000
    }, 1000)
    if (getCurrentInstance()) onBeforeUnmount(() => clearInterval(zeitgeber))
    return jetzt
}

/**
 * A duration as minutes and seconds.
 *
 * @param sekunden the duration
 * @returns "m:ss", or "h:mm:ss" from an hour on
 */
export function dauer(sekunden: number): string {
    const ganz = Math.max(0, Math.floor(sekunden))
    const stunden = Math.floor(ganz / 3600)
    const minuten = Math.floor((ganz % 3600) / 60)
    const rest = String(ganz % 60).padStart(2, '0')
    return stunden ? `${stunden}:${String(minuten).padStart(2, '0')}:${rest}` : `${minuten}:${rest}`
}
