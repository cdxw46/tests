export const ROWS = 7
export const COLS = 7

export type SymbolKind =
  | 'nova'
  | 'corazon'
  | 'gota'
  | 'cometa'
  | 'estrella'
  | 'flor'
  | 'gema'
  | 'scatter'

export type Cell = {
  id: number
  kind: SymbolKind
}

export type Cluster = {
  kind: SymbolKind
  indexes: number[]
}

export const SYMBOL_META: Record<
  SymbolKind,
  { label: string; payout: number; weight: number }
> = {
  nova: { label: 'Nova de fresa', payout: 1.25, weight: 15 },
  corazon: { label: 'Corazón solar', payout: 1, weight: 17 },
  gota: { label: 'Orbe de frambuesa', payout: 0.8, weight: 18 },
  cometa: { label: 'Cometa de mora', payout: 0.7, weight: 18 },
  estrella: { label: 'Estrella lima', payout: 0.6, weight: 20 },
  flor: { label: 'Flor galáctica', payout: 0.5, weight: 21 },
  gema: { label: 'Gema violeta', payout: 0.45, weight: 22 },
  scatter: { label: 'Portal bonus', payout: 0, weight: 3 },
}

const PAYING_SYMBOLS = (Object.keys(SYMBOL_META) as SymbolKind[]).filter(
  (kind) => kind !== 'scatter',
)

let nextId = 1

function randomKind(): SymbolKind {
  const entries = Object.entries(SYMBOL_META) as [
    SymbolKind,
    (typeof SYMBOL_META)[SymbolKind],
  ][]
  const total = entries.reduce((sum, [, meta]) => sum + meta.weight, 0)
  let cursor = Math.random() * total

  for (const [kind, meta] of entries) {
    cursor -= meta.weight
    if (cursor <= 0) return kind
  }

  return 'gema'
}

function makeCell(kind = randomKind()): Cell {
  return { id: nextId++, kind }
}

export function createBoard(addCluster = false): Cell[] {
  const board = Array.from({ length: ROWS * COLS }, () => makeCell())

  if (addCluster) {
    injectCluster(board)
    if (Math.random() < 0.2) injectCluster(board)
  }

  return board
}

function injectCluster(board: Cell[]) {
  const kind = PAYING_SYMBOLS[Math.floor(Math.random() * PAYING_SYMBOLS.length)]
  const targetSize = 5 + Math.floor(Math.random() * 5)
  const startRow = 1 + Math.floor(Math.random() * (ROWS - 2))
  const startCol = 1 + Math.floor(Math.random() * (COLS - 2))
  const selected = new Set<number>([startRow * COLS + startCol])

  let safety = 0
  while (selected.size < targetSize && safety < 100) {
    safety += 1
    const current = [...selected][Math.floor(Math.random() * selected.size)]
    const row = Math.floor(current / COLS)
    const col = current % COLS
    const candidates = [
      [row - 1, col],
      [row + 1, col],
      [row, col - 1],
      [row, col + 1],
    ].filter(
      ([candidateRow, candidateCol]) =>
        candidateRow >= 0 &&
        candidateRow < ROWS &&
        candidateCol >= 0 &&
        candidateCol < COLS,
    )
    const [nextRow, nextCol] =
      candidates[Math.floor(Math.random() * candidates.length)]
    selected.add(nextRow * COLS + nextCol)
  }

  selected.forEach((index) => {
    board[index] = makeCell(kind)
  })
}

export function findClusters(board: Cell[]): Cluster[] {
  const visited = new Set<number>()
  const clusters: Cluster[] = []

  board.forEach((cell, startIndex) => {
    if (visited.has(startIndex) || cell.kind === 'scatter') return

    const indexes: number[] = []
    const queue = [startIndex]
    visited.add(startIndex)

    while (queue.length > 0) {
      const index = queue.shift()
      if (index === undefined) break
      indexes.push(index)

      const row = Math.floor(index / COLS)
      const col = index % COLS
      const neighbours = [
        row > 0 ? index - COLS : -1,
        row < ROWS - 1 ? index + COLS : -1,
        col > 0 ? index - 1 : -1,
        col < COLS - 1 ? index + 1 : -1,
      ]

      neighbours.forEach((neighbour) => {
        if (
          neighbour >= 0 &&
          !visited.has(neighbour) &&
          board[neighbour].kind === cell.kind
        ) {
          visited.add(neighbour)
          queue.push(neighbour)
        }
      })
    }

    if (indexes.length >= 5) clusters.push({ kind: cell.kind, indexes })
  })

  return clusters
}

export function calculateWin(
  clusters: Cluster[],
  bet: number,
  multipliers: number[],
): number {
  const amount = clusters.reduce((total, cluster) => {
    const sizeBoost = 1 + (cluster.indexes.length - 5) * 0.28
    const multiplierTotal = cluster.indexes.reduce(
      (sum, index) => sum + (multipliers[index] ?? 0),
      0,
    )
    const multiplierBoost = multiplierTotal > 0 ? multiplierTotal : 1
    return (
      total +
      SYMBOL_META[cluster.kind].payout * bet * sizeBoost * multiplierBoost
    )
  }, 0)

  return Math.round(amount * 100) / 100
}

export function collapseBoard(board: Cell[], removed: Set<number>): Cell[] {
  const next = Array<Cell>(ROWS * COLS)

  for (let col = 0; col < COLS; col += 1) {
    const survivors: Cell[] = []
    for (let row = ROWS - 1; row >= 0; row -= 1) {
      const index = row * COLS + col
      if (!removed.has(index)) survivors.push(board[index])
    }

    for (let row = ROWS - 1; row >= 0; row -= 1) {
      next[row * COLS + col] = survivors[ROWS - 1 - row] ?? makeCell()
    }
  }

  return next
}

export function countScatters(board: Cell[]): number {
  return board.filter((cell) => cell.kind === 'scatter').length
}
