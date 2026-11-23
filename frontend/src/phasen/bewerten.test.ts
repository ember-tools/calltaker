import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import {leererEntwurf} from '../modell/szenarioentwurf'
import type {Szenario} from '../modell/szenario'
import {testgraph} from '../modell/testgraph.test-hilfe'
import {bewerten} from './register'

const graph = testgraph()
const szenario: Szenario = {
    ...leererEntwurf(1), id: 's', titel: 'Sturz',
    ort: {adresse: {strasse: 'Karl-Marx-Straße', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln'}, koordinaten: [52.4793, 13.4385], objekt: '', geschoss: '2. OG', klingel: '', anfahrt: '', gefahren: ''},
    anrufer: {name: 'Ayşe Yılmaz', rufnummerUnterdrueckt: false, rufnummer: '491761234567', rueckrufnummer: '493012345678'},
    ziel: {knoten: 'p.e2', code: '17D01'},
}

/**
 * The comparisons of all phases as one list of field and verdict.
 *
 * @param eintraege the entries
 * @returns field and verdict per comparison
 */
function urteile(eintraege = leereEintraege()) {
    return bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen.map(b => [b.feld, b.urteil, b.abstand]))
}

describe('bewerten', () => {
    it('lässt Leeres offen', () => {
        expect(urteile().every(([, urteil]) => urteil === 'offen')).toBe(true)
    })

    it('erkennt Richtiges bei anderer Schreibweise und nahem Punkt', () => {
        const eintraege = leereEintraege()
        eintraege.ort = {...eintraege.ort, adresse: {strasse: 'Karl-Marx-Str.', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln'}, koordinaten: [52.4795, 13.4386], geschoss: '2.OG'}
        eintraege.anrufer = {name: 'Frau Yılmaz', rufnummerBestaetigt: false, rueckrufnummer: '030 12345678'}
        eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e2', code: '17D01'}}
        expect(urteile(eintraege)).toEqual([
            ['bewertung.adresse', 'richtig', undefined],
            ['bewertung.punkt', 'richtig', 23],
            ['bewertung.geschoss', 'richtig', undefined],
            ['bewertung.code', 'richtig', undefined],
            ['bewertung.name', 'richtig', undefined],
            ['bewertung.rueckrufnummer', 'richtig', undefined],
        ])
    })

    it('erkennt die bestätigte angezeigte Nummer als falsch, wenn der Anrufer anders erreichbar ist', () => {
        const eintraege = leereEintraege()
        eintraege.ort.koordinaten = [52.49, 13.44]
        eintraege.anrufer = {name: 'Müller', rufnummerBestaetigt: true, rueckrufnummer: '491761234567'}
        eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e1', code: '17A01'}}
        const liste = urteile(eintraege)
        expect(liste.find(([feld]) => feld === 'bewertung.rueckrufnummer')![1]).toBe('falsch')
        expect(liste.find(([feld]) => feld === 'bewertung.name')![1]).toBe('falsch')
        expect(liste.find(([feld]) => feld === 'bewertung.code')![1]).toBe('falsch')
        expect(liste.find(([feld]) => feld === 'bewertung.punkt')![1]).toBe('falsch')
    })
})

describe('bewerten in Sonderfällen', () => {
    it('vergleicht einen Ort ohne Straße über das Objekt und lässt leere Wahrheiten weg', () => {
        const amPlatz: Szenario = {...szenario, ort: {...szenario.ort, adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: 'Tempelhof'}, objekt: 'Tempelhofer Feld', geschoss: ''}, anrufer: {...szenario.anrufer, name: ''}}
        const eintraege = leereEintraege()
        eintraege.ort.objekt = 'Tempelhofer Feld, Eingang Oderstraße'
        eintraege.anrufer.name = 'Irgendwer'
        const felder = bewerten(eintraege, amPlatz, graph).flatMap(p => p.bewertungen.map(b => [b.feld, b.urteil]))
        expect(felder).toContainEqual(['bewertung.objekt', 'richtig'])
        expect(felder.map(([feld]) => feld)).not.toContain('bewertung.name')
        expect(felder.map(([feld]) => feld)).not.toContain('bewertung.geschoss')
        const ohneObjekt = bewerten(eintraege, {...amPlatz, ort: {...amPlatz.ort, objekt: ''}}, graph).flatMap(p => p.bewertungen.map(b => b.feld))
        expect(ohneObjekt).not.toContain('bewertung.objekt')
    })

    it('nimmt das Ergebnis eines Abbruchs als Code', () => {
        const eintraege = leereEintraege()
        eintraege.abfrage = {pfad: [], abbruch: {grund: 'aufgelegt', ergebnis: {knoten: 'p.e2', code: '17D01'}}}
        const code = bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen).find(b => b.feld === 'bewertung.code')!
        expect(code).toMatchObject({urteil: 'richtig', ist: '17D01 · RD2NC.'})
    })
})
