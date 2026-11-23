import {computed, shallowRef} from 'vue'
import {ladeAbfrage} from '../api/abfrage'
import type {Abfragegraph} from '../modell/abfragegraph'
import {schwersteErreichbare} from '../modell/abfrageweg'

/** The graph, loaded once per tab and shared by every view that asks for it. */
const geladen = shallowRef<Abfragegraph | null>(null)
let laden: Promise<Abfragegraph> | null = null

/**
 * The question graph and, worked out once, the most urgent endpoint reachable from each node.
 *
 * @returns the graph once loaded, the endpoints per node, and whether loading failed
 */
export function useAbfragegraph() {
    const fehler = shallowRef<string | null>(null)
    laden ??= ladeAbfrage()
    laden.then(graph => {
        geladen.value = graph
    }).catch((e: Error) => {
        laden = null
        fehler.value = e.message
    })
    const schwerste = computed(() => (geladen.value ? schwersteErreichbare(geladen.value) : new Map()))
    return {graph: geladen, schwerste, fehler}
}
