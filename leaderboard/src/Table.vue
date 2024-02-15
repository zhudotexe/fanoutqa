<script setup lang="ts">
import FilterIcon from '@/FilterIcon.vue'
import { filters } from '@/filters'
import { sorters, SortOrder } from '@/sorters'
import SortIcon from '@/SortIcon.vue'
import { isArray } from 'lodash'
import { computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// setup
const router = useRouter()
const route = useRoute()

// state
const pagination = reactive({
  currentPage: 0,
  numPerPage: 50
})
const filterSelections = reactive(new Map<string, Set<number>>())
const sortOrders = reactive(new Map<string, SortOrder>())

// computed
const worldPlots = computed(() => {
  const allPlots = Array.from(props.client.plotStates.values())
  return allPlots.filter((state) => state.world_id === props.worldId)
})
const filteredSortedWorldPlots = computed(() => {
  let plots = [...worldPlots.value]
  // filter
  for (const [filterKey, selected] of filterSelections) {
    const filterImpl = filters[filterKey]
    if (!filterImpl) continue
    plots = plots.filter(filterImpl.strategy(Array.from(selected)))
  }
  // sort: return first non-zero sort
  return plots.sort((a, b) => {
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
const currentPagePlots = computed(() => {
  return filteredSortedWorldPlots.value.slice(
    pagination.currentPage * pagination.numPerPage,
    (pagination.currentPage + 1) * pagination.numPerPage
  )
})
const numPages = computed(() => {
  return Math.ceil(filteredSortedWorldPlots.value.length / pagination.numPerPage)
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
    filterSelections.set(filterKey, new Set<number>(selected))
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
  const queryParams: { [key: string]: any } = {
    ...route.query,
    sort: buildSortQueryParam()
  }
  for (const filterKey of Object.keys(filters)) {
    const oneFilterSelections = filterSelections.get(filterKey)
    if (oneFilterSelections) {
      queryParams[filterKey] = Array.from(oneFilterSelections)
    } else {
      queryParams[filterKey] = undefined
    }
  }
  router.replace({ query: queryParams })
}

function loadFilterQueryParams() {
  for (const [filterKey, filterDef] of Object.entries(filters)) {
    // if the filter is in the query param and valid, set it up
    // ensure query params are array
    let filterQuery = route.query[filterKey]
    if (!filterQuery) continue
    if (!isArray(filterQuery)) {
      filterQuery = [filterQuery]
    }
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
      filterSelections.set(filterKey, new Set<number>(validOptions))
    }
  }
}

function loadSortQueryParams() {
  // if the sorter is in the query param and valid, set it up
  // ensure query params are array
  let sortQuery = route.query.sort
  if (!sortQuery) return
  if (!isArray(sortQuery)) {
    sortQuery = [sortQuery]
  }
  for (const sortElem of sortQuery) {
    // ensure key and direction are valid
    if (!sortElem) continue
    const [sorterKey, direction] = sortElem.split(':', 2)
    if (!(sorters[sorterKey] && (+direction === 1 || +direction === 2))) continue
    // init the sorter
    sortOrders.set(sorterKey, +direction)
  }
}

function buildSortQueryParam(): string[] {
  const result = []
  for (const [sorterKey, direction] of sortOrders) {
    result.push(`${sorterKey}:${direction}`)
  }
  return result
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
  <p>
    {{ client.worldName(worldId) }} has
    <FlashOnChange :value="worldPlots.length" />
    open plots, at least
    <FlashOnChange :value="worldPlots.filter(utils.isEntryPhase).length" />
    of which are available for bidding.
  </p>
  <p v-if="worldPlots.filter(utils.isUnknownOrOutdatedPhase).length">
    <strong>
      <FlashOnChange :value="worldPlots.filter(utils.isUnknownOrOutdatedPhase).length" />
    </strong>
    plots have missing or outdated lottery data. You can contribute by installing the
    <a href="https://github.com/zhudotexe/FFXIV_PaissaHouse#lottery-sweeps" target="_blank">
      PaissaHouse XIVLauncher plugin
    </a>
    and clicking on the placard of any outdated plot in-game. This site will update in real time!
  </p>
  <!-- /# info -->

  <!-- filter info -->
  <div class="level mt-2">
    <div class="level-left">
      <p class="level-item" v-if="client.nextOrLatestPhaseChange() > +new Date() / 1000">
        The current lottery phase ends at
        <TimeDisplay :time="client.nextOrLatestPhaseChange()" format="datetimeWeekday" />
        (
        <TimeDisplay :time="client.nextOrLatestPhaseChange()" format="relative" />
        ).
      </p>
      <p class="level-item" v-else-if="client.nextOrLatestPhaseChange() > 0">
        The previous lottery phase ended at
        <TimeDisplay :time="client.nextOrLatestPhaseChange()" format="datetimeWeekday" />
        (
        <TimeDisplay :time="client.nextOrLatestPhaseChange()" format="relative" />
        ).
      </p>
      <p class="level-item" v-else>There is insufficient data to calculate when the next lottery phase ends.</p>
    </div>
    <div class="level-right">
      <p class="level-item">
        {{ filteredSortedWorldPlots.length }}
        {{ filteredSortedWorldPlots.length === 1 ? 'plot matches' : 'plots match' }}
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
              <span>District</span>
              <FilterIcon
                class="ml-1"
                :options="filters.districts.options"
                :selected="getSelectedFilterOptions('districts')"
                @selectionChanged="onFilterSelectionChange('districts', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Ward</span>
              <FilterIconGrid
                class="ml-1"
                :options="filters.wards.options"
                :selected="getSelectedFilterOptions('wards')"
                @selectionChanged="onFilterSelectionChange('wards', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Plot</span>
              <FilterIconGrid
                class="ml-1"
                :options="filters.plots.options"
                :selected="getSelectedFilterOptions('plots')"
                @selectionChanged="onFilterSelectionChange('plots', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Size</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('size')"
                :direction="getSortDirection('size')"
                @directionChanged="onSortDirectionChange('size', $event)"
              />
              <FilterIcon
                :options="filters.sizes.options"
                :selected="getSelectedFilterOptions('sizes')"
                @selectionChanged="onFilterSelectionChange('sizes', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Price</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('price')"
                :direction="getSortDirection('price')"
                @directionChanged="onSortDirectionChange('price', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Entries</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('entries')"
                :direction="getSortDirection('entries')"
                @directionChanged="onSortDirectionChange('entries', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Lottery Phase</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('phase')"
                :direction="getSortDirection('phase')"
                @directionChanged="onSortDirectionChange('phase', $event)"
              />
              <FilterIcon
                :options="filters.phases.options"
                :selected="getSelectedFilterOptions('phases')"
                @selectionChanged="onFilterSelectionChange('phases', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Allowed Tenants</span>
              <FilterIcon
                class="ml-1"
                :options="filters.tenants.options"
                :selected="getSelectedFilterOptions('tenants')"
                @selectionChanged="onFilterSelectionChange('tenants', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>Last Updated</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('updateTime')"
                :direction="getSortDirection('updateTime')"
                @directionChanged="onSortDirectionChange('updateTime', $event)"
              />
            </span>
        </th>
        <th>
            <span class="icon-text">
              <span>First Seen</span>
              <SortIcon
                class="ml-1"
                :index="getSortIndex('firstSeen')"
                :direction="getSortDirection('firstSeen')"
                @directionChanged="onSortDirectionChange('firstSeen', $event)"
              />
            </span>
        </th>
      </tr>
      </thead>

      <tbody>
      <tr
        v-for="plot in currentPagePlots"
        :key="[plot.world_id, plot.district_id, plot.ward_number, plot.plot_number].toString()"
      >
        <td>{{ client.districtName(plot.district_id) }}</td>
        <td>Ward {{ plot.ward_number + 1 }}</td>
        <td>Plot {{ plot.plot_number + 1 }}</td>
        <td>{{ utils.sizeStr(plot.size) }}</td>
        <td>{{ plot.price.toLocaleString() }}</td>
        <td>
          <FlashOnChange :value="utils.lotteryEntryCountStr(plot)" :class="{'is-italic': utils.shouldEm(plot)}" />
        </td>
        <td>
          <FlashOnChange :value="utils.lotteryPhaseStr(plot)" :class="{'is-italic': utils.shouldEm(plot)}" />
        </td>
        <td>{{ utils.tenantStr(plot.purchase_system) }}</td>
        <td>
          <FlashOnChange :value="utils.updatedStr(plot.last_updated_time)" />
        </td>
        <td>{{ utils.updatedStr(plot.first_seen_time) }}</td>
      </tr>
      </tbody>
    </table>

    <div class="level" v-if="numPages > 1">
      <p class="level-item">
        <button class="button mr-2" v-if="pagination.currentPage > 0" @click="pagination.currentPage--">
          <span class="icon is-small">
            <font-awesome-icon :icon="['fas', 'angle-left']" />
          </span>
        </button>
        <span>Page {{ pagination.currentPage + 1 }} / {{ numPages }}</span>
        <button class="button ml-2" v-if="pagination.currentPage < numPages - 1" @click="pagination.currentPage++">
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
