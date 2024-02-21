<script setup lang="ts">
import Table from '@/Table.vue'
import closedBookData from '@/data/web-closedbook.json'
import openBookData from '@/data/web-openbook.json'
import evidenceProvidedData from '@/data/web-wiki-provided.json'
import type { Datum } from '@/scores'
</script>

<template>
  <section class="section">
    <div class="container">
      <nav class="breadcrumb" aria-label="breadcrumbs">
        <ul>
          <li><a href="/">FanOutQA Documentation</a></li>
          <li class="is-active"><a href="#" aria-current="page">Leaderboard</a></li>
        </ul>
      </nav>

      <h1 class="title">FanOutQA Leaderboards</h1>
      <p>
        These leaderboards contain the test-set scores of various models. To submit your own model's
        generations to the leaderboards, see
        <a href="/index.html#test-set-evaluation">Test Set Evaluation</a>.
      </p>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <h2 class="title">Closed Book</h2>
      <h3 class="subtitle">
        In the closed book setting, models must answer fan-out questions using only parametric
        knowledge.
      </h3>
      <Table :data="closedBookData as Datum[]" />
    </div>
  </section>

  <section class="section">
    <div class="container">
      <h2 class="title">Open Book</h2>
      <h3 class="subtitle">
        In the open book setting, models are given access to retrieval tools and must retrieve
        Wikipedia articles to answer fan-out questions.
      </h3>
      <Table :data="openBookData as Datum[]" />
    </div>
  </section>

  <section class="section">
    <div class="container">
      <h2 class="title">Evidence Provided</h2>
      <h3 class="subtitle">
        In the evidence provided setting, models are given the text of the articles needed to answer
        a fan-out question.
      </h3>
      <Table :data="evidenceProvidedData as Datum[]" />
    </div>
  </section>
</template>

<style lang="scss">
@import './global.scss';
</style>
