import type {Gefahrstoffliste} from '../modell/gefahrstoffe'

/**
 * Loads the hazardous goods by UN number from the server.
 *
 * @returns the list with where it comes from
 */
export async function ladeGefahrstoffe(): Promise<Gefahrstoffliste> {
    const antwort = await fetch('/api/gefahrstoffe')
    if (!antwort.ok) throw new Error(`Gefahrstoffliste nicht ladbar: HTTP ${antwort.status}`)
    return await antwort.json() as Gefahrstoffliste
}
