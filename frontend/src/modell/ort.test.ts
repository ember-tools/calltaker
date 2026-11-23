import {describe, expect, it} from 'vitest'
import {ausAdresse, ausOrt, type Ortsangabe} from './ort'

const leer: Ortsangabe = {adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: ''}, objekt: 'Treppenhaus'}

describe('ort', () => {
    it('übernimmt eine Tür mit Punkt und behält das Objekt', () => {
        const neu = ausAdresse({beschriftung: '', strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau', breite: 52.56, laenge: 13.21}, leer)
        expect(neu).toEqual({adresse: {strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde'}, koordinaten: [52.56, 13.21], objekt: 'Treppenhaus'})
    })

    it('behält den Punkt, wenn dieselbe Straße ohne Hausnummer gewählt wird', () => {
        const mitPunkt: Ortsangabe = {adresse: {strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde'}, koordinaten: [52.5, 13.4], objekt: ''}
        expect(ausAdresse({beschriftung: '', strasse: 'Werderstraße', hausnummer: '', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau'}, mitPunkt).koordinaten).toEqual([52.5, 13.4])
    })

    it('macht aus einem Ort das Objekt, ohne Straße', () => {
        const neu = ausOrt({beschriftung: '', name: 'Tempelhofer Feld', ortsteil: 'Tempelhof', breite: 52.47, laenge: 13.4}, leer)
        expect(neu.objekt).toBe('Tempelhofer Feld')
        expect(neu.adresse.strasse).toBe('')
        expect(neu.koordinaten).toEqual([52.47, 13.4])
    })
})

describe('ort beim Wechsel', () => {
    const punkt: [number, number] = [52.48, 13.44]
    const neukoelln: Ortsangabe = {adresse: {strasse: 'Karl-Marx-Straße', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln'}, koordinaten: punkt, objekt: ''}

    it('verwirft den Punkt, wenn eine andere Straße gewählt wird', () => {
        const neu = ausAdresse({beschriftung: '', strasse: 'Werderstraße', hausnummer: '', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau'}, neukoelln)
        expect(neu.koordinaten).toBeUndefined()
    })

    it('ersetzt den Namen eines Ortes durch die gewählte Adresse', () => {
        const feld = ausOrt({beschriftung: '', name: 'Tempelhofer Feld', ortsteil: 'Tempelhof', breite: 52.47, laenge: 13.4}, neukoelln)
        const danach = ausAdresse({beschriftung: '', strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde', bezirk: 'Spandau', breite: 52.56, laenge: 13.21}, feld)
        expect(danach.objekt).toBe('')
    })
})
