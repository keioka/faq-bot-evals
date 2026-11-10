import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import Markdown, { type Components } from 'react-markdown'
import './App.css'

// version: the prompt version asked for (null = the server's default), reused by RETRY
type Turn =
  | { id: number; question: string; version: string | null; status: 'loading' }
  | { id: number; question: string; version: string | null; status: 'error'; message: string }
  | { id: number; question: string; version: string | null; status: 'done'; answer: string; servedBy: string }

type VersionInfo = { version: string; description: string }
type VersionsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; current: string; live: string; versions: VersionInfo[] }

// Each chip sends a full question the knowledge base can answer
const SUGGESTIONS = [
  { label: 'Sizing help', question: 'How do I find my shoe size?' },
  { label: 'Return policy', question: 'What is your return policy?' },
  { label: 'Return fees', question: 'How much does a return cost?' },
  { label: 'Duties & taxes', question: 'Are duties and taxes refunded when I return an item?' },
]
const TYPING_BARS = [0, 1, 2, 3, 4]

const ERROR_MESSAGES: Record<number, string> = {
  422: 'Please enter a question (up to 1,000 characters).',
  502: "Couldn't get an answer right now. Please try again.",
}
const FALLBACK_ERROR = "Something went wrong and we couldn't get an answer. Please try again."

// Open bot links (e.g. the Global-e contact page) in a new tab
const MARKDOWN_COMPONENTS: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

async function askBot(question: string, version: string | null): Promise<{ answer: string; version: string }> {
  if (!navigator.onLine) throw new Error("You're offline. Check your connection and try again.")
  let response: Response
  try {
    response = await fetch('/api/faq', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, version }),
    })
  } catch {
    throw new Error("Couldn't reach the server. Check your connection and try again.")
  }
  if (!response.ok) throw new Error(ERROR_MESSAGES[response.status] ?? FALLBACK_ERROR)
  return response.json()
}

async function fetchVersions(signal: AbortSignal): Promise<{ default: string; live: string; versions: VersionInfo[] }> {
  const response = await fetch('/api/versions', { signal })
  if (!response.ok) throw new Error(`versions request failed: ${response.status}`)
  return response.json()
}

function App() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [versions, setVersions] = useState<VersionsState>({ status: 'loading' })
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null) // null = server default

  // Load the registry versions for the selector (syncs with the backend)
  useEffect(() => {
    const controller = new AbortController()
    fetchVersions(controller.signal)
      .then(data => setVersions({ status: 'ready', current: data.default, live: data.live, versions: data.versions }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return // unmounted or StrictMode re-run: not a real failure
        console.error('versions request failed', error)
        setVersions({ status: 'error' })
      })
    return () => controller.abort()
  }, [])
  const isSending = turns.some(turn => turn.status === 'loading')
  const lastStatus = turns.at(-1)?.status

  // Keep the newest message in view (syncs with the browser's scroll position)
  useEffect(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }, [turns.length, lastStatus])

  async function send(id: number, question: string, version: string | null): Promise<void> {
    setTurns(prev => upsert(prev, { id, question, version, status: 'loading' }))
    try {
      const result = await askBot(question, version)
      setTurns(prev => upsert(prev, { id, question, version, status: 'done', answer: result.answer, servedBy: result.version }))
    } catch (error) {
      console.error('faq request failed', error) // real error for the log; the user sees the friendly message
      const message = error instanceof Error ? error.message : FALLBACK_ERROR
      setTurns(prev => upsert(prev, { id, question, version, status: 'error', message }))
    }
  }

  function ask(question: string): void {
    const trimmed = question.trim()
    if (!trimmed || isSending) return
    setDraft('')
    void send(Date.now(), trimmed, selectedVersion)
  }

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    ask(draft)
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    setDraft(event.target.value)
  }

  function handleVersionChange(event: ChangeEvent<HTMLSelectElement>): void {
    setSelectedVersion(event.target.value)
  }

  return (
    <div className="page">
      <header className="topbar">
        <span className="wordmark">FAQ ASSISTANT</span>
        <VersionSelect state={versions} value={selectedVersion} onChange={handleVersionChange} />
      </header>
      <main className="chat">
        {turns.length === 0 ? (
          <section className="hero">
            <h1>Store questions, answered.</h1>
            <p>Ask about sizing, returns, fees, or store terms.</p>
          </section>
        ) : null}
        <ol className="turns" aria-live="polite">
          {turns.map(turn => (
            <TurnItem key={turn.id} turn={turn} onRetry={send} />
          ))}
        </ol>
      </main>
      <footer className="composer">
        <div className="composer-inner">
          <div className="chips">
            {SUGGESTIONS.map(s => (
              <SuggestionChip key={s.label} label={s.label} question={s.question} disabled={isSending} onAsk={ask} />
            ))}
          </div>
          <form className="prompt" onSubmit={handleSubmit}>
            <span className="prompt-mark" aria-hidden="true">
              &gt;
            </span>
            <label htmlFor="question" className="visually-hidden">
              Your question
            </label>
            <input id="question" value={draft} onChange={handleChange} placeholder="Ask anything…" maxLength={1000} autoComplete="off" />
            <button type="submit" disabled={isSending}>
              SEND
            </button>
          </form>
        </div>
      </footer>
    </div>
  )
}

function VersionSelect({
  state,
  value,
  onChange,
}: {
  state: VersionsState
  value: string | null
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void
}) {
  if (state.status === 'loading') return <span className="version-note">Loading versions…</span>
  if (state.status === 'error') {
    return <span className="version-note">Couldn't load versions · using the live prompt</span>
  }
  return (
    <div className="version-select">
      <label htmlFor="version">PROMPT</label>
      {/* Until the user picks one, show the version the server answers with by default (the current version) */}
      <select id="version" value={value ?? state.current} onChange={onChange}>
        {state.versions.map(v => (
          <option key={v.version} value={v.version}>
            {v.version} · {v.description}
            {v.version === state.live ? ' (live)' : ''}
          </option>
        ))}
      </select>
    </div>
  )
}

function SuggestionChip({
  label,
  question,
  disabled,
  onAsk,
}: {
  label: string
  question: string
  disabled: boolean
  onAsk: (question: string) => void
}) {
  function handleClick(): void {
    onAsk(question)
  }
  return (
    <button type="button" className="chip" disabled={disabled} onClick={handleClick}>
      {label}
    </button>
  )
}

function TurnItem({
  turn,
  onRetry,
}: {
  turn: Turn
  onRetry: (id: number, question: string, version: string | null) => Promise<void>
}) {
  function handleRetry(): void {
    void onRetry(turn.id, turn.question, turn.version)
  }
  return (
    <li className="turn">
      <div className="message message--user">
        <span className="label">YOU</span>
        <p className="bubble">{turn.question}</p>
      </div>
      {turn.status === 'loading' ? (
        <div className="message message--bot">
          <span className="label label--accent">ASSIST / PROCESSING</span>
          <div className="bubble typing" role="status" aria-label="Answering">
            {TYPING_BARS.map(bar => (
              <span key={bar} className="bar" />
            ))}
          </div>
        </div>
      ) : null}
      {turn.status === 'error' ? (
        <div className="message message--bot" role="alert">
          <span className="label label--danger">ASSIST / ERROR</span>
          <div className="bubble bubble--error">
            <p>
              <span aria-hidden="true">⚠ </span>
              {turn.message}
            </p>
            <button type="button" className="chip chip--danger" onClick={handleRetry}>
              RETRY
            </button>
          </div>
        </div>
      ) : null}
      {turn.status === 'done' ? (
        <div className="message message--bot">
          <span className="label label--accent">ASSIST · PROMPT {turn.servedBy.toUpperCase()}</span>
          <div className="bubble">
            <Markdown components={MARKDOWN_COMPONENTS}>{turn.answer}</Markdown>
          </div>
        </div>
      ) : null}
    </li>
  )
}

function upsert(turns: Turn[], next: Turn): Turn[] {
  return turns.some(turn => turn.id === next.id)
    ? turns.map(turn => (turn.id === next.id ? next : turn))
    : [...turns, next]
}

export default App
