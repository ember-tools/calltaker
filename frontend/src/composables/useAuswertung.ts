import {computed, type Ref} from 'vue'
import type {Rolle, ZustandFuer} from '../modell/uebung'
import {sichtVon} from '../modell/uebung'
import type {Ausgewertet} from '../phasen/uebersicht'

/**
 * The ended calls of an exercise with their truth, whichever role looks at them: the trainer has
 * the truth of every call, the trainee gets it with each call that ended.
 *
 * @param zustand the exercise as the role sees it
 * @param rolle the role
 * @returns the ended calls with their truth, in order, and every call the role sees
 */
export function useAuswertung(zustand: Ref<ZustandFuer<Rolle> | null>, rolle: Rolle) {
    const anrufe = computed(() => zustand.value?.anrufe ?? [])
    const ausgewertet = computed<Ausgewertet[]>(() => {
        if (!zustand.value) return []
        const ziele = zustand.value.engine.ziele
        if (rolle === 'ausbilder') {
            return (zustand.value as ZustandFuer<'ausbilder'>).anrufe
                .filter(a => a.zustand === 'beendet')
                .map(a => ({anruf: sichtVon(a), szenario: a.szenario, ziele}))
        }
        return (zustand.value as ZustandFuer<'trainee'>).anrufe
            .filter(a => a.zustand === 'beendet' && a.szenario)
            .map(a => ({anruf: a, szenario: a.szenario!, ziele}))
    })
    return {anrufe, ausgewertet}
}
