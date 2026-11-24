import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from './ausbilder.test-hilfe'
import {i18n} from '../i18n'
import {lageText, leitfaden, werDuBist} from './leitfaden'

describe('leitfaden', () => {
    it('baut Stichpunkte aus dem Szenario, in Sprechreihenfolge', () => {
        const szenario = anrufMit('l').szenario
        szenario.antworten = {...szenario.antworten, 'eroeffnung.hand': {antwort: '3-hand-der-anrufer-meldet-fuer-andere'}, 'eroeffnung.vor-ort': {antwort: 'nein-war-nicht-vor-ort'}}
        szenario.betroffener = {name: 'Aylin Kaya'}
        szenario.ort.haustier = 'ein Hund'
        const punkte = leitfaden(GRAPH, szenario)
        expect(punkte.map(p => p.schluessel)).toEqual(['leitfaden.ort', 'leitfaden.lage', 'leitfaden.name', 'leitfaden.wer.nieOhne', 'leitfaden.notizen', 'leitfaden.wohnung', 'leitfaden.haustier', 'leitfaden.betroffen', 'leitfaden.rueckruf', 'leitfaden.stimmung.panisch'])
        expect(punkte[0]!.werte?.ort).toBe('Werderstraße 20, 13587 Hakenfelde')
        expect(punkte[1]!.werte).toEqual({anlass: 'Sturz: Schwer'})
        expect(punkte[2]!.werte).toEqual({name: 'Mehmet Kaya'})
        expect(punkte[5]!.werte).toEqual({geschoss: '2. OG', klingel: 'Kaya'})
        expect(punkte[7]!.werte?.person).toBe('Aylin Kaya, 81 Jahre')
        expect(punkte[4]!.werte).toEqual({notizen: 'Weint.'})
    })

    it('sagt in genau einem Satz, wer der Anrufer ist, mit der Beziehung', () => {
        const faelle: [string, string, string][] = [
            ['1-hand-der-anrufer-ist-selbst-betroffen', 'ja-der-anrufer-ist-vor-ort', 'leitfaden.wer.selbst'],
            ['2-hand-der-anrufer-ist-beim-betroffenen', 'ja-der-anrufer-ist-vor-ort', 'leitfaden.wer.dabeiRd'],
            ['3-hand-der-anrufer-meldet-fuer-andere', 'nein-war-nicht-vor-ort', 'leitfaden.wer.nie'],
            ['3-hand-der-anrufer-meldet-fuer-andere', 'nein-nicht-mehr-vor-ort', 'leitfaden.wer.nichtMehr'],
            ['4-hand-der-anrufer-hat-es-nur-gehoert', 'nein-war-nicht-vor-ort', 'leitfaden.wer.gehoert'],
            ['3-hand-der-anrufer-meldet-fuer-andere', 'unbekannt', 'leitfaden.wer.unbekannt'],
            ['4-hand-der-anrufer-hat-es-nur-gehoert', 'unbekannt', 'leitfaden.wer.unbekannt'],
            ['automatische-meldung', 'nein-war-nicht-vor-ort', 'leitfaden.wer.automatisch'],
        ]
        for (const [hand, vorOrt, schluessel] of faelle) {
            const szenario = anrufMit('w').szenario
            szenario.anrufer = {...szenario.anrufer, beziehung: 'Tochter'}
            szenario.antworten = {...szenario.antworten, 'eroeffnung.hand': {antwort: hand}, 'eroeffnung.vor-ort': {antwort: vorOrt}}
            const wer = leitfaden(GRAPH, szenario).filter(p => p.schluessel.startsWith('leitfaden.wer.'))
            expect(wer.map(p => p.schluessel)).toEqual([schluessel])
            if (wer[0]!.werte) expect(wer[0]!.werte).toEqual({beziehung: 'Tochter'})
        }
        expect(werDuBist({...anrufMit('w').szenario, antworten: {'eroeffnung.hand': {antwort: '2-hand-der-anrufer-ist-beim-betroffenen'}}}, false))
            .toEqual({schluessel: 'leitfaden.wer.dabeiFwOhne'})
        expect(werDuBist({...anrufMit('w').szenario, antworten: {'eroeffnung.vor-ort': {antwort: 'ja-der-anrufer-ist-vor-ort'}}}, true))
            .toEqual({schluessel: 'leitfaden.wer.vorOrt'})
        expect(i18n.global.t('leitfaden.wer.dabeiRd', {beziehung: 'Tochter'})).toContain('Tochter')
    })

    it('nennt Todeszeichen, geschätztes Alter, Kohlenmonoxid und Atemnot als eigene Punkte', () => {
        const labels = (...pfad: string[]) => {
            const texte = ['Protokoll', ...pfad]
            return {
            ...GRAPH,
            knoten: {...GRAPH.knoten, 'x.k': {frage: 'x?', antworten: texte.map((label, i) => ({id: `a${i}`, label, ziel: 'x.e'}))}, 'x.e': {anlass: 'Unzweifelhaft tote Person', kategorie: 'RD', code: '09B01c'}},
            endpunkte: [...GRAPH.endpunkte, {knoten: 'x.e', code: '09B01c', anlass: '', kategorie: 'RD', stichwort: '', fachrichtung: 'rd', protokoll: 'rd.09', pfad: texte.map((_, i) => ({knoten: 'x.k', antwort: `a${i}`}))}],
            } as typeof GRAPH
        }
        const schluessel = (graph: typeof GRAPH, code: string, hand = '2-hand-der-anrufer-ist-beim-betroffenen', alter = '70') => {
            const szenario = anrufMit('o').szenario
            szenario.ziel = {knoten: 'x.e', code}
            szenario.antworten = {...szenario.antworten, 'eroeffnung.hand': {antwort: hand}, 'eroeffnung.vor-ort': {antwort: 'ja-der-anrufer-ist-vor-ort'}, 'rd.alter': {wert: alter}}
            return leitfaden(graph, szenario).map(p => p.schluessel)
        }
        expect(schluessel(labels('bei Patientenalter älter 12 Jahre, Verwesung'), '09B01c')).toContain('leitfaden.todeszeichen.verwesung')
        expect(schluessel(labels('Kalt und steif'), '09B01a')).toContain('leitfaden.todeszeichen.kalt')
        expect(schluessel(labels('Sturz'), '17A01')).not.toContain('leitfaden.todeszeichen.kalt')
        expect(schluessel(labels('Sturz'), '17A01', undefined, 'etwa 60')).toContain('leitfaden.geschaetzt')
        expect(schluessel(labels('Kohlenmonoxid'), '08C01')).toContain('leitfaden.kohlenmonoxid')
        expect(schluessel(labels('Kohlenmonoxid-Alarm (automatischer Alarm)'), '08O01')).not.toContain('leitfaden.kohlenmonoxid')
        expect(schluessel(labels('Kohlenmonoxid-Alarm (Personen ohne Notfallleitsymptome vor Ort)'), '08O02')).not.toContain('leitfaden.kohlenmonoxid')
        const gas = {...labels('Chemikalien'), knoten: {...labels('Chemikalien').knoten}}
        gas.knoten['x.k'] = {frage: 'x?', antworten: [{id: 'a0', label: 'Kohlenmonoxid / Inhalation / Gefahrgut / CBRN', ziel: 'x.e'}, {id: 'a1', label: 'Chemikalien', ziel: 'x.e'}]}
        expect(schluessel(gas, '08B01')).not.toContain('leitfaden.kohlenmonoxid')
        expect(schluessel(labels('Schwerste, mit dem Leben nicht zu vereinbarende Verletzungen'), '09B01f')).toContain('leitfaden.todeszeichen.verletzungen')
        expect(schluessel(labels('Kohlenmonoxid'), '08C01', '3-hand-der-anrufer-meldet-fuer-andere')).not.toContain('leitfaden.kohlenmonoxid')
        const atemnot = labels('Sprachschwierigkeiten zwischen Atemzügen')
        expect(schluessel(atemnot, '06D02', '1-hand-der-anrufer-ist-selbst-betroffen')).toContain('leitfaden.abgehackt')
        expect(schluessel(atemnot, '06D02')).not.toContain('leitfaden.abgehackt')
    })

    it('nennt die Warntafel, oder dass keine lesbar ist', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'p.tafel': {frage: 'Tafel?', eingabe: {art: 'warntafel' as const, vorlage: '{wert}', platzhalter: ''}, ziel: 'p.k0'}}}
        const szenario = anrufMit('t').szenario
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {wert: '33/1203'}}}).find(p => p.schluessel === 'leitfaden.tafel')?.werte).toEqual({oben: '33', unten: '1203'})
        expect(leitfaden(graph, {...szenario, antworten: {'p.tafel': {}}}).some(p => p.schluessel === 'leitfaden.keineTafel')).toBe(true)
    })

    it('lässt einen Anrufer ohne Adresse die Umgebung beschreiben statt den Ort zu nennen', () => {
        const szenario = anrufMit('d').szenario
        szenario.ort = {...szenario.ort, adresse: {strasse: '', hausnummer: '', plz: '', ortsteil: 'Neukölln'}, objekt: 'Volkspark Hasenheide (Park)', geschoss: '', klingel: '',
            ohneAdresse: {wo: 'ein Park', umgebung: [{name: 'U Hermannplatz', art: 'Bahnhof', richtung: 'Nordosten', meter: 250}]}}
        const punkte = leitfaden(GRAPH, szenario)
        expect(punkte.map(p => p.schluessel)).toContain('leitfaden.ohneAdresse')
        expect(punkte.map(p => p.schluessel)).not.toContain('leitfaden.ort')
        expect(punkte.find(p => p.schluessel === 'leitfaden.umgebung')?.werte).toEqual({name: 'U Hermannplatz', art: 'Bahnhof', richtung: 'Nordosten', meter: '250'})
    })

    it('beschreibt die Lage auch bei Codes ohne lesbaren Anlass mit Worten statt mit dem Code', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'p.e2': {...GRAPH.knoten['p.e2']!, anlass: '17D01'}}}
        const szenario = {...anrufMit('c').szenario, ziel: {knoten: 'p.e2', code: '17D01'}}
        expect(lageText(graph, szenario)).toBe('Sturz: Schwer')
        const mitAnlass = {...GRAPH, knoten: {...GRAPH.knoten, 'p.e2': {...GRAPH.knoten['p.e2']!, anlass: 'Sturz mit Kopfverletzung'}}}
        expect(lageText(mitAnlass, szenario)).toBe('Sturz mit Kopfverletzung')
    })

    it('nennt das Geschlecht als Adjektiv', () => {
        const graph = {...GRAPH, knoten: {...GRAPH.knoten, 'rd.geschlecht': {frage: 'Geschlecht?', antworten: [{id: 'mann', label: 'Mann', ziel: 'x', geschlecht: 'm' as const}, {id: 'frau', label: 'Frau', ziel: 'x', geschlecht: 'w' as const}]}}}
        const szenario = {...anrufMit('g').szenario, betroffener: {name: 'Murat Yıldız'}}
        szenario.antworten = {...szenario.antworten, 'rd.alter': {wert: '88'}, 'rd.geschlecht': {antwort: 'mann', label: 'Mann'}}
        expect(leitfaden(graph, szenario).find(p => p.schluessel === 'leitfaden.betroffen')?.werte?.person).toBe('Murat Yıldız, 88 Jahre, männlich')
    })
})
