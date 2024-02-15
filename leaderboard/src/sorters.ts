// helpers
export type Sorter = (a: PlotState, b: PlotState) => number;

const inverse = (f: Sorter) => (a: PlotState, b: PlotState) => -f(a, b)

export const enum SortOrder {
  NONE = 0,
  ASC = 1,
  DESC = 2,
}

export const addressSorter: Sorter = (a, b) =>
  a.district_id - b.district_id || a.ward_number - b.ward_number || a.plot_number - b.plot_number

// sorter impls
const size = (a: PlotState, b: PlotState) => a.size - b.size
const sizeDesc = inverse(size)

const price = (a: PlotState, b: PlotState) => a.price - b.price
const priceDesc = inverse(price)

const entries = (a: PlotState, b: PlotState) => {
  const aVal = isOutdatedPhase(a) || a.lotto_phase === null ? Number.MAX_VALUE : a.lotto_entries ?? 0
  const bVal = isOutdatedPhase(b) || b.lotto_phase === null ? Number.MAX_VALUE : b.lotto_entries ?? 0
  return aVal - bVal
}
const entriesDesc = (a: PlotState, b: PlotState) => {
  // Number.MIN_VALUE is actually an epsilon and not the minimum value representable in a float
  // because *that's* not a foot-gun at all. Thanks Javascript.
  const aVal = isOutdatedPhase(a) || a.lotto_phase === null ? Number.MIN_SAFE_INTEGER : a.lotto_entries ?? 0
  const bVal = isOutdatedPhase(b) || b.lotto_phase === null ? Number.MIN_SAFE_INTEGER : b.lotto_entries ?? 0
  return bVal - aVal
}

const phase = (a: PlotState, b: PlotState) => {
  const aVal = isUnknownOrOutdatedPhase(a) ? Number.MAX_VALUE : a.lotto_phase!
  const bVal = isUnknownOrOutdatedPhase(b) ? Number.MAX_VALUE : b.lotto_phase!
  return aVal - bVal
}
const phaseDesc = inverse(phase)

const updateTime = (a: PlotState, b: PlotState) => b.last_updated_time - a.last_updated_time
const updateTimeDesc = inverse(updateTime)

const firstSeen = (a: PlotState, b: PlotState) => b.first_seen_time - a.first_seen_time
const firstSeenDesc = inverse(firstSeen)

// full mapping
export const sorters: { [id: string]: { asc: Sorter; desc?: Sorter } } = {
  size: { asc: size, desc: sizeDesc },
  price: { asc: price, desc: priceDesc },
  entries: { asc: entries, desc: entriesDesc },
  phase: { asc: phase, desc: phaseDesc },
  updateTime: { asc: updateTime, desc: updateTimeDesc },
  firstSeen: { asc: firstSeen, desc: firstSeenDesc }
}
