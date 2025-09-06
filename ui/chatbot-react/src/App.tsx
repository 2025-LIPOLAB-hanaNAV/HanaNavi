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
        body: JSON.stringify({ query, top_k: 8, enforce_policy: true }),
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

      {error && <p style={{ color: 'red' }}>에러: {error}</p>}

      {answer && (
        <div style={{ marginTop: 16 }}>
          <h3>답변</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{answer}</pre>
          {policy && (
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
              정책: refusal={String(policy.refusal)}, masked={String(policy.masked)}, types={policy.pii_types?.join(',') || '-'}{policy.reason ? `, reason=${policy.reason}` : ''}
            </div>
          )}
        </div>
      )}

      {citations.length > 0 && (
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

      {preview && (
        <div style={{ marginTop: 16, borderTop: '1px solid #ddd', paddingTop: 12 }}>
          <h3>첨부 미리보기 (post_id: {preview.postId})</h3>
          {preview.attachments.length === 0 && <p>첨부 없음</p>}
          {preview.attachments.map((a, idx) => {
            const lower = a.filename.toLowerCase()
            const isPdf = lower.endsWith('.pdf')
            return (
              <div key={idx} style={{ marginBottom: 12 }}>
                <div>
                  <strong>{a.filename}</strong> {' '}<a href={a.public_url} target="_blank" rel="noreferrer">새창에서 열기</a>
                </div>
                {isPdf && (
                  <iframe src={a.public_url} title={a.filename} style={{ width: '100%', height: 480, border: '1px solid #ccc' }} />
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default App

