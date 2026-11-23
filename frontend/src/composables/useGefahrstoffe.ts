import {shallowRef} from 'vue'
import {ladeGefahrstoffe} from '../api/gefahrstoffe'
import type {Gefahrstoffliste} from '../modell/gefahrstoffe'

const geladen = shallowRef<Gefahrstoffliste | null>(null)
let laden: Promise<Gefahrstoffliste> | null = null

/**
 * The hazardous goods by UN number, loaded on first use and shared by every view that asks.
 *
 * @returns the list once loaded
 */
export function useGefahrstoffe() {
    laden ??= ladeGefahrstoffe()
    laden.then(liste => {
        geladen.value = liste
    }).catch(() => {
        laden = null
    })
    return geladen
}
