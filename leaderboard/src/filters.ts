import type { Datum } from '@/scores'
import { ModelType } from '@/scores'

export interface FilterOption<T> {
  label: string
  value: T
}

export type Filter = (datum: Datum) => boolean

export interface FilterParams<T> {
  options: FilterOption<T>[]
  strategy: (values: T[]) => Filter
}

export const filters: { [id: string]: FilterParams<any> } = {
  modelType: {
    options: [
      { label: 'Foundation Model', value: ModelType.foundation },
      { label: 'Fine-Tune', value: ModelType.finetune },
      { label: 'Specialized Prompting', value: ModelType.prompt },
      { label: 'Other', value: ModelType.other }
    ],
    strategy(values: any[]): (datum: Datum) => boolean {
      return (datum: Datum) => values.includes(datum.type)
    }
  }
}
