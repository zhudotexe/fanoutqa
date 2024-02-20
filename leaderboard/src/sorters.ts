import type { Datum } from '@/scores'

// helpers
export type Sorter = (a: Datum, b: Datum) => number

const inverse = (f: Sorter) => (a: Datum, b: Datum) => -f(a, b)

export const enum SortOrder {
  NONE = 0,
  ASC = 1,
  DESC = 2
}

// ==== sorter impls ====
const numeric: (getter: (datum: Datum) => number) => Sorter = (getter) => (a, b) =>
  getter(a) - getter(b)
const numericDesc: (getter: (datum: Datum) => number) => Sorter = (key) => inverse(numeric(key))

// ==== export mapping ====
export const sorters: { [id: string]: { asc: Sorter; desc?: Sorter } } = {
  context: { asc: numeric((datum) => datum.context), desc: numericDesc((datum) => datum.context) },
  loose: {
    asc: numeric((datum) => datum.acc.loose),
    desc: numericDesc((datum) => datum.acc.loose)
  },
  strict: {
    asc: numeric((datum) => datum.acc.strict),
    desc: numericDesc((datum) => datum.acc.strict)
  },
  rouge1: {
    asc: numeric((datum) => datum.rouge.rouge1.fscore),
    desc: numericDesc((datum) => datum.rouge.rouge1.fscore)
  },
  rouge2: {
    asc: numeric((datum) => datum.rouge.rouge2.fscore),
    desc: numericDesc((datum) => datum.rouge.rouge2.fscore)
  },
  rougeL: {
    asc: numeric((datum) => datum.rouge.rougeL.fscore),
    desc: numericDesc((datum) => datum.rouge.rougeL.fscore)
  },
  bleurt: { asc: numeric((datum) => datum.bleurt), desc: numericDesc((datum) => datum.bleurt) },
  gptscore: { asc: numeric((datum) => datum.gpt), desc: numericDesc((datum) => datum.gpt) }
}
export const defaultSorter: Sorter = sorters.context.asc
