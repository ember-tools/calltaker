import type {Abfragegraph} from './abfragegraph'

/**
 * A small graph that narrows: a reaction that orders the complaints, a typed age and a sex that
 * decide a later age question.
 *
 * @returns the graph
 */
export function eingrenzungsgraph(): Abfragegraph {
    return {
    meta: {
        version: 1, wurzel: 'reaktion', quelle: '', hinweise: {}, notfallkategorien: {},
        person: {alter_knoten: 'alter', geschlecht_knoten: 'geschlecht', geschlecht: {frau: 'w', mann: 'm'}},
        eingrenzung: [{knoten: 'beschwerde', wenn: [{knoten: 'reaktion', antworten: ['nicht']}], zuerst: ['p.bewusstlos', 'krampf']}],
    },
    knoten: {
        reaktion: {frage: 'Reagiert?', antworten: [{id: 'ja', label: 'Ja', ziel: 'alter'}, {id: 'nicht', label: 'Nicht', ziel: 'alter'}]},
        alter: {frage: 'Alter?', eingabe: {vorlage: '{wert}', platzhalter: '', leer: {label: 'unbekannt', aussage: ''}}, ziel: 'geschlecht'},
        geschlecht: {frage: 'Geschlecht?', antworten: [{id: 'frau', label: 'Frau', ziel: 'beschwerde'}, {id: 'mann', label: 'Mann', ziel: 'beschwerde'}]},
        beschwerde: {frage: 'Was?', antworten: [
            {id: 'bauch', label: 'Bauch', ziel: 'altersfrage', protokoll: 'p.bauch'},
            {id: 'krampf', label: 'Krampf', ziel: 'altersfrage', protokoll: 'p.krampf'},
            {id: 'bewusstlos', label: 'Bewusstlos', ziel: 'altersfrage', protokoll: 'p.bewusstlos'},
        ]},
        altersfrage: {frage: 'Alter?', antworten: [
            {id: 'unbekannt', label: 'bei Patientenalter unbekannt', ziel: 'ende', alter: {unbekannt: true}},
            {id: 'kind', label: 'bis 12', ziel: 'ende', alter: {max: 12}},
            {id: 'erwachsen', label: 'älter 12', ziel: 'ende', alter: {min: 13}},
            {id: 'frauen', label: 'Frauen 12–50', ziel: 'ende', alter: {min: 12, max: 50}, geschlecht: 'w'},
        ]},
        ende: {code: '01A01', kategorie: 'RD4C.'},
    },
    endpunkte: [],
    }
}
