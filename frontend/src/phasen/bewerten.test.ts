import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import {leererEntwurf} from '../modell/szenarioentwurf'
import type {Szenario} from '../modell/szenario'
import {testgraph} from '../modell/testgraph.test-hilfe'
import {codestufe} from './abfrage'
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
        expect(liste.find(([feld]) => feld === 'bewertung.code')![1]).toBe('teilweise')
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

describe('codestufe', () => {
    it('stuft Codes: exakt, gleiches Protokoll, gleiche Kategorie, falsch', () => {
        const soll = {knoten: 'p.e2', code: '17D01'}
        const ergebnis = (knoten: string, code: string, kategorie: string) => ({knoten, code, kategorie, stichwort: kategorie})
        expect(codestufe(graph, soll, ergebnis('p.e2', '17D01', 'RD2NC.'))).toBe('exakt')
        expect(codestufe(graph, soll, ergebnis('p.e1', '17A01', 'RD4C.'))).toBe('protokoll')
        expect(codestufe(graph, soll, ergebnis('x', '06D01', 'RD2NC.'))).toBe('kategorie')
        expect(codestufe(graph, soll, ergebnis('x', '17X99', 'RD3B.'))).toBe('falsch')
        expect(codestufe(graph, soll, ergebnis('x', '06D01', 'RD3B.'))).toBe('falsch')
        expect(codestufe(graph, {knoten: 'fw.e', code: '67B01'}, ergebnis('y', '99X', 'Aufwertung entfällt.'))).toBe('falsch')
    })


    it('lässt die Kategorie-Stufe weg, wenn ein Code keine verwertbare Kategorie hat', () => {
        const ohne = testgraph()
        ohne.knoten['p.e2'] = {...ohne.knoten['p.e2']!, kategorie: 'Aufwertung entfällt.'}
        ohne.knoten['fw.e'] = {...ohne.knoten['fw.e']!, kategorie: ''}
        const ergebnis = (knoten: string, code: string, kategorie: string) => ({knoten, code, kategorie, stichwort: kategorie})
        expect(codestufe(ohne, {knoten: 'p.e2', code: '17D01'}, ergebnis('x', '06D01', 'Aufwertung entfällt.'))).toBe('falsch')
        expect(codestufe(ohne, {knoten: 'fw.e', code: '67B01'}, ergebnis('y', '06D01', ''))).toBe('falsch')
    })

    it('liest das Protokoll aus dem Code-Index, nicht aus den Ziffern', () => {
        const ergebnis = (knoten: string, code: string) => ({knoten, code, kategorie: 'BRAND 9', stichwort: ''})
        expect(codestufe(graph, {knoten: 'fw.e', code: '67B01'}, ergebnis('fremd', '67A01'))).toBe('falsch')
    })
})

describe('bewerten nach Aufwertung und Abbruch', () => {
    it('nennt den Code vor der Aufwertung und den Grund des Abbruchs', () => {
        const eintraege = leereEintraege()
        eintraege.abfrage = {pfad: [{knoten: 'fachrichtung', antwort: 'rd'}, {knoten: 'hand', antwort: 'eins'}, {knoten: 'rd.alter', wert: '81'}, {knoten: 'rd.wahl', antwort: 'sturz'}, {knoten: 'p.k0', antwort: 'leicht'}], aufwertung: {knoten: 'p.e2', code: '17D01'}}
        const auf = bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen)
        expect(auf.find(b => b.feld === 'bewertung.codeVorAufwertung')).toMatchObject({ist: '17A01 · RD4C.', urteil: 'hinweis'})
        eintraege.abfrage = {pfad: [], abbruch: {grund: 'Anrufer legt auf', ergebnis: {knoten: 'p.e1', code: '17A01'}}}
        const ab = bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen)
        expect(ab.find(b => b.feld === 'bewertung.abbruch')).toMatchObject({ist: 'Anrufer legt auf', urteil: 'hinweis'})
        eintraege.abfrage = {pfad: [], abbruch: {grund: 'vor dem Protokoll aufgelegt'}}
        const frueh = bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen)
        expect(frueh.find(b => b.feld === 'bewertung.code')!.urteil).toBe('offen')
        expect(frueh.find(b => b.feld === 'bewertung.abbruch')!.ist).toBe('vor dem Protokoll aufgelegt')
        eintraege.abfrage = {pfad: [], aufwertung: {knoten: 'p.e2', code: '17D01'}}
        expect(bewerten(eintraege, szenario, graph).flatMap(p => p.bewertungen).map(b => b.feld)).not.toContain('bewertung.codeVorAufwertung')
    })
})

describe('codestufe bei Kreislaufstillstand', () => {
    it('zählt 09E01 als exakt, wenn die Wahrheit ein Stillstand eines anderen Protokolls ist', () => {
        const rea = testgraph()
        rea.knoten['p.e3'] = {...rea.knoten['p.e3']!, kategorie: 'RD1NC REA.'}
        const stillstand = {knoten: 'x', code: '09E01', kategorie: 'RD1NC REA.', stichwort: ''}
        expect(codestufe(rea, {knoten: 'p.e3', code: '17E01'}, stillstand)).toBe('exakt')
        expect(codestufe(rea, {knoten: 'p.e2', code: '17D01'}, stillstand)).not.toBe('exakt')
        expect(codestufe(rea, {knoten: 'p.e3', code: '09E04'}, {...stillstand, code: '09E03'})).not.toBe('exakt')
    })
})
