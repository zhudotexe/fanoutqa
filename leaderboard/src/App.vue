<script setup lang="ts">
import Table from '@/Table.vue'
import closedBookData from '@/data/web-closedbook.json'
import openBookData from '@/data/web-openbook.json'
import evidenceProvidedData from '@/data/web-wiki-provided.json'
import type { Datum } from '@/scores'
</script>

<template>
  <Table :data="closedBookData as Datum[]" />
  <Table :data="openBookData as Datum[]" />
  <Table :data="evidenceProvidedData as Datum[]" />
</template>

<style lang="scss">
@import "./global.scss";
</style>
