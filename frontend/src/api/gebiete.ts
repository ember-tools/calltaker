import type {Adressvorschlag} from '../modell/ort'

/** Where random addresses are drawn from: a Bezirk, an Ortsteil, or all of Berlin when both are empty. */
export interface Gebiet {
    bezirk: string
    ortsteil: string
}

/**
 * Asks for a random door from the address list.
 *
 * @param gebiet where to draw it from
 * @returns the address with its point, or undefined when the list has none there
 * @throws {TypeError} when the server cannot be reached
 */
export async function zufallsAdresse(gebiet: Gebiet): Promise<Adressvorschlag | undefined> {
    const parameter = new URLSearchParams({bezirk: gebiet.bezirk, ortsteil: gebiet.ortsteil})
    const antwort = await fetch(`/api/adressen/zufall?${parameter}`)
    return antwort.ok ? await antwort.json() as Adressvorschlag : undefined
}

/**
 * Asks for the Bezirke and their Ortsteile.
 *
 * @returns the Ortsteile by Bezirk, empty before the address list is loaded
 */
export async function ladeGebiete(): Promise<Record<string, string[]>> {
    try {
        const antwort = await fetch('/api/adressen/gebiete')
        return antwort.ok ? await antwort.json() as Record<string, string[]> : {}
    } catch {
        return {}
    }
}
