<script setup lang="ts">
import { SortOrder } from '@/sorters'

// setup
const props = defineProps<{
  index: number | null;
  direction: SortOrder;
  disallowSortDesc?: boolean;
}>()
const emit = defineEmits<{
  (e: 'directionChanged', direction: SortOrder): void;
}>()

// methods
function cycleSortState() {
  if (props.direction === SortOrder.NONE) {
    emit('directionChanged', SortOrder.ASC)
  } else if (props.direction === SortOrder.ASC) {
    if (!props.disallowSortDesc) {
      emit('directionChanged', SortOrder.DESC)
    } else {
      emit('directionChanged', SortOrder.NONE)
    }
  } else {
    emit('directionChanged', SortOrder.NONE)
  }
}
</script>

<template>
  <span class="icon m-0 is-clickable" @click="cycleSortState">
    <font-awesome-icon :icon="['fas', 'sort']" v-if="direction === 0" />
    <font-awesome-icon :icon="['fas', 'sort-up']" v-else-if="direction === 1" />
    <font-awesome-icon :icon="['fas', 'sort-down']" v-else />
    {{ index !== null ? index + 1 : null }}
  </span>
</template>
