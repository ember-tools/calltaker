<script setup lang="ts">
import AppFuss from './components/AppFuss.vue'
import NeueFassung from './components/NeueFassung.vue'
</script>

<template>
    <div class="flex min-h-screen flex-col">
        <NeueFassung/>
        <RouterView :key="$route.fullPath"/>
        <AppFuss/>
    </div>
</template>
