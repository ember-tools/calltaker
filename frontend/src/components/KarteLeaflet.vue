<script setup lang="ts">
import type L from 'leaflet'
import {onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {BERLIN_GRENZEN, BERLIN_MITTE, type Funkzelle, KACHEL_ADRESSE, type Kartenpunkt, ZOOM_MAX, ZOOM_MIN} from '../modell/karte'

const props = withDefaults(defineProps<{punkte?: Kartenpunkt[], funkzelle?: Funkzelle, setzbar?: boolean, beschriftung: string}>(), {
    punkte: () => [],
    funkzelle: undefined,
    setzbar: false,
})
const emit = defineEmits<{gesetzt: [breite: number, laenge: number]}>()

const {t} = useI18n()
const behaelter = useTemplateRef<HTMLDivElement>('behaelter')
const karte = shallowRef<L.Map | null>(null)
let leaflet: typeof L | undefined
let ebene: L.LayerGroup | undefined

/** Which theme colour marks which kind of point: what was taken in red, the truth in blue. */
const FARBEN: Record<Kartenpunkt['art'], ThemeColour> = {erfasst: 'error', wahrheit: 'info'}

/** A theme colour the map draws with. */
type ThemeColour = 'error' | 'info' | 'warning'

/**
 * A theme colour as the page resolves it right now, so the map follows the theme.
 *
 * @param name the colour
 * @returns its CSS value
 */
function themeColour(name: ThemeColour): string {
    return getComputedStyle(document.documentElement).getPropertyValue(`--ui-${name}`).trim() || 'currentColor'
}

function zeichnen(): void {
    if (!leaflet || !ebene) return
    const L = leaflet
    ebene.clearLayers()
    if (props.funkzelle) {
        L.circle(props.funkzelle.mitte, {radius: props.funkzelle.radius, color: themeColour('warning'), weight: 2, dashArray: '6 6', fillOpacity: 0.08, interactive: false}).addTo(ebene)
    }
    for (const punkt of props.punkte) {
        L.circleMarker([punkt.breite, punkt.laenge], {
            radius: punkt.art === 'wahrheit' ? 11 : 7,
            color: themeColour(FARBEN[punkt.art]),
            fillColor: themeColour(FARBEN[punkt.art]),
            fillOpacity: punkt.art === 'wahrheit' ? 0.15 : 0.9,
            weight: 3,
        }).addTo(ebene)
    }
    mitteSetzen()
}

let letzteMitte = ''

/**
 * Brings the points into view: one point close up, several all at once; a cell area is always
 * shown whole, with the points.
 */
function mitteSetzen(): void {
    const erster = props.punkte[0]
    const zelle = props.funkzelle
    const mitte = [...props.punkte.map(p => `${p.breite},${p.laenge}`), zelle ? `${zelle.mitte.join(',')},${zelle.radius}` : ''].join(';')
    if (!karte.value || !leaflet || mitte === letzteMitte) return
    const L = leaflet
    if (!erster) {
        if (zelle) {
            letzteMitte = mitte
            karte.value.fitBounds(L.latLng(zelle.mitte).toBounds(zelle.radius * 2), {padding: [10, 10]})
        }
        return
    }
    letzteMitte = mitte
    if (props.punkte.length > 1 || zelle) {
        const grenzen = L.latLngBounds(props.punkte.map(p => [p.breite, p.laenge]))
        if (zelle) grenzen.extend(L.latLng(zelle.mitte).toBounds(zelle.radius * 2))
        karte.value.fitBounds(grenzen, {padding: [30, 30], maxZoom: 17})
        return
    }
    karte.value.setView([erster.breite, erster.laenge], Math.max(karte.value.getZoom(), 16))
}

/**
 * Leaflet reaches for `window` as soon as it is imported, so it is loaded only once the map is in
 * the browser; a prerendered page never imports it.
 */
onMounted(async () => {
    const {default: L} = await import('leaflet')
    if (!behaelter.value) return
    leaflet = L
    ebene = L.layerGroup()
    const neu = L.map(behaelter.value!, {minZoom: ZOOM_MIN, maxZoom: ZOOM_MAX, maxBounds: BERLIN_GRENZEN})
    neu.setView(BERLIN_MITTE, 12)
    const mitwirkende = t('karte.mitwirkende')
    L.tileLayer(KACHEL_ADRESSE, {
        minZoom: ZOOM_MIN,
        maxZoom: ZOOM_MAX,
        bounds: BERLIN_GRENZEN,
        attribution: `© <a href="https://www.openstreetmap.org/copyright">${mitwirkende}</a>`,
    }).addTo(neu)
    ebene.addTo(neu)
    neu.on('click', ereignis => {
        if (props.setzbar) emit('gesetzt', ereignis.latlng.lat, ereignis.latlng.lng)
    })
    karte.value = neu
    zeichnen()
    if (typeof ResizeObserver !== 'undefined') {
        groesse = new ResizeObserver(() => karte.value?.invalidateSize())
        groesse.observe(behaelter.value!)
    }
})

let groesse: ResizeObserver | undefined

watch(() => [props.punkte, props.funkzelle], zeichnen, {deep: true})

onBeforeUnmount(() => {
    groesse?.disconnect()
    karte.value?.remove()
})
</script>

<template>
    <div ref="behaelter" role="region" :aria-label="beschriftung" class="isolate h-full min-h-40 w-full"/>
</template>
