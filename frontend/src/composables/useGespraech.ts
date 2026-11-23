import {getCurrentInstance, onBeforeUnmount, ref, watch, type Ref} from 'vue'
import {leereEintraege, type Eintraege} from '../modell/eintraege'
import type {AnrufSicht} from '../modell/uebung'

/** How long typing has to pause before the entries are sent. */
export const SENDEN_NACH_MS = 300

/**
 * The entries of the running conversation, kept in this view and sent to the server.
 *
 * The entries start from what the server holds when a conversation begins and are this view's
 * from then on, so a poll never overwrites what is being typed. Changes are sent after a short
 * pause in typing; `jetztSenden` sends at once, for clicks. Only one send runs at a time; what
 * changes meanwhile follows as one more send of the newest entries, so an older body never lands
 * after a newer one.
 *
 * @param anruf the call in conversation, if any
 * @param absicht sends an intent to the exercise
 * @returns the entries and a way to send them at once
 */
export function useGespraech(anruf: Ref<AnrufSicht | undefined>, absicht: (art: string, daten: Record<string, unknown>) => Promise<unknown>) {
    const eintraege = ref<Eintraege>(leereEintraege())
    let anrufId: string | undefined
    let uebernommen = ''
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    let laufend: Promise<void> | null = null
    let nochmal = false

    watch(() => anruf.value?.id, id => {
        if (id === anrufId) return
        clearTimeout(zeitgeber)
        anrufId = id
        eintraege.value = {...leereEintraege(), ...anruf.value?.eintraege}
        uebernommen = JSON.stringify(eintraege.value)
    }, {immediate: true})

    /**
     * Takes what only the server sets, its times and the handover snapshot, from its answer into
     * the entries. When nothing was typed since the send, this is no change to send; otherwise the
     * typing is sent anyway.
     *
     * @param antwort the answer to a send
     * @param gesendet the entries as sent, as JSON
     */
    function serverFelderUebernehmen(antwort: unknown, gesendet: string): void {
        const felder = antwort as {zeiten?: Eintraege['zeiten'], uebergeben?: Eintraege['uebergeben'] | null} | undefined
        if (!felder?.zeiten) return
        const unveraendert = JSON.stringify(eintraege.value) === gesendet
        const neu = {...eintraege.value, zeiten: felder.zeiten, uebergeben: felder.uebergeben ?? undefined}
        if (unveraendert) uebernommen = JSON.stringify(neu)
        eintraege.value = neu
    }

    async function senden(): Promise<void> {
        do {
            nochmal = false
            if (!anrufId) return
            const fuer = anrufId
            const gesendet = JSON.stringify(eintraege.value)
            const antwort = await absicht('eintragen', {anrufId, eintraege: eintraege.value}).catch(() => undefined)
            if (fuer === anrufId) serverFelderUebernehmen(antwort, gesendet)
        } while (nochmal)
    }

    async function jetztSenden(): Promise<void> {
        clearTimeout(zeitgeber)
        if (laufend) {
            nochmal = true
            return laufend
        }
        laufend = senden().finally(() => {
            laufend = null
        })
        return laufend
    }

    watch(eintraege, wert => {
        if (JSON.stringify(wert) === uebernommen) return
        uebernommen = ''
        clearTimeout(zeitgeber)
        zeitgeber = setTimeout(() => void jetztSenden(), SENDEN_NACH_MS)
    }, {deep: true})

    if (getCurrentInstance()) onBeforeUnmount(() => clearTimeout(zeitgeber))
    return {eintraege, jetztSenden}
}
