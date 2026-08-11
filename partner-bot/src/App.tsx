import { useState } from 'react'
import { SelectField, TextField, Button, View, Authenticator } from '@aws-amplify/ui-react'
import { fetchAuthSession } from 'aws-amplify/auth'
import './App.css'

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
  meta: object
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
  const [answer, setAnswer] = useState<string | null>(null)

  async function handleSubmit() {
    if (!question || !company || !year || !period) {
      setError("Please fill in all fields before submitting.")
      return
    }

    setLoading(true)
    setError(null)
    setAnswer(null)

    const body: RequestBody = {
      question: question,
      ticker: COMPANIES[company],
      year: Number(year),
      period: period,
    }

    try {
      const result = await submitQuery(body)
      setAnswer(result.answer)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <>
          <p>Signed in as {user?.signInDetails?.loginId}</p>
          <Button onClick={signOut}>Sign out</Button>

          <TextField
            descriptiveText="Ask your question"
            placeholder="What was the earnings?"
            label="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />

          <SelectField
            label="company"
            placeholder="Select a company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            descriptiveText="What company are you searching for?"
          >
            {Object.keys(COMPANIES).map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </SelectField>

          <SelectField
            label="year"
            placeholder="Select a year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            descriptiveText="Which fiscal year?"
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </SelectField>

          <SelectField
            label="period"
            placeholder="Select a period"
            value={period}
            descriptiveText="What period?"
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="Q1">Q1</option>
            <option value="Q2">Q2</option>
            <option value="Q3">Q3</option>
            <option value="Q4">Q4</option>
            <option value="FY">FY</option>
          </SelectField>

          <Button onClick={handleSubmit} isLoading={loading} loadingText="Thinking...">
            Submit
          </Button>

          {error && (
            <View backgroundColor="red.10" padding="1rem" marginTop="1rem">
              {error}
            </View>
          )}

          {answer && (
            <View backgroundColor="neutral.10" padding="1rem" marginTop="1rem">
              {answer}
            </View>
          )}
        </>
      )}
    </Authenticator>
  )
}

export default App