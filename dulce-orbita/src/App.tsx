import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import {
  COLS,
  ROWS,
  SYMBOL_META,
  calculateWin,
  collapseBoard,
  countScatters,
  createBoard,
  findClusters,
  type SymbolKind,
} from './game'

const BETS = [0.2, 0.4, 0.6, 1, 2, 5, 10]
const money = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds))

function CandyIcon({ kind }: { kind: SymbolKind }) {
  if (kind === 'nova') {
    return (
      <svg className="candy-icon nova" viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="28" cy="24" r="15" />
        <circle cx="72" cy="24" r="15" />
        <path d="M25 39c-12 8-14 25-4 34l9 8 4 14h13l3-11 3 11h13l4-14 9-8c10-9 8-26-4-34-7-5-16-6-25-1-9-5-18-4-25 1Z" />
        <circle className="candy-detail dark" cx="37" cy="54" r="4" />
        <circle className="candy-detail dark" cx="63" cy="54" r="4" />
        <path className="candy-detail shine" d="M28 43c7-8 16-8 21-5-8 2-13 6-17 13Z" />
        <path className="candy-detail dark" d="M42 66q8 8 16 0-2 13-8 13t-8-13Z" />
      </svg>
    )
  }

  if (kind === 'corazon') {
    return (
      <svg className="candy-icon corazon" viewBox="0 0 100 100" aria-hidden="true">
        <path d="M50 88C38 76 13 60 13 36 13 17 36 10 50 28 64 10 87 17 87 36c0 24-25 40-37 52Z" />
        <path className="candy-detail shine" d="M27 29c6-9 18-6 20 2-9-4-16 1-19 9-4 10-10 2-1-11Z" />
        <path className="candy-detail glow" d="M30 63c13 10 24 9 39 0-8 10-14 15-19 20-6-6-12-11-20-20Z" />
      </svg>
    )
  }

  if (kind === 'gota') {
    return (
      <svg className="candy-icon gota" viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="50" r="38" />
        <ellipse className="candy-detail shine" cx="38" cy="34" rx="13" ry="9" transform="rotate(-30 38 34)" />
        <path className="candy-detail glow" d="M20 58c12 24 48 31 65 2-7 27-34 36-54 22-8-6-11-14-11-24Z" />
      </svg>
    )
  }

  if (kind === 'cometa') {
    return (
      <svg className="candy-icon cometa" viewBox="0 0 100 100" aria-hidden="true">
        <path d="M18 65c1-14 14-27 29-31 17-4 20-20 18-25 13 6 24 23 17 43-8 23-35 36-55 28-7-3-10-8-9-15Z" />
        <path className="candy-detail shine" d="M32 57c9-13 22-14 31-21-4 12-15 18-24 23-7 4-10 4-7-2Z" />
        <path className="candy-detail glow" d="M24 70c18 7 40-4 51-18-5 20-30 33-48 25Z" />
      </svg>
    )
  }

  if (kind === 'estrella') {
    return (
      <svg className="candy-icon estrella" viewBox="0 0 100 100" aria-hidden="true">
        <path d="m50 7 12 27 30 3-23 20 7 30-26-16-26 16 7-30L8 37l30-3Z" />
        <path className="candy-detail shine" d="m48 18-5 24-21 3 18 5 10-28 12 23 14-3-18-4Z" />
        <path className="candy-detail glow" d="m25 70 25-10 24 10-24-2Z" />
      </svg>
    )
  }

  if (kind === 'flor') {
    return (
      <svg className="candy-icon flor" viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="24" r="20" />
        <circle cx="76" cy="50" r="20" />
        <circle cx="50" cy="76" r="20" />
        <circle cx="24" cy="50" r="20" />
        <circle className="candy-detail center" cx="50" cy="50" r="18" />
        <ellipse className="candy-detail shine" cx="42" cy="18" rx="8" ry="5" />
      </svg>
    )
  }

  if (kind === 'gema') {
    return (
      <svg className="candy-icon gema" viewBox="0 0 100 100" aria-hidden="true">
        <path d="m50 6 36 21 1 45-37 22-37-22 1-45Z" />
        <path className="candy-detail facet" d="m50 6 10 34 27 32-37-9-37 9 27-32Z" />
        <path className="candy-detail shine" d="m21 30 25-17-8 25-18 17Z" />
      </svg>
    )
  }

  return (
    <div className="scatter-symbol" aria-hidden="true">
      <svg className="candy-icon scatter" viewBox="0 0 100 100">
        <path d="M30 12h40l8 20-6 57H28l-6-57-6-20Z" />
        <path className="candy-detail cap" d="M24 28h52l5 10H19Z" />
        <circle className="candy-detail candy-a" cx="40" cy="50" r="9" />
        <circle className="candy-detail candy-b" cx="61" cy="56" r="10" />
        <circle className="candy-detail candy-c" cx="47" cy="72" r="9" />
        <path className="candy-detail shine" d="M32 18h28l4 7H29Z" />
      </svg>
      <span>BONUS</span>
    </div>
  )
}

function App() {
  const [board, setBoard] = useState(() => createBoard(true))
  const [winning, setWinning] = useState<Set<number>>(() => new Set())
  const [multipliers, setMultipliers] = useState<number[]>(() =>
    Array(ROWS * COLS).fill(0),
  )
  const [balance, setBalance] = useState(1000)
  const [betIndex, setBetIndex] = useState(3)
  const [lastWin, setLastWin] = useState(0)
  const [cascade, setCascade] = useState(0)
  const [busy, setBusy] = useState(false)
  const [phase, setPhase] = useState('LISTO PARA DESPEGAR')
  const [freeSpins, setFreeSpins] = useState(0)
  const [autoSpins, setAutoSpins] = useState(0)
  const [muted, setMuted] = useState(false)
  const [modal, setModal] = useState<'rules' | 'bonus' | null>(null)
  const [toast, setToast] = useState('')
  const [bigWin, setBigWin] = useState(0)
  const busyRef = useRef(false)
  const balanceRef = useRef(balance)
  const multipliersRef = useRef(multipliers)
  const audioRef = useRef<AudioContext | null>(null)
  const bet = BETS[betIndex]

  useEffect(() => {
    balanceRef.current = balance
  }, [balance])

  useEffect(() => {
    multipliersRef.current = multipliers
  }, [multipliers])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 2600)
    return () => window.clearTimeout(timer)
  }, [toast])

  const playSound = useCallback(
    (sound: 'spin' | 'pop' | 'win' | 'bonus' | 'click') => {
      if (muted) return
      const AudioContextClass =
        window.AudioContext ??
        (
          window as typeof window & {
            webkitAudioContext?: typeof AudioContext
          }
        ).webkitAudioContext
      if (!AudioContextClass) return

      const context = audioRef.current ?? new AudioContextClass()
      audioRef.current = context
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      const frequencies = {
        spin: 180,
        pop: 520,
        win: 760,
        bonus: 980,
        click: 320,
      }
      const duration = sound === 'bonus' ? 0.55 : sound === 'spin' ? 0.28 : 0.18
      oscillator.type = sound === 'spin' ? 'sawtooth' : 'sine'
      oscillator.frequency.setValueAtTime(frequencies[sound], context.currentTime)
      oscillator.frequency.exponentialRampToValueAtTime(
        frequencies[sound] * (sound === 'spin' ? 2.4 : 1.35),
        context.currentTime + duration,
      )
      gain.gain.setValueAtTime(0.0001, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + duration)
      oscillator.connect(gain)
      gain.connect(context.destination)
      oscillator.start()
      oscillator.stop(context.currentTime + duration)
    },
    [muted],
  )

  const executeSpin = useCallback(
    async (isFree = false) => {
      if (busyRef.current) return
      if (!isFree && balanceRef.current < bet) {
        setToast('Saldo demo insuficiente')
        playSound('click')
        return
      }

      busyRef.current = true
      setBusy(true)
      setWinning(new Set())
      setLastWin(0)
      setCascade(0)
      setBigWin(0)

      if (!isFree) {
        const nextBalance = Math.round((balanceRef.current - bet) * 100) / 100
        balanceRef.current = nextBalance
        setBalance(nextBalance)
      }

      let activeMultipliers = isFree
        ? [...multipliersRef.current]
        : Array<number>(ROWS * COLS).fill(0)
      if (!isFree) {
        multipliersRef.current = activeMultipliers
        setMultipliers(activeMultipliers)
      }

      setPhase(isFree ? 'ÓRBITA GRATIS' : 'LANZANDO…')
      playSound('spin')
      await wait(280)

      let activeBoard = createBoard(Math.random() < (isFree ? 0.88 : 0.64))
      const scatterCount = countScatters(activeBoard)
      setBoard(activeBoard)
      await wait(460)

      let totalWin = 0
      let chain = 0
      let clusters = findClusters(activeBoard)

      while (clusters.length > 0 && chain < 7) {
        chain += 1
        const removed = new Set(clusters.flatMap((cluster) => cluster.indexes))
        const cascadeWin = calculateWin(clusters, bet, activeMultipliers)
        totalWin = Math.round((totalWin + cascadeWin) * 100) / 100

        setCascade(chain)
        setWinning(removed)
        setLastWin(totalWin)
        setPhase(chain > 1 ? `CASCADA ×${chain}` : '¡COMBINACIÓN!')
        playSound(chain > 1 ? 'win' : 'pop')
        await wait(470)

        const multiplierChance = isFree ? 0.44 : 0.25
        const upgraded = [...activeMultipliers]
        removed.forEach((index) => {
          if (Math.random() < multiplierChance) {
            upgraded[index] =
              upgraded[index] > 0 ? Math.min(upgraded[index] * 2, 128) : 2
          }
        })
        activeMultipliers = upgraded
        multipliersRef.current = upgraded
        setMultipliers(upgraded)
        setWinning(new Set())

        activeBoard = collapseBoard(activeBoard, removed)
        setBoard(activeBoard)
        await wait(430)
        clusters = findClusters(activeBoard)
      }

      if (totalWin > 0) {
        const nextBalance = Math.round((balanceRef.current + totalWin) * 100) / 100
        balanceRef.current = nextBalance
        setBalance(nextBalance)
        setPhase(totalWin >= bet * 10 ? '¡PREMIO ESTELAR!' : 'PREMIO')
        if (totalWin >= bet * 10) {
          setBigWin(totalWin)
          playSound('bonus')
        }
      } else {
        setPhase('CASI… SIGUIENTE ÓRBITA')
      }

      if (scatterCount >= 3) {
        const awarded = scatterCount >= 4 ? 12 : 8
        setFreeSpins((current) => current + awarded)
        setToast(`¡${awarded} órbitas gratis activadas!`)
        playSound('bonus')
      }

      await wait(totalWin >= bet * 10 ? 900 : 350)
      setPhase(isFree ? 'MODO ÓRBITA' : 'LISTO PARA DESPEGAR')
      setBusy(false)
      busyRef.current = false
    },
    [bet, playSound],
  )

  useEffect(() => {
    if (busy) return
    let timer: number | undefined

    if (freeSpins > 0) {
      timer = window.setTimeout(() => {
        setFreeSpins((current) => Math.max(0, current - 1))
        void executeSpin(true)
      }, 700)
    } else if (autoSpins > 0) {
      timer = window.setTimeout(() => {
        setAutoSpins((current) => Math.max(0, current - 1))
        void executeSpin(false)
      }, 650)
    }

    return () => {
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [autoSpins, busy, executeSpin, freeSpins])

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (
        event.code === 'Space' &&
        !event.repeat &&
        !modal &&
        !(event.target instanceof HTMLButtonElement)
      ) {
        event.preventDefault()
        void executeSpin(false)
      }
      if (event.code === 'Escape') setModal(null)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [executeSpin, modal])

  const changeBet = (direction: -1 | 1) => {
    if (busy) return
    playSound('click')
    setBetIndex((current) =>
      Math.min(BETS.length - 1, Math.max(0, current + direction)),
    )
  }

  const buyBonus = () => {
    const cost = bet * 50
    if (balanceRef.current < cost) {
      setToast('Necesitas más saldo demo')
      setModal(null)
      return
    }
    const nextBalance = Math.round((balanceRef.current - cost) * 100) / 100
    balanceRef.current = nextBalance
    setBalance(nextBalance)
    const cleanMultipliers = Array<number>(ROWS * COLS).fill(0)
    multipliersRef.current = cleanMultipliers
    setMultipliers(cleanMultipliers)
    setFreeSpins(8)
    setModal(null)
    setToast('Portal abierto: 8 órbitas gratis')
    playSound('bonus')
  }

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void document.documentElement.requestFullscreen()
  }

  return (
    <div className="game-app">
      <div className="sky" aria-hidden="true">
        <span className="planet planet-one" />
        <span className="planet planet-two" />
        <span className="cloud cloud-one" />
        <span className="cloud cloud-two" />
        <div className="hills hills-back" />
        <div className="hills hills-front" />
        <span className="lollipop lollipop-one" />
        <span className="lollipop lollipop-two" />
      </div>

      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-orbit" aria-hidden="true">✦</span>
          <div>
            <strong>DULCE ÓRBITA</strong>
            <small>Cluster adventure</small>
          </div>
        </div>
        <div className="top-status">
          <span className="demo-pill">DEMO</span>
          <span className="online-dot" />
          <span>Conectado</span>
        </div>
      </header>

      <main className="game-stage">
        <aside className="side-panel mission-panel">
          <span className="eyebrow">MISIÓN ACTIVA</span>
          <div className="mission-orb">
            <span>{freeSpins}</span>
            <small>GRATIS</small>
          </div>
          <h2>Abre el portal</h2>
          <p>Consigue 3 cápsulas BONUS para entrar en la órbita multiplicadora.</p>
          <div className="scatter-track">
            {[0, 1, 2].map((item) => <span key={item}>✦</span>)}
          </div>
          <button
            className="bonus-button"
            type="button"
            onClick={() => setModal('bonus')}
            disabled={busy}
          >
            <small>ABRIR PORTAL</small>
            <strong>{money.format(bet * 50)} €</strong>
          </button>
        </aside>

        <section className="machine" aria-label="Dulce Órbita, juego de cascadas">
          <div className="machine-top">
            <span className="machine-light" />
            <div className="game-logo">
              <span>DULCE</span>
              <strong>ÓRBITA</strong>
              <small>∞ CASCADAS ∞</small>
            </div>
            <span className="machine-light" />
          </div>

          <div className="board-frame">
            <div className="board-glow" />
            <div
              className={`symbol-grid ${busy ? 'is-spinning' : ''}`}
              style={{ '--cols': COLS } as React.CSSProperties}
              role="grid"
              aria-label={`${ROWS} por ${COLS} símbolos`}
            >
              {board.map((cell, index) => (
                <div
                  className={`symbol-cell ${winning.has(index) ? 'is-winning' : ''}`}
                  key={cell.id}
                  role="gridcell"
                  aria-label={SYMBOL_META[cell.kind].label}
                  style={{ '--delay': `${(index % COLS) * 24}ms` } as React.CSSProperties}
                >
                  <CandyIcon kind={cell.kind} />
                  {multipliers[index] > 0 && (
                    <span className="multiplier-badge">×{multipliers[index]}</span>
                  )}
                  <span className="cell-spark" aria-hidden="true" />
                </div>
              ))}
            </div>
            <div className={`phase-banner ${lastWin > 0 ? 'has-win' : ''}`}>
              <span>{phase}</span>
              {lastWin > 0 && <strong>{money.format(lastWin)} €</strong>}
            </div>
          </div>

          <div className="control-deck">
            <div className="stat-block balance-stat">
              <span>SALDO DEMO</span>
              <strong>{money.format(balance)} €</strong>
            </div>

            <div className="bet-control">
              <button
                type="button"
                onClick={() => changeBet(-1)}
                disabled={busy || betIndex === 0}
                aria-label="Bajar apuesta"
              >−</button>
              <div>
                <span>APUESTA</span>
                <strong>{money.format(bet)} €</strong>
              </div>
              <button
                type="button"
                onClick={() => changeBet(1)}
                disabled={busy || betIndex === BETS.length - 1}
                aria-label="Subir apuesta"
              >+</button>
            </div>

            <button
              className={`spin-button ${busy ? 'is-busy' : ''}`}
              type="button"
              onClick={() => void executeSpin(false)}
              disabled={busy || freeSpins > 0}
              aria-label={busy ? 'Cascada en curso' : 'Girar'}
            >
              <span className="spin-arrow">↻</span>
              <small>{busy ? 'VIAJANDO' : 'GIRAR'}</small>
            </button>

            <button
              className={`deck-action ${autoSpins > 0 ? 'is-active' : ''}`}
              type="button"
              onClick={() => setAutoSpins((current) => (current > 0 ? 0 : 10))}
              disabled={busy && autoSpins === 0}
            >
              <span>∞</span>
              <small>{autoSpins > 0 ? `AUTO ${autoSpins}` : 'AUTO'}</small>
            </button>

            <button className="deck-action" type="button" onClick={() => setModal('rules')}>
              <span>i</span>
              <small>INFO</small>
            </button>
          </div>
        </section>

        <aside className="side-panel multiplier-panel">
          <span className="eyebrow">ENERGÍA CÓSMICA</span>
          <h2>Multiplicadores</h2>
          <div className="multiplier-orbit">
            {[2, 4, 8, 16, 32, 64, 128].map((value) => (
              <span key={value} className={`multi multi-${value}`}>×{value}</span>
            ))}
            <i className="orbit-core">✦</i>
          </div>
          <p>Cada explosión carga su casilla. En modo gratis, la energía permanece.</p>
          <div className="cascade-readout">
            <span>CASCADA</span>
            <strong>×{Math.max(1, cascade)}</strong>
          </div>
        </aside>
      </main>

      <div className="mobile-quickbar">
        <button type="button" onClick={() => setModal('bonus')}>
          <span>✦ BONUS</span>
          <strong>{money.format(bet * 50)} €</strong>
        </button>
        <div><span>GRATIS</span><strong>{freeSpins}</strong></div>
        <div><span>CASCADA</span><strong>×{Math.max(1, cascade)}</strong></div>
      </div>

      <footer className="utility-bar">
        <span>18+ · Ficción recreativa · Sin apuestas ni premios reales</span>
        <div>
          <button
            type="button"
            onClick={() => setMuted((current) => !current)}
            aria-label={muted ? 'Activar sonido' : 'Silenciar'}
          >{muted ? '🔇' : '🔊'}</button>
          <button type="button" onClick={toggleFullscreen} aria-label="Pantalla completa">⛶</button>
        </div>
      </footer>

      {toast && <div className="toast">{toast}</div>}

      {bigWin > 0 && (
        <button
          className="big-win"
          type="button"
          onClick={() => setBigWin(0)}
          aria-label="Cerrar celebración"
        >
          <span>✦</span>
          <small>PREMIO ESTELAR</small>
          <strong>{money.format(bigWin)} €</strong>
          <em>Toca para continuar</em>
        </button>
      )}

      {modal && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setModal(null)}>
          <section
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="modal-close" type="button" onClick={() => setModal(null)}>×</button>
            {modal === 'bonus' ? (
              <>
                <span className="modal-icon">✦</span>
                <small>PORTAL DE ÓRBITA</small>
                <h2 id="modal-title">Activa 8 giros gratis</h2>
                <p>Los multiplicadores permanecen entre cascadas durante toda la ronda.</p>
                <div className="purchase-price">
                  <span>Coste demo</span>
                  <strong>{money.format(bet * 50)} €</strong>
                </div>
                <button className="modal-primary" type="button" onClick={buyBonus}>
                  ABRIR PORTAL
                </button>
              </>
            ) : (
              <>
                <span className="modal-icon">?</span>
                <small>CÓMO JUGAR</small>
                <h2 id="modal-title">Agrupa, explota, repite</h2>
                <ul className="rules-list">
                  <li><b>5+ iguales</b> conectados pagan y desaparecen.</li>
                  <li>Los símbolos nuevos caen y pueden crear otra cascada.</li>
                  <li>Las casillas ganadoras pueden cargar multiplicadores.</li>
                  <li><b>3 BONUS</b> activan 8 órbitas gratis.</li>
                </ul>
                <p className="demo-note">Experiencia de entretenimiento. No usa ni entrega dinero real.</p>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

export default App
