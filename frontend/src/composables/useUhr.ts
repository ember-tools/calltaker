import {getCurrentInstance, onBeforeUnmount, ref} from 'vue'
import {dauer} from '../modell/zeit'

export {dauer}

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
 * How long a call has waited: up to now, or up to the start of a pause, when waiting stands still.
 *
 * @param klingeltSeit when the call started ringing
 * @param jetzt the present
 * @param pausiertSeit when the queue was paused, if it is
 * @returns the waiting time as "m:ss"
 */
export function wartezeit(klingeltSeit: number, jetzt: number, pausiertSeit?: number): string {
    return dauer((pausiertSeit ?? jetzt) - klingeltSeit)
}

/**
 * How long a conversation has run.
 *
 * @param angenommenUm when the call was accepted
 * @param jetzt the present
 * @returns the duration as "m:ss"
 */
export function gespraechsdauer(angenommenUm: number | undefined, jetzt: number): string {
    return dauer(jetzt - (angenommenUm ?? jetzt))
}
