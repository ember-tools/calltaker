import type {Ort} from './szenario'

/** An address the address list suggests: a whole street, or one door with its point. */
export interface Adressvorschlag {
    beschriftung: string
    strasse: string
    hausnummer: string
    plz: string
    ortsteil: string
    bezirk: string
    breite?: number
    laenge?: number
}

/** A place without a house number that Photon suggests: a park, a station, a bridge. */
export interface Ortsvorschlag {
    beschriftung: string
    name: string
    ortsteil: string
    breite: number
    laenge: number
}

/** What a location form holds: the address, the point and the name of the place. */
export type Ortsangabe = Pick<Ort, 'adresse' | 'koordinaten' | 'objekt'>

/**
 * A location from an address the list suggested. A door brings its point. A street without a door
 * keeps the point only while street and postcode stay the same, since a point elsewhere in the
 * city would contradict the address. A place's name chosen before gives way to the address.
 *
 * @param vorschlag the suggestion
 * @param bisher the location so far
 * @returns the new location
 */
export function ausAdresse(vorschlag: Adressvorschlag, bisher: Ortsangabe): Ortsangabe {
    const gleicheStrasse = vorschlag.strasse === bisher.adresse.strasse && vorschlag.plz === bisher.adresse.plz
    const punkt: [number, number] | undefined = vorschlag.breite !== undefined && vorschlag.laenge !== undefined
        ? [vorschlag.breite, vorschlag.laenge]
        : gleicheStrasse ? bisher.koordinaten : undefined
    const warOrt = !bisher.adresse.strasse && Boolean(bisher.objekt) && Boolean(bisher.koordinaten)
    return {
        ...bisher,
        objekt: warOrt ? '' : bisher.objekt,
        adresse: {strasse: vorschlag.strasse, hausnummer: vorschlag.hausnummer, plz: vorschlag.plz, ortsteil: vorschlag.ortsteil},
        koordinaten: punkt,
    }
}

/**
 * A location from a place Photon suggested: no street, the place's name as the object.
 *
 * @param vorschlag the suggestion
 * @param bisher the location so far
 * @returns the new location
 */
export function ausOrt(vorschlag: Ortsvorschlag, bisher: Ortsangabe): Ortsangabe {
    return {
        ...bisher,
        adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: vorschlag.ortsteil},
        koordinaten: [vorschlag.breite, vorschlag.laenge],
        objekt: vorschlag.name,
    }
}
