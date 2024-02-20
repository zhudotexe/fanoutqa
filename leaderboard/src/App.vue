<script setup lang="ts">
import Table from '@/Table.vue'
import closedBookData from '@/data/web-closedbook.json'
import openBookData from '@/data/web-openbook.json'
import evidenceProvidedData from '@/data/web-wiki-provided.json'
</script>

<template>
  <Table :data="closedBookData" />
  <Table :data="openBookData" />
  <Table :data="evidenceProvidedData" />
</template>

<style scoped></style>
