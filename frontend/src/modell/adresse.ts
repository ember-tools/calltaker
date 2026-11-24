import type {Adresse} from './szenario'

/**
 * An address as one line.
 *
 * @param adresse the address
 * @returns street and number, postcode and Ortsteil
 */
export function zeile(adresse: Adresse): string {
    const strasse = `${adresse.strasse} ${adresse.hausnummer}`.trim()
    return [strasse, `${adresse.plz} ${adresse.ortsteil}`.trim()].filter(Boolean).join(', ')
}
