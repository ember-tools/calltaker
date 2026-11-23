import type {Ortsvorschlag} from '../modell/ort'

/**
 * Asks the server for named places matching a text: parks, stations, hospitals and the like.
 *
 * @param text what was typed
 * @param signal cancels the request when newer text replaces it
 * @returns the places, best first
 */
export async function sucheOrte(text: string, signal: AbortSignal): Promise<Ortsvorschlag[]> {
    const antwort = await fetch(`/api/orte/suche?q=${encodeURIComponent(text)}`, {signal})
    if (!antwort.ok) return []
    return await antwort.json() as Ortsvorschlag[]
}
