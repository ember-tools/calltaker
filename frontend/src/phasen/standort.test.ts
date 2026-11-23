import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import type {Szenario} from '../modell/szenario'
import {leererEntwurf} from '../modell/szenarioentwurf'
import {testgraph} from '../modell/testgraph.test-hilfe'
import {standort} from './standort'

describe('standort mit Warntafel', () => {
    it('vergleicht die UN-Nummer, wenn die Wahrheit eine Tafel hat', () => {
        const szenario = {...leererEntwurf(1), ort: {...leererEntwurf(1).ort, gefahrgut: {un: '1203', gefahrenzahl: '33'}}} as Szenario
        const eintraege = leereEintraege()
        const zeile = () => standort.bewerten(eintraege, szenario, testgraph()).find(b => b.feld === 'bewertung.gefahrgut')
        expect(zeile()?.urteil).toBe('offen')
        eintraege.ort.gefahrgut = {un: '1203', gefahrenzahl: '33'}
        expect(zeile()?.urteil).toBe('richtig')
        eintraege.ort.gefahrgut = {un: '1202', gefahrenzahl: '30'}
        expect(zeile()?.urteil).toBe('falsch')
    })
})
