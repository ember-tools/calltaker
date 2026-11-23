<script setup lang="ts">
import L from 'leaflet'
import {onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {BERLIN_GRENZEN, BERLIN_MITTE, KACHEL_ADRESSE, type Kartenpunkt, ZOOM_MAX, ZOOM_MIN} from '../modell/karte'

const props = withDefaults(defineProps<{punkte?: Kartenpunkt[], setzbar?: boolean, beschriftung: string}>(), {
    punkte: () => [],
    setzbar: false,
})
const emit = defineEmits<{gesetzt: [breite: number, laenge: number]}>()

const {t} = useI18n()
const behaelter = useTemplateRef<HTMLDivElement>('behaelter')
const karte = shallowRef<L.Map | null>(null)
const ebene = L.layerGroup()

const FARBEN: Record<Kartenpunkt['art'], string> = {erfasst: '#c4361c', wahrheit: '#1f5fae'}

function zeichnen(): void {
    ebene.clearLayers()
    for (const punkt of props.punkte) {
        L.circleMarker([punkt.breite, punkt.laenge], {
            radius: punkt.art === 'wahrheit' ? 11 : 7,
            color: FARBEN[punkt.art],
            fillColor: FARBEN[punkt.art],
            fillOpacity: punkt.art === 'wahrheit' ? 0.15 : 0.9,
            weight: 3,
        }).addTo(ebene)
    }
    mitteSetzen()
}

let letzteMitte = ''

function mitteSetzen(): void {
    const erster = props.punkte[0]
    const mitte = erster ? `${erster.breite},${erster.laenge}` : ''
    if (!karte.value || !erster || mitte === letzteMitte) return
    letzteMitte = mitte
    karte.value.setView([erster.breite, erster.laenge], Math.max(karte.value.getZoom(), 16))
}

onMounted(() => {
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
})

watch(() => props.punkte, zeichnen, {deep: true})

onBeforeUnmount(() => karte.value?.remove())
</script>

<template>
    <div ref="behaelter" role="region" :aria-label="beschriftung" class="h-full min-h-40 w-full"/>
</template>
