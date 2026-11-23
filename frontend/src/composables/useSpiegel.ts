import {getCurrentInstance, onBeforeUnmount, watch, type Ref} from 'vue'

/** How long typing has to pause before it is mirrored to the trainer. */
export const SPIEGELN_NACH_MS = 300

/**
 * Mirrors what the trainee types or opens but has not entered yet, such as the address search,
 * the age being typed or an open cancellation, so the trainer sees it while it happens.
 *
 * @param felder the typed texts by name
 * @param absicht sends an intent to the exercise
 */
export function useSpiegel(felder: Ref<Record<string, unknown>>, absicht: (art: string, daten: Record<string, unknown>) => Promise<unknown>): void {
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    watch(felder, wert => {
        clearTimeout(zeitgeber)
        zeitgeber = setTimeout(() => void absicht('spiegeln', {felder: wert}).catch(() => undefined), SPIEGELN_NACH_MS)
    }, {deep: true})
    if (getCurrentInstance()) onBeforeUnmount(() => clearTimeout(zeitgeber))
}
