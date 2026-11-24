/** The box around Berlin the tile proxy serves, as [[south, west], [north, east]]. */
export const BERLIN_GRENZEN: [[number, number], [number, number]] = [[52.25, 12.9], [52.8, 13.95]]

/** Where the map opens when it has nothing to show: Berlin's centre. */
export const BERLIN_MITTE: [number, number] = [52.52, 13.405]

/** The zoom levels the tile proxy serves. */
export const ZOOM_MIN = 10
export const ZOOM_MAX = 18

/** Where the tiles come from: the backend's cache of OpenStreetMap. */
export const KACHEL_ADRESSE = '/kacheln/{z}/{x}/{y}.png'

/** The area a mobile cell covers: its centre (latitude, longitude) and radius in metres. */
export interface Funkzelle {
    mitte: [number, number]
    radius: number
}

/** A point on the map: where it is, and whether it is what was entered or the truth. */
export interface Kartenpunkt {
    breite: number
    laenge: number
    art: 'erfasst' | 'wahrheit'
}

/**
 * The straight-line distance between two points in metres, by the haversine formula.
 *
 * @param a one point as (latitude, longitude)
 * @param b the other
 * @returns the distance in metres
 */
export function abstandMeter(a: [number, number], b: [number, number]): number {
    const rad = (grad: number) => grad * Math.PI / 180
    const dBreite = rad(b[0] - a[0])
    const dLaenge = rad(b[1] - a[1])
    const h = Math.sin(dBreite / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLaenge / 2) ** 2
    return 2 * 6_371_000 * Math.asin(Math.sqrt(h))
}

/**
 * The distance between two points in whole metres.
 *
 * @param a one point as (latitude, longitude)
 * @param b the other
 * @returns the rounded distance
 */
export function abstandGerundet(a: [number, number], b: [number, number]): number {
    return Math.round(abstandMeter(a, b))
}
