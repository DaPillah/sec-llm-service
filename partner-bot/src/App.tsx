import { useState } from 'react'
import { fetchAuthSession } from 'aws-amplify/auth'
import './App.css'
import { Authenticator, ThemeProvider, createTheme } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import ReactMarkdown from 'react-markdown'


const theme = createTheme({
  name: 'edgar-theme',
  tokens: {
    colors: {
      background: {
        primary: { value: '#0E1420' },
        secondary: { value: '#161D2C' },
      },
      font: {
        primary: { value: '#E8E6DD' },
        secondary: { value: '#6B7488' },
        interactive: { value: '#E0A458' },
      },
      border: {
        primary: { value: '#2A3B5C' },
        secondary: { value: '#2A3B5C' },
        focus: { value: '#E0A458' },
      },
      brand: {
        primary: {
          10: { value: '#20180E' },
          80: { value: '#E0A458' },
          90: { value: '#E0A458' },
          100: { value: '#E0A458' },
        },
      },
    },
    components: {
      authenticator: {
        router: {
          backgroundColor: { value: '#161D2C' },
          borderColor: { value: '#2A3B5C' },
          boxShadow: { value: '0 20px 40px -20px rgba(0,0,0,0.5)' },
        },
      },
      tabs: {
        item: {
          color: { value: '#6B7488' },
          _active: {
            color: { value: '#E0A458' },
            borderColor: { value: '#E0A458' },
          },
        },
      },
      fieldcontrol: {
        borderColor: { value: '#2A3B5C' },
        color: { value: '#E8E6DD' },
        _focus: { borderColor: { value: '#E0A458' } },
      },
      button: {
        primary: {
          backgroundColor: { value: '#E0A458' },
          color: { value: '#14171F' },
          _hover: { backgroundColor: { value: '#D89448' } },
        },
        link: {
          color: { value: '#E0A458' },
        },
      },
    },
  },
})

const COMPANIES: Record<string, string> = {
  Apple: "AAPL",
  Amazon: "AMZN",
  Microsoft: "MSFT",
}
const currentYear = new Date().getFullYear()
const years = Array.from({ length: 5 }, (_, i) => currentYear - i)

type RequestBody = {
  question: string
  ticker: string
  year: number
  period: string
}

type ResponseBody = {
  answer: string
  meta: {
    model?: string
    input_tokens?: number
    output_tokens?: number
    latency_ms?: number
  }
}

async function submitQuery(body: RequestBody): Promise<ResponseBody> {
  const { tokens } = await fetchAuthSession()
  const idToken = tokens?.idToken?.toString() ?? ""

  const response = await fetch(import.meta.env.VITE_INFERENCE_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: idToken,
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorBody = await response.json()
    throw new Error(errorBody.message ?? `Request failed with status ${response.status}`)
  }

  return response.json()
}

function App() {
  const [question, setQuestion] = useState("")
  const [company, setCompany] = useState("")
  const [year, setYear] = useState("")
  const [period, setPeriod] = useState("")

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResponseBody | null>(null)
  const [filedFor, setFiledFor] = useState<{ ticker: string; period: string; year: string } | null>(null)

  async function handleSubmit() {
    if (!question || !company || !year || !period) {
      setError("All fields are required before a request can be filed.")
      setResult(null)
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const ticker = COMPANIES[company]
    const body: RequestBody = { question, ticker, year: Number(year), period }

    try {
      const data = await submitQuery(body)
      setResult(data)
      setFiledFor({ ticker, period, year })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <ThemeProvider theme={theme}>
      <Authenticator>
        {({ signOut, user }) => (
          <div className="edgar">
            <header className="edgar-bar">
              <span className="edgar-wordmark">EDGAR // ANALYZER</span>
              <div className="edgar-session">
                <span className="edgar-user">{user?.signInDetails?.loginId}</span>
                <button className="edgar-signout" onClick={signOut}>sign out</button>
              </div>
            </header>

            <main className="edgar-body">
              <section className="filing-form">
                <h1 className="form-title">Form 10-Q / 10-K Request</h1>
                <div className="rule" />

                <label className="field">
                  <span className="field-label">Company</span>
                  <select className="field-input" value={company} onChange={(e) => setCompany(e.target.value)}>
                    <option value="">— select —</option>
                    {Object.keys(COMPANIES).map((name) => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Fiscal year</span>
                  <select className="field-input" value={year} onChange={(e) => setYear(e.target.value)}>
                    <option value="">— select —</option>
                    {years.map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Period</span>
                  <select className="field-input" value={period} onChange={(e) => setPeriod(e.target.value)}>
                    <option value="">— select —</option>
                    {["Q1", "Q2", "Q3", "Q4", "FY"].map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Question</span>
                  <input
                    className="field-input"
                    type="text"
                    placeholder="What was the earnings this quarter?"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                </label>

                <button className="submit-btn" onClick={handleSubmit} disabled={loading}>
                  {loading ? "Filing…" : "Submit request →"}
                </button>
              </section>

              {error && (
                <section key={error} className="receipt receipt--error">
                  <div className="stamp stamp--pending">REJECTED</div>
                  <p className="receipt-body">{error}</p>
                </section>
              )}

              {result && filedFor && (
                <section key={result.answer} className="receipt">
                  <div className="stamp stamp--filed">FILED</div>
                  <div className="receipt-head">
                    {filedFor.ticker} · {filedFor.period} FY{filedFor.year}
                  </div>
                  <div className="rule rule--tight" />
                  <div className="receipt-body">
                    <ReactMarkdown>{result.answer}</ReactMarkdown>
                  </div>
                  <div className="rule rule--tight" />
                  <dl className="receipt-meta">
                    <div><dt>model</dt><dd>{result.meta.model ?? "—"}</dd></div>
                    <div>
                      <dt>tokens</dt>
                      <dd>{result.meta.input_tokens ?? "—"} in · {result.meta.output_tokens ?? "—"} out</dd>
                    </div>
                    <div>
                      <dt>latency</dt>
                      <dd>{result.meta.latency_ms ? `${(result.meta.latency_ms / 1000).toFixed(1)}s` : "—"}</dd>
                    </div>
                  </dl>
                </section>
              )}
            </main>
          </div>
        )}
      </Authenticator>
    </ThemeProvider>
  )
}

export default App