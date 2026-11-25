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
    /** A low-quality match: the street is spelled or sounds almost like what was typed. */
    ungefaehr?: boolean
}

/** A named place without a house number, from OpenStreetMap: a park, a station, a hospital. */
export interface Ortsvorschlag {
    beschriftung: string
    name: string
    art: string
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
 * @param ortsname the name of the place picked last, which gives way like one without a street
 * @returns the new location
 */
export function ausAdresse(vorschlag: Adressvorschlag, bisher: Ortsangabe, ortsname = ''): Ortsangabe {
    const gleicheStrasse = vorschlag.strasse === bisher.adresse.strasse && vorschlag.plz === bisher.adresse.plz
    const punkt: [number, number] | undefined = vorschlag.breite !== undefined && vorschlag.laenge !== undefined
        ? [vorschlag.breite, vorschlag.laenge]
        : gleicheStrasse ? bisher.koordinaten : undefined
    const warOrt = Boolean(bisher.objekt) && (bisher.objekt === ortsname || (!bisher.adresse.strasse && Boolean(bisher.koordinaten)))
    return {
        ...bisher,
        objekt: warOrt ? '' : bisher.objekt,
        adresse: {strasse: vorschlag.strasse, hausnummer: vorschlag.hausnummer, plz: vorschlag.plz, ortsteil: vorschlag.ortsteil},
        koordinaten: punkt,
    }
}

/**
 * A location from a named place: the place's name as the object, its point, and the address of
 * the nearest door when one is known, else no street.
 *
 * @param vorschlag the suggestion
 * @param bisher the location so far
 * @param tuer the door nearest to the place
 * @returns the new location
 */
export function ausOrt(vorschlag: Ortsvorschlag, bisher: Ortsangabe, tuer?: Adressvorschlag): Ortsangabe {
    return {
        ...bisher,
        adresse: tuer
            ? {strasse: tuer.strasse, hausnummer: tuer.hausnummer, plz: tuer.plz, ortsteil: tuer.ortsteil}
            : {strasse: '', hausnummer: '', plz: '', ortsteil: vorschlag.ortsteil},
        koordinaten: [vorschlag.breite, vorschlag.laenge],
        objekt: vorschlag.name,
    }
}
