export enum ModelType {
  foundation = 'FOUNDATION',
  finetune = 'FINETUNE',
  prompt = 'PROMPT',
  other = 'OTHER'
}

interface RougeScore {
  precision: number
  recall: number
  fscore: number
}

export interface Score {
  // meta
  name: string
  authors: string
  url: string
  citation: string
  type: ModelType
  context: number
  // score
  acc: { loose: number; strict: number }
  rouge: { rouge1: RougeScore; rouge2: RougeScore; rougeL: RougeScore }
  bleurt: number
  gpt: number
}

export type Datum = Score
