import {computed, getCurrentInstance, onBeforeUnmount, ref, watch, type Ref} from 'vue'

/**
 * Whether the trainer changed the pool since it was last downloaded, and a warning before leaving
 * the page while they have. The pool lives only as long as the exercise, so a download is the
 * only way to keep it. Only the trainer's own changes count, read from the server's change
 * counter: the engine drawing scenarios for calls and putting them back is no reason to download
 * again. The first count this tab sees counts as kept.
 *
 * @param stand the server's count of the trainer's changes to the pool, once known
 * @returns whether it changed, and a way to mark it as downloaded
 */
export function useExportErinnerung(stand: Ref<number | undefined>) {
    const gesichert = ref<number | null>(null)
    watch(stand, wert => {
        if (gesichert.value === null && wert !== undefined) gesichert.value = wert
    }, {immediate: true})
    const geaendert = computed(() => stand.value !== undefined && gesichert.value !== null && stand.value !== gesichert.value)

    function exportiert(): void {
        gesichert.value = stand.value ?? null
    }

    function warnen(ereignis: BeforeUnloadEvent): void {
        if (geaendert.value) ereignis.preventDefault()
    }

    window.addEventListener('beforeunload', warnen)
    if (getCurrentInstance()) onBeforeUnmount(() => window.removeEventListener('beforeunload', warnen))
    return {geaendert, exportiert}
}
