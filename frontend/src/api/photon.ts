import type {Ortsvorschlag} from '../modell/ort'

/** Photon's search, asked straight from the browser so its fair use is spread over the users. */
export const PHOTON_ADRESSE = 'https://photon.komoot.io/api/'

/** The box Photon searches in: Berlin, as west, south, east, north. */
export const BERLIN_BOX = '13.08,52.33,13.77,52.68'

const ORTE_HOECHSTENS = 5
const ZWISCHENSPEICHER_HOECHSTENS = 100
const zwischenspeicher = new Map<string, Ortsvorschlag[]>()

/** The part of a Photon feature this application reads. */
interface PhotonFeature {
    geometry: {coordinates: [number, number]}
    properties: {name?: string, housenumber?: string, street?: string, district?: string, locality?: string, state?: string}
}

/**
 * Asks Photon for places without a house number in Berlin, such as parks, stations and bridges.
 *
 * Addresses with a house number are left out, since the address list has those. Photon answers
 * GeoJSON, whose points are (longitude, latitude); they are turned around. The last hundred
 * answers are kept in memory for this tab, so retyping a search asks nobody.
 *
 * @param text what was typed
 * @param signal cancels the request when newer text replaces it
 * @returns the places
 */
export async function sucheOrte(text: string, signal: AbortSignal): Promise<Ortsvorschlag[]> {
    const schluessel = text.trim().toLowerCase()
    const bekannt = zwischenspeicher.get(schluessel)
    if (bekannt) return bekannt
    const parameter = new URLSearchParams({q: text, lang: 'de', limit: String(ORTE_HOECHSTENS * 2), bbox: BERLIN_BOX})
    const antwort = await fetch(`${PHOTON_ADRESSE}?${parameter}`, {signal})
    if (!antwort.ok) return []
    const daten = await antwort.json() as {features?: PhotonFeature[]}
    const orte = (daten.features ?? [])
        .filter(f => f.properties.state === 'Berlin' && !f.properties.housenumber && f.properties.name)
        .slice(0, ORTE_HOECHSTENS)
        .map(ortAus)
    merken(schluessel, orte)
    return orte
}

/**
 * Turns a Photon feature into a suggestion.
 *
 * @param feature the feature
 * @returns the suggestion
 */
function ortAus(feature: PhotonFeature): Ortsvorschlag {
    const [laenge, breite] = feature.geometry.coordinates
    const name = feature.properties.name ?? ''
    const ortsteil = feature.properties.district ?? feature.properties.locality ?? ''
    return {beschriftung: ortsteil ? `${name}, ${ortsteil}` : name, name, ortsteil, breite, laenge}
}

/**
 * Keeps an answer, dropping the oldest once the store is full.
 *
 * @param schluessel the search
 * @param orte its places
 */
function merken(schluessel: string, orte: Ortsvorschlag[]): void {
    zwischenspeicher.delete(schluessel)
    zwischenspeicher.set(schluessel, orte)
    if (zwischenspeicher.size > ZWISCHENSPEICHER_HOECHSTENS) zwischenspeicher.delete(zwischenspeicher.keys().next().value!)
}
