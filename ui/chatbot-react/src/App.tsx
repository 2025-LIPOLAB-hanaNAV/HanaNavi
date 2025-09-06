import React, { useMemo, useState } from 'react'

type Citation = { id: string; title?: string; source?: string; post_id?: string | null }
type Policy = { refusal: boolean; masked: boolean; pii_types: string[]; reason: string }
type RagResponse = { answer: string; citations: Citation[]; policy: Policy }

type Attachment = { filename: string; public_url: string; sha1?: string }

const App: React.FC = () => {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [citations, setCitations] = useState<Citation[]>([])
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<{ postId: string; attachments: Attachment[] } | null>(null)
  const [activeTab, setActiveTab] = useState<'질문' | '답변' | '출처'>('질문')
  const [vote, setVote] = useState<'up' | 'down' | null>(null)

  // Filters
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [category, setCategory] = useState('')
  const [filetype, setFiletype] = useState('')

  const RAG_BASE = useMemo(() => import.meta.env.VITE_RAG_BASE || 'http://localhost:8001', [])
  const ETL_BASE = useMemo(() => import.meta.env.VITE_ETL_BASE || 'http://localhost:8002', [])

  const send = async () => {
    setLoading(true)
    setError(null)
    setPreview(null)
    try {
      const res = await fetch(`${RAG_BASE}/rag/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          top_k: 8,
          enforce_policy: true,
          filters: {
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            category: category || undefined,
            filetype: filetype || undefined,
          },
        }),
      })
      if (!res.ok) throw new Error(`RAG failed: ${res.status}`)
      const data: RagResponse = await res.json()
      setAnswer(data.answer)
      setCitations(data.citations)
      setPolicy(data.policy)
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const openPreview = async (postId?: string | null) => {
    if (!postId) return
    try {
      const res = await fetch(`${ETL_BASE}/posts/${postId}/attachments`)
      if (!res.ok) throw new Error(`attachments failed: ${res.status}`)
      const data = await res.json()
      setPreview({ postId, attachments: data.attachments as Attachment[] })
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '20px auto', fontFamily: 'sans-serif' }}>
      <h2>Chatbot</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={query} onChange={e => setQuery(e.target.value)} style={{ flex: 1 }} placeholder="질문을 입력하세요" />
        <button disabled={loading || !query.trim()} onClick={send}>{loading ? '질의 중...' : '질의'}</button>
      </div>
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(4, 1fr)', marginTop: 8 }}>
        <input value={dateFrom} onChange={e => setDateFrom(e.target.value)} placeholder="시작일 YYYY-MM-DD" />
        <input value={dateTo} onChange={e => setDateTo(e.target.value)} placeholder="종료일 YYYY-MM-DD" />
        <input value={category} onChange={e => setCategory(e.target.value)} placeholder="카테고리" />
        <input value={filetype} onChange={e => setFiletype(e.target.value)} placeholder="파일타입(pdf/xlsx/docx)" />
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        {(['질문', '답변', '출처'] as const).map(t => (
          <button key={t} onClick={() => setActiveTab(t)} disabled={activeTab === t}>{t}</button>
        ))}
      </div>

      {error && <p style={{ color: 'red' }}>에러: {error}</p>}

      {answer && activeTab === '답변' && (
        <div style={{ marginTop: 16 }}>
          <h3>답변</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{answer}</pre>
          {policy && (
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
              정책: refusal={String(policy.refusal)}, masked={String(policy.masked)}, types={policy.pii_types?.join(',') || '-'}{policy.reason ? `, reason=${policy.reason}` : ''}
            </div>
          )}
          <div style={{ marginTop: 8 }}>
            피드백: {' '}
            <button onClick={async () => {
              setVote('up')
              await fetch(`${RAG_BASE}/feedback`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, answer: answer!, citations, policy, vote: 'up' })
              })
            }}>👍</button>
            {' '}
            <button onClick={async () => {
              setVote('down')
              await fetch(`${RAG_BASE}/feedback`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, answer: answer!, citations, policy, vote: 'down' })
              })
            }}>👎</button>
            {vote && <span style={{ marginLeft: 8, fontSize: 12 }}>감사합니다! ({vote})</span>}
          </div>
        </div>
      )}

      {citations.length > 0 && activeTab === '출처' && (
        <div style={{ marginTop: 16 }}>
          <h3>출처</h3>
          <ul>
            {citations.map((c, i) => (
              <li key={i}>
                [{i + 1}] {c.title || c.id} <small>{c.source}</small>
                {' '}
                {c.post_id && <button onClick={() => openPreview(c.post_id)}>미리보기</button>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {preview && activeTab === '출처' && (
        <div style={{ marginTop: 16, borderTop: '1px solid #ddd', paddingTop: 12 }}>
          <h3>첨부 미리보기 (post_id: {preview.postId})</h3>
          {preview.attachments.length === 0 && <p>첨부 없음</p>}
          {preview.attachments.map((a, idx) => {
            const lower = a.filename.toLowerCase()
            const isPdf = lower.endsWith('.pdf')
            const isXlsx = lower.endsWith('.xlsx') || lower.endsWith('.xlsm')
            return (
              <div key={idx} style={{ marginBottom: 12 }}>
                <div>
                  <strong>{a.filename}</strong> {' '}<a href={a.public_url} target="_blank" rel="noreferrer">새창에서 열기</a>
                </div>
                {isPdf && <PdfPreview url={a.public_url} />}
                {isXlsx && <XlsxPreview apiBase={ETL_BASE} filename={a.filename} />}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default App

const PdfPreview: React.FC<{ url: string }> = ({ url }) => {
  const [page, setPage] = useState(1)
  const src = `${url}#page=${page}`
  return (
    <div>
      <div style={{ margin: '6px 0' }}>
        페이지: <input type="number" min={1} value={page} onChange={e => setPage(Math.max(1, Number(e.target.value)))} style={{ width: 80 }} />
      </div>
      <iframe src={src} title={`pdf-${page}`} style={{ width: '100%', height: 480, border: '1px solid #ccc' }} />
    </div>
  )
}

const XlsxPreview: React.FC<{ apiBase: string, filename: string }> = ({ apiBase, filename }) => {
  const [range, setRange] = useState('A1:D20')
  const [sheet, setSheet] = useState('')
  const [rows, setRows] = useState<string[][] | null>(null)
  const [loading, setLoading] = useState(false)
  const load = async () => {
    setLoading(true)
    try {
      const qs = new URLSearchParams({ filename, range, ...(sheet ? { sheet } : {}) })
      const res = await fetch(`${apiBase}/preview/xlsx?${qs.toString()}`)
      const data = await res.json()
      setRows(data.rows)
      if (!sheet) setSheet(data.sheet)
    } finally {
      setLoading(false)
    }
  }
  return (
    <div>
      <div style={{ margin: '6px 0', display: 'flex', gap: 8 }}>
        <input value={sheet} onChange={e => setSheet(e.target.value)} placeholder="시트명(옵션)" />
        <input value={range} onChange={e => setRange(e.target.value)} placeholder="범위 (예: A1:D20)" />
        <button onClick={load} disabled={loading}>{loading ? '로딩...' : '가져오기'}</button>
      </div>
      {rows && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td key={j} style={{ border: '1px solid #ccc', padding: 4 }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
