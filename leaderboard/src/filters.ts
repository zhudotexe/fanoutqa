const maxWardNumber = 30
const maxPlotNumber = 60

export interface FilterOption<T> {
  label: string;
  value: T;
}

export type Filter = (plot: PlotState) => boolean;

export interface FilterParams<T> {
  options: FilterOption<T>[];
  strategy: (values: T[]) => Filter;
}

export const filters: { [id: string]: FilterParams<number> } = {
  districts: {
    options: [
      { label: 'Mist', value: 339 },
      { label: 'The Lavender Beds', value: 340 },
      { label: 'The Goblet', value: 341 },
      { label: 'Shirogane', value: 641 },
      { label: 'Empyreum', value: 979 }
    ],
    strategy(values: number[]): (plot: PlotState) => boolean {
      return (plot: PlotState) => values.includes(plot.district_id)
    }
  },
  wards: {
    options: generateOptionSequence(maxWardNumber),
    strategy(values: number[]): (plot: PlotState) => boolean {
      return (plot: PlotState) => values.includes(plot.ward_number)
    }
  },
  plots: {
    options: generateOptionSequence(maxPlotNumber),
    strategy(values: number[]): (plot: PlotState) => boolean {
      return (plot: PlotState) => values.includes(plot.plot_number)
    }
  },
  sizes: {
    options: [
      { label: 'Small', value: HouseSize.SMALL },
      { label: 'Medium', value: HouseSize.MEDIUM },
      { label: 'Large', value: HouseSize.LARGE }
    ],
    strategy(values: number[]): (plot: PlotState) => boolean {
      return (plot: PlotState) => values.includes(plot.size)
    }
  },
  phases: {
    options: [
      { label: 'Accepting Entries', value: LottoPhase.ENTRY },
      { label: 'Results', value: LottoPhase.RESULTS },
      { label: 'Unavailable', value: LottoPhase.UNAVAILABLE },
      { label: 'FCFS', value: -2 },
      { label: 'Missing/Outdated', value: -1 }
    ],
    strategy(values: number[]): (plot: PlotState) => boolean {
      return (plot: PlotState) => {
        if (!isLottery(plot)) {
          return values.includes(-2)
        } else if (isUnknownOrOutdatedPhase(plot)) {
          return values.includes(-1)
        }
        return values.includes(plot.lotto_phase!)
      }
    }
  },
  tenants: {
    options: [
      { label: 'Free Company', value: PurchaseSystem.FREE_COMPANY },
      { label: 'Individual', value: PurchaseSystem.INDIVIDUAL }
    ],
    strategy(values: number[]): (plot: PlotState) => boolean {
      const tenantBitField = values.reduce((acc, x) => acc | x)
      return (plot: PlotState) => (plot.purchase_system & tenantBitField) !== 0
    }
  }
}
