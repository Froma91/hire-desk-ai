<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
</script>

<template>
  <div id="app">
    <NavBar />
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
main {
  padding: 1rem 1.5rem;
}
</style>
