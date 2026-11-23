<script setup lang="ts">
import AppFuss from './components/AppFuss.vue'
</script>

<template>
    <div class="flex min-h-screen flex-col">
        <RouterView :key="$route.fullPath"/>
        <AppFuss/>
    </div>
</template>
