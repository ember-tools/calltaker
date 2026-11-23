import type {Rolle} from '../modell/uebung'

/** A request the server refused, with its reason in German. */
export class Abgelehnt extends Error {
    readonly status: number

    /**
     * @param status the HTTP status
     * @param grund the server's reason
     */
    constructor(status: number, grund: string) {
        super(grund)
        this.status = status
    }
}

/** The reason given when the server cannot be reached at all. */
export const NICHT_ERREICHBAR = 'Der Server ist nicht erreichbar.'

/**
 * Sends a request, turning a network failure into a refusal with a German reason.
 *
 * @param adresse the address
 * @param optionen the request options
 * @returns the response
 */
async function senden(adresse: string, optionen?: RequestInit): Promise<Response> {
    try {
        return await fetch(adresse, optionen)
    } catch {
        throw new Abgelehnt(0, NICHT_ERREICHBAR)
    }
}

/** A state with the version it belongs to. */
export interface Stand<T> {
    version: number
    zustand: T
}

/**
 * Throws the server's German reason for a refused request.
 *
 * @param antwort the response
 */
async function pruefe(antwort: Response): Promise<void> {
    if (antwort.ok) return
    const inhalt = await antwort.json().catch(() => ({})) as {detail?: unknown}
    throw new Abgelehnt(antwort.status, typeof inhalt.detail === 'string' ? inhalt.detail : `HTTP ${antwort.status}`)
}

/**
 * Creates an exercise.
 *
 * @returns its two codes
 */
export async function anlegen(): Promise<{ausbilderCode: string, traineeCode: string}> {
    const antwort = await senden('/api/uebung', {method: 'POST'})
    await pruefe(antwort)
    return await antwort.json() as {ausbilderCode: string, traineeCode: string}
}

/**
 * Asks which role a code stands for.
 *
 * @param code the code
 * @returns the role
 */
export async function rolleVon(code: string): Promise<Rolle> {
    const antwort = await senden(`/api/uebung/${encodeURIComponent(code)}`)
    await pruefe(antwort)
    return (await antwort.json() as {rolle: Rolle}).rolle
}

/**
 * Polls the state of an exercise.
 *
 * @param code the code, which decides what is seen
 * @param version the version already held
 * @returns the new state, or null when nothing changed
 */
export async function holeZustand<T>(code: string, version: number): Promise<Stand<T> | null> {
    const antwort = await senden(`/api/uebung/${encodeURIComponent(code)}/zustand?version=${version}`)
    await pruefe(antwort)
    if (antwort.status === 204) return null
    return await antwort.json() as Stand<T>
}

/**
 * Sends an intent to an exercise.
 *
 * @param code the code, which decides what is allowed
 * @param art what is wanted
 * @param daten the data it needs
 * @returns the result and the state's new version
 */
export async function sendeAbsicht(code: string, art: string, daten: Record<string, unknown> = {}): Promise<{version: number, ergebnis: Record<string, unknown>}> {
    const antwort = await senden(`/api/uebung/${encodeURIComponent(code)}/absicht`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({art, ...daten}),
    })
    await pruefe(antwort)
    return await antwort.json() as {version: number, ergebnis: Record<string, unknown>}
}
