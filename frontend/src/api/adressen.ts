import type {Adressvorschlag} from '../modell/ort'

/**
 * Asks the address list what it suggests for a text.
 *
 * @param text what was typed
 * @param signal cancels the request when newer text replaces it
 * @returns streets, or doors once a house number is typed
 */
export async function sucheAdressen(text: string, signal: AbortSignal): Promise<Adressvorschlag[]> {
    const antwort = await fetch(`/api/adressen/suche?q=${encodeURIComponent(text)}`, {signal})
    if (!antwort.ok) return []
    return await antwort.json() as Adressvorschlag[]
}

/**
 * Asks whether the address list is there yet.
 *
 * @returns true when completion can be offered
 */
export async function adresslisteVerfuegbar(): Promise<boolean> {
    try {
        const antwort = await fetch('/api/adressen/status')
        return antwort.ok && (await antwort.json() as {verfuegbar: boolean}).verfuegbar
    } catch {
        return false
    }
}
