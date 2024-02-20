<script setup lang="ts">
import FilterIcon from '@/FilterIcon.vue'
import { filters } from '@/filters'
import { defaultSorter, sorters, SortOrder } from '@/sorters'
import SortIcon from '@/SortIcon.vue'
import { computed, onMounted, reactive } from 'vue'
import type { Datum } from '@/scores'

// setup
const props = defineProps<{
  data: Datum[]
}>()

// state
const pagination = reactive({
  currentPage: 0,
  numPerPage: 50
})
const filterSelections = reactive(new Map<string, Set<any>>())
const sortOrders = reactive(new Map<string, SortOrder>())

// computed
const filteredSortedData = computed(() => {
  let tempData = [...props.data]
  // filter
  for (const [filterKey, selected] of filterSelections) {
    const filterImpl = filters[filterKey]
    if (!filterImpl) continue
    tempData = tempData.filter(filterImpl.strategy(Array.from(selected)))
  }
  // sort: return first non-zero sort
  return tempData.sort((a, b) => {
    for (const [sorterKey, direction] of sortOrders) {
      const sorterImpl = sorters[sorterKey]
      if (!sorterImpl) continue
      let val = 0
      if (direction === SortOrder.ASC) {
        val = sorterImpl.asc(a, b)
      } else if (direction === SortOrder.DESC && sorterImpl.desc) {
        val = sorterImpl.desc(a, b)
      }
      if (val) return val
    }
    return defaultSorter(a, b)
  })
})
const currentPageData = computed(() => {
  return filteredSortedData.value.slice(
    pagination.currentPage * pagination.numPerPage,
    (pagination.currentPage + 1) * pagination.numPerPage
  )
})
const numPages = computed(() => {
  return Math.ceil(filteredSortedData.value.length / pagination.numPerPage)
})

// methods
// filters
function getSelectedFilterOptions(filterKey: string): number[] {
  const selected = filterSelections.get(filterKey)
  if (selected !== undefined) {
    return Array.from(selected)
  }
  return []
}

function onFilterSelectionChange(filterKey: string, selected: number[]) {
  if (!selected.length) {
    filterSelections.delete(filterKey)
  } else {
    filterSelections.set(filterKey, new Set(selected))
  }
  updateQueryParams()
}

// sorters
function getSortIndex(sorterKey: string): number | null {
  const idx = Array.from(sortOrders.keys()).indexOf(sorterKey)
  return idx === -1 ? null : idx
}

function getSortDirection(sorterKey: string): SortOrder {
  return sortOrders.get(sorterKey) ?? SortOrder.NONE
}

function onSortDirectionChange(sorterKey: string, direction: SortOrder) {
  if (direction === SortOrder.NONE) {
    sortOrders.delete(sorterKey)
  } else {
    sortOrders.set(sorterKey, direction)
  }
  updateQueryParams()
}

// query param helpers
function updateQueryParams() {
  const searchParams = new URLSearchParams(window.location.search)

  // build sort query param
  searchParams.delete('sort')
  for (const [sorterKey, direction] of sortOrders) {
    searchParams.append('sort', `${sorterKey}:${direction}`)
  }

  // build filter query params
  for (const filterKey of Object.keys(filters)) {
    searchParams.delete(filterKey)
    const oneFilterSelections = filterSelections.get(filterKey)
    if (oneFilterSelections) {
      oneFilterSelections.forEach((v) => searchParams.append(filterKey, v))
    }
  }

  // set query string without reloading
  const newRelativePathQuery = window.location.pathname + '?' + searchParams.toString()
  history.pushState(null, '', newRelativePathQuery)
}

function loadFilterQueryParams() {
  const searchParams = new URLSearchParams(window.location.search)
  for (const [filterKey, filterDef] of Object.entries(filters)) {
    // if the filter is in the query param and valid, set it up
    const filterQuery = searchParams.getAll(filterKey)
    // find the valid options
    let validOptions = []
    for (const queryElem of filterQuery) {
      const matchingOption = filterDef.options.find((option) => option.value === +(queryElem ?? 0))
      if (matchingOption) {
        validOptions.push(matchingOption.value)
      }
    }
    // and init the filter
    if (validOptions.length) {
      filterSelections.set(filterKey, new Set(validOptions))
    }
  }
}

function loadSortQueryParams() {
  // if the sorter is in the query param and valid, set it up
  const searchParams = new URLSearchParams(window.location.search)
  const sortQuery = searchParams.getAll('sort')
  for (const sortElem of sortQuery) {
    // ensure key and direction are valid
    if (!sortElem) continue
    const [sorterKey, direction] = sortElem.split(':', 2)
    if (!(sorters[sorterKey] && (+direction === 1 || +direction === 2))) continue
    // init the sorter
    sortOrders.set(sorterKey, +direction)
  }
}

// other
function clearFilters() {
  filterSelections.clear()
  sortOrders.clear()
  updateQueryParams()
}

// hooks
onMounted(() => {
  loadFilterQueryParams()
  loadSortQueryParams()
})
</script>

<template>
  <!-- # info -->
  <p>look, this is the loeaderboard waow</p>
  <!-- /# info -->

  <!-- filter info -->
  <div class="level mt-2">
    <div class="level-right">
      <p class="level-item">
        {{ filteredSortedData.length }}
        {{ filteredSortedData.length === 1 ? 'entry matches' : 'entries match' }}
        your current filters.
      </p>
      <p class="level-item">
        <button class="button" @click="clearFilters()">Clear Sort &amp; Filters</button>
      </p>
    </div>
  </div>
  <!-- /filter info -->

  <div class="table-container mt-4">
    <table class="table is-striped is-fullwidth is-hoverable">
      <thead>
        <tr>
          <th>
            <span class="icon-text">
              <span>Model</span>
              <FilterIcon
                class="ml-1"
                :options="filters.modelType.options"
                :selected="getSelectedFilterOptions('modelType')"
                @selectionChanged="onFilterSelectionChange('modelType', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>Context Size</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('context')"
                :direction="getSortDirection('context')"
                @directionChanged="onSortDirectionChange('context', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>Loose</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('loose')"
                :direction="getSortDirection('loose')"
                @directionChanged="onSortDirectionChange('loose', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>Strict</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('strict')"
                :direction="getSortDirection('strict')"
                @directionChanged="onSortDirectionChange('strict', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>ROUGE-1</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('rouge1')"
                :direction="getSortDirection('rouge1')"
                @directionChanged="onSortDirectionChange('rouge1', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>ROUGE-2</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('rouge2')"
                :direction="getSortDirection('rouge2')"
                @directionChanged="onSortDirectionChange('rouge2', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>ROUGE-L</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('rougeL')"
                :direction="getSortDirection('rougeL')"
                @directionChanged="onSortDirectionChange('rougeL', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>BLEURT</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('bleurt')"
                :direction="getSortDirection('bleurt')"
                @directionChanged="onSortDirectionChange('bleurt', $event)"
              />
            </span>
          </th>
          <th>
            <span class="icon-text">
              <span>GPT Judge</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('gptscore')"
                :direction="getSortDirection('gptscore')"
                @directionChanged="onSortDirectionChange('gptscore', $event)"
              />
            </span>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="datum in currentPageData">
          <td>{{ datum.name }} ({{ datum.citation }})</td>
          <td>{{ datum.context }}</td>
          <td>{{ datum.acc.loose }}</td>
          <td>{{ datum.acc.strict }}</td>
          <td>{{ datum.rouge.rouge1.fscore }}</td>
          <td>{{ datum.rouge.rouge2.fscore }}</td>
          <td>{{ datum.rouge.rougeL.fscore }}</td>
          <td>{{ datum.bleurt }}</td>
          <td>{{ datum.gpt }}</td>
        </tr>
      </tbody>
    </table>

    <div class="level" v-if="numPages > 1">
      <p class="level-item">
        <button
          class="button mr-2"
          v-if="pagination.currentPage > 0"
          @click="pagination.currentPage--"
        >
          <span class="icon is-small">
            <font-awesome-icon :icon="['fas', 'angle-left']" />
          </span>
        </button>
        <span>Page {{ pagination.currentPage + 1 }} / {{ numPages }}</span>
        <button
          class="button ml-2"
          v-if="pagination.currentPage < numPages - 1"
          @click="pagination.currentPage++"
        >
          <span class="icon is-small">
            <font-awesome-icon :icon="['fas', 'angle-right']" />
          </span>
        </button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.table-container {
  min-height: 350px;
}
</style>
