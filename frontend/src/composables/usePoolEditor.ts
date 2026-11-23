import {computed, ref, watch, type Ref} from 'vue'
import type {Abfragegraph} from '../modell/abfragegraph'
import {entwurfAus, leererEntwurf, type Entwurf} from '../modell/szenarioentwurf'
import type {Befund, Szenario} from '../modell/szenario'

type Absicht = (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>

/** What the pool editor shows besides the draft. */
export interface Meldungen {
    /** The engine drew the open scenario for a call; saving adds it anew. */
    gezogen: string
}

/**
 * The trainer's work on the pool: one scenario open in the editor at a time, saved, removed and
 * moved through the exercise's intents.
 *
 * The server checks every saved scenario; its refusal is shown in the editor, which stays open so
 * nothing typed is lost. A saved scenario is marked as written for the current graph. While the
 * draft has unsaved changes, no other scenario can be opened over it. When the engine draws the
 * open scenario for a call, the draft loses its id, so saving adds it as a new scenario. Refusals
 * of list actions are shown at the list, not in the editor.
 *
 * @param pool the pool as the server holds it
 * @param poolBefunde the findings per scenario
 * @param graph the question graph, once loaded
 * @param absicht sends an intent to the exercise
 * @param meldungen the texts for notices
 * @returns the draft being edited and what can be done with it
 */
export function usePoolEditor(pool: Ref<Szenario[] | undefined>, poolBefunde: Ref<Record<string, Befund[]> | undefined>, graph: Ref<Abfragegraph | null>, absicht: Absicht, meldungen: Meldungen) {
    const entwurf = ref<Entwurf | null>(null)
    const fehler = ref('')
    const hinweis = ref('')
    const listenFehler = ref('')
    const geoeffnet = ref('')
    const befunde = computed(() => (entwurf.value?.id ? poolBefunde.value?.[entwurf.value.id] ?? [] : []))
    const ungespeichert = computed(() => entwurf.value !== null && JSON.stringify(entwurf.value) !== geoeffnet.value)

    watch(pool, szenarien => {
        const id = entwurf.value?.id
        if (!id || !szenarien || szenarien.some(s => s.id === id)) return
        entwurf.value = {...entwurf.value!, id: undefined}
        hinweis.value = meldungen.gezogen
    })

    function oeffnen(neu: Entwurf): void {
        entwurf.value = neu
        geoeffnet.value = JSON.stringify(neu)
        fehler.value = ''
        hinweis.value = ''
    }

    function neu(): void {
        if (graph.value && !ungespeichert.value) oeffnen(leererEntwurf(graph.value.meta.version))
    }

    function bearbeiten(id: string): void {
        const szenario = pool.value?.find(s => s.id === id)
        if (szenario && !ungespeichert.value) oeffnen(entwurfAus(szenario))
    }

    async function speichern(): Promise<void> {
        if (!entwurf.value || !graph.value) return
        const szenario = {...entwurf.value, abfrageVersion: graph.value.meta.version}
        try {
            await absicht(szenario.id ? 'pool.ersetzen' : 'pool.hinzufuegen', {szenario})
            schliessen()
        } catch (e) {
            fehler.value = (e as Error).message
        }
    }

    async function amPool(art: string, daten: Record<string, unknown>): Promise<boolean> {
        listenFehler.value = ''
        try {
            await absicht(art, daten)
            return true
        } catch (e) {
            listenFehler.value = (e as Error).message
            return false
        }
    }

    async function entfernen(id: string): Promise<void> {
        const offen = entwurf.value?.id === id
        if (await amPool('pool.entfernen', {szenarioId: id}) && offen) schliessen()
    }

    async function verschieben(id: string, ziel: number): Promise<void> {
        await amPool('pool.verschieben', {szenarioId: id, ziel})
    }

    function schliessen(): void {
        entwurf.value = null
        fehler.value = ''
        hinweis.value = ''
    }

    return {entwurf, fehler, hinweis, listenFehler, befunde, ungespeichert, neu, bearbeiten, speichern, entfernen, verschieben, schliessen}
}
