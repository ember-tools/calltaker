import type {Abfragegraph} from '../modell/abfragegraph'

/**
 * Loads the question graph from the server.
 *
 * @returns the graph with its code index
 */
export async function ladeAbfrage(): Promise<Abfragegraph> {
    const antwort = await fetch('/api/abfrage')
    if (!antwort.ok) throw new Error(`Abfragegraph nicht ladbar: HTTP ${antwort.status}`)
    return await antwort.json() as Abfragegraph
}
