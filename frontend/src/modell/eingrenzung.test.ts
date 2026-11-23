import {describe, expect, it} from 'vitest'
import {alterAus, einenZurueck, mitAutomatik, ordnen, passtZurPerson, personAus, vonSelbst} from './eingrenzung'
import {eingrenzungsgraph} from './eingrenzung.test-hilfe'

const graph = eingrenzungsgraph()

const bis = (reaktion: string, alter?: string, geschlecht = 'mann') => [
    {knoten: 'reaktion', antwort: reaktion},
    alter === undefined ? {knoten: 'alter'} : {knoten: 'alter', wert: alter},
    {knoten: 'geschlecht', antwort: geschlecht},
]

describe('eingrenzung', () => {
    it('liest Alter und Geschlecht aus dem Pfad', () => {
        expect(personAus(graph, bis('ja', '81', 'frau'))).toEqual({alter: 81, alterUnbekannt: false, geschlecht: 'w'})
        expect(personAus(graph, bis('ja'))).toMatchObject({alter: undefined, alterUnbekannt: true})
        expect(personAus(graph, [])).toEqual({alter: undefined, alterUnbekannt: false, geschlecht: undefined})
    })

    it('stellt nach der Lage passende Beschwerden vorn an, den Rest unter weitere', () => {
        const ordnung = ordnen(graph, 'beschwerde', bis('nicht', '40'))
        expect(ordnung.vorn.map(a => a.id)).toEqual(['bewusstlos', 'krampf'])
        expect(ordnung.weitere.map(a => a.id)).toEqual(['bauch'])
        expect(ordnen(graph, 'beschwerde', bis('ja', '40')).vorn.map(a => a.id)).toEqual(['bauch', 'krampf', 'bewusstlos'])
    })

    it('rückt Antworten, die nicht zur Person passen, nach hinten', () => {
        const ordnung = ordnen(graph, 'altersfrage', bis('ja', '40', 'mann'))
        expect(ordnung.vorn.map(a => a.id)).toEqual(['erwachsen'])
        expect(ordnung.weitere.map(a => a.id)).toEqual(['unbekannt', 'kind', 'frauen'])
        expect(passtZurPerson({id: 'f', label: '', ziel: '', geschlecht: 'w'}, {alterUnbekannt: false})).toBe(true)
    })

    it('beantwortet eine Frage selbst, wenn die Person nur eine Antwort lässt', () => {
        expect(vonSelbst(graph, 'altersfrage', bis('ja', '81'))).toBe('erwachsen')
        expect(vonSelbst(graph, 'altersfrage', bis('ja', '7'))).toBe('kind')
        expect(vonSelbst(graph, 'altersfrage', bis('ja'))).toBe('unbekannt')
        expect(vonSelbst(graph, 'altersfrage', bis('ja', '30', 'frau'))).toBeUndefined()
        expect(vonSelbst(graph, 'beschwerde', bis('ja', '30'))).toBeUndefined()
    })
})

describe('eingrenzung im Pfad', () => {
    it('geht selbst beantwortete Fragen mit und beim Zurückgehen mit zurück', () => {
        const pfad = mitAutomatik(graph, [...bis('ja', '81'), {knoten: 'beschwerde', antwort: 'bauch'}])
        expect(pfad.at(-1)).toEqual({knoten: 'altersfrage', antwort: 'erwachsen', automatisch: true})
        expect(einenZurueck(pfad)).toEqual(bis('ja', '81'))
        expect(einenZurueck(bis('ja', '81'))).toEqual(bis('ja', '81').slice(0, 2))
    })
})

describe('eingrenzung bei getipptem Alter', () => {
    it('liest Zahlen aus freiem Text und hält Babys für null Jahre alt', () => {
        expect(alterAus('ungefähr 60')).toBe(60)
        expect(alterAus('ca. 60 Jahre')).toBe(60)
        expect(alterAus('3 Wochen')).toBe(0)
        expect(alterAus('6 Monate')).toBe(0)
        expect(alterAus('weiß nicht')).toBeUndefined()
        expect(alterAus('60, seit gestern Nachmittag')).toBe(60)
    })

    it('hält nur ein leeres Alter für unbekannt', () => {
        expect(personAus(graph, bis('ja', 'weiß nicht'))).toMatchObject({alter: undefined, alterUnbekannt: false})
        expect(vonSelbst(graph, 'altersfrage', bis('ja', 'weiß nicht'))).toBeUndefined()
        expect(vonSelbst(graph, 'altersfrage', bis('ja', 'ungefähr 60'))).toBe('erwachsen')
        expect(vonSelbst(graph, 'altersfrage', bis('ja', '3 Wochen'))).toBe('kind')
    })

    it('lässt ein Unbekannt-Alter zu, solange nach dem Alter nicht gefragt wurde', () => {
        expect(passtZurPerson({id: 'u', label: '', ziel: '', alter: {unbekannt: true}}, {alterUnbekannt: false})).toBe(true)
    })
})
