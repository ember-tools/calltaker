import {readFileSync} from 'node:fs'
import {join} from 'node:path'
import {describe, expect, it} from 'vitest'
import type {Abfragegraph, Knoten} from './abfragegraph'
import {schwersteErreichbare, unterscheidungen} from './abfrageweg'

/**
 * Reads protocols of the real question graph into a graph of their own.
 *
 * @param dateien the protocol files below daten/abfrage
 * @returns the graph of their nodes
 */
function echteProtokolle(...dateien: string[]): Abfragegraph {
    const knoten: Record<string, Knoten> = {}
    for (const datei of dateien) Object.assign(knoten, JSON.parse(readFileSync(join(process.cwd(), '..', 'daten', 'abfrage', datei), 'utf-8')).knoten)
    return {meta: {version: 1, wurzel: '', quelle: '', hinweise: {}, notfallkategorien: {}}, knoten, endpunkte: []}
}

describe('unterscheidungen im echten Graphen', () => {
    it('unterscheidet jede Gruppe gleich lautender Antworten', () => {
        const graph = echteProtokolle('rd/09.json', 'rd/23.json', 'rd/06.json', 'rd/17.json')
        const schwerste = schwersteErreichbare(graph)
        for (const knoten of Object.values(graph.knoten)) {
            const zusatz = unterscheidungen(knoten, schwerste, graph)
            const gruppen = new Map<string, string[]>()
            for (const antwort of knoten.antworten ?? []) {
                if (!zusatz.has(antwort.id)) continue
                gruppen.set(antwort.label, [...(gruppen.get(antwort.label) ?? []), zusatz.get(antwort.id)!])
            }
            for (const werte of gruppen.values()) expect(new Set(werte).size).toBe(werte.length)
        }
    })
})
