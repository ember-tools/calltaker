import {computed, ref} from 'vue'
import {beispielAnruf, beispielEintraege, beispielReanimation, beispielSchlange, beispielWahrheit} from '../modell/hilfebeispiele'
import {phasenstand} from '../phasen/register'
import {useAbfragegraph} from './useAbfragegraph'

/**
 * The made-up call, queue and entries the help pages show in their replicas of the interface, built
 * once per page from the query graph.
 *
 * @returns the examples; those that need the graph are undefined until it has loaded
 */
export function useHelpExamples() {
    const {graph, schwerste} = useAbfragegraph()
    const now = Date.now() / 1000
    const queue = beispielSchlange(now)
    const call = beispielAnruf(now)
    const entries = computed(() => (graph.value ? beispielEintraege(graph.value) : undefined))
    const resuscitation = ref(beispielReanimation(now))
    const plate = ref({un: '1203', gefahrenzahl: '33'})
    const truth = computed(() => (graph.value ? beispielWahrheit(graph.value, now) : undefined))
    const phases = computed(() => (graph.value && entries.value ? phasenstand(entries.value, {graph: graph.value, anruf: call}) : []))
    const activePhase = computed(() => phases.value.find(stand => stand.fehlend.length > 0)?.phase.id ?? '')
    return {graph, schwerste, now, queue, call, entries, resuscitation, plate, truth, phases, activePhase}
}
