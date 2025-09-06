import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Citation = { id: string; title?: string; source?: string; post_id?: string | null }
type Policy = { refusal: boolean; masked: boolean; pii_types: string[]; reason: string }

type Message = { role: 'user' | 'assistant'; content: string; citations?: Citation[]; policy?: Policy }

const ChatApp: React.FC = () => {
  const RAG_BASE = useMemo(() => import.meta.env.VITE_RAG_BASE || 'http://localhost:8001', [])
  const ETL_BASE = useMemo(() => import.meta.env.VITE_ETL_BASE || 'http://localhost:8002', [])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCitations, setShowCitations] = useState(true)
  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    if (!input.trim() || streaming) return
    setError(null)
    const user = { role: 'user' as const, content: input }
    setMessages(m => [...m, user, { role: 'assistant', content: '' }])
    setInput('')
    setStreaming(true)
    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const res = await fetch(`${RAG_BASE}/rag/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: user.content, top_k: 8, enforce_policy: true }),
        signal: ctrl.signal,
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += dec.decode(value, { stream: true })
        // parse SSE chunks
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        for (const chunk of parts) {
          const line = chunk.trim()
          if (!line) continue
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            setMessages(m => {
              const copy = [...m]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') last.content += data
              return copy
            })
          } else if (line.startsWith('event: citations')) {
            // next part should be data: json
            // handled when iteration reaches it
          } else if (line.startsWith('data:{') || line.startsWith('data: {')) {
            try {
              const obj = JSON.parse(line.slice(5))
              if (Array.isArray(obj)) {
                setMessages(m => {
                  const copy = [...m]
                  const last = copy[copy.length - 1]
                  if (last && last.role === 'assistant') (last as any).citations = obj
                  return copy
                })
              }
            } catch {}
          }
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') setError(e?.message || String(e))
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const stop = () => {
    abortRef.current?.abort()
  }

  return (
    <div className="min-h-screen flex">
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="font-semibold">HanaNavi Chatbot</div>
          <div className="text-sm text-gray-500">RAG • Policy Guard</div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-3 py-2 whitespace-pre-wrap prose prose-sm ${m.role==='user'?'bg-blue-600 text-white':'bg-white border'}`}>
                  {m.role==='assistant' ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                      a: props => <a {...props} target="_blank"/>,
                      code: ({inline, className, children, ...props}) => (
                        <code className={`bg-gray-100 px-1 rounded ${className||''}`} {...props}>{children}</code>
                      ),
                    }}>{m.content || (idx===messages.length-1 && streaming ? '...' : '')}</ReactMarkdown>
                  ) : (
                    <span>{m.content}</span>
                  )}
                </div>
              </div>
            ))}
            <div ref={endRef} />
            {error && <div className="text-red-600 text-sm">에러: {error}</div>}
          </div>
        </main>
        <footer className="border-t bg-white">
          <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-2">
            <input className="flex-1" value={input} onChange={e=>setInput(e.target.value)} placeholder="질문을 입력하세요" onKeyDown={e=>{ if(e.key==='Enter') send() }} />
            {!streaming ? (
              <button onClick={send} disabled={!input.trim()}>전송</button>
            ) : (
              <button className="bg-gray-600" onClick={stop}>중지</button>
            )}
          </div>
        </footer>
      </div>
      <aside className="w-[320px] border-l bg-gray-50 hidden md:block">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="font-medium">출처</div>
          <label className="text-sm flex items-center gap-1">
            <input type="checkbox" checked={showCitations} onChange={e=>setShowCitations(e.target.checked)} /> 표시
          </label>
        </div>
        {showCitations ? (
          <div className="px-4 pb-6 space-y-2 overflow-y-auto max-h-[calc(100vh-60px)]">
            {messages.filter(m=>m.role==='assistant').map((m, i) => (
              <div key={i} className="bg-white border rounded p-2">
                <div className="text-xs text-gray-500 mb-1">답변 {i+1}</div>
                <ul className="space-y-1 text-sm">
                  {(m.citations||[]).map((c, j) => (
                    <li key={j} className="flex justify-between gap-2">
                      <span className="truncate">[{j+1}] {c.title || c.id}</span>
                      {c.post_id && <a className="text-blue-600" href={`${ETL_BASE}/posts/${c.post_id}/attachments`} target="_blank" rel="noreferrer">보기</a>}
                    </li>
                  ))}
                  {(m.citations||[]).length===0 && <li className="text-gray-500">(없음)</li>}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-4 text-sm text-gray-500">숨김</div>
        )}
      </aside>
    </div>
  )
}

export default ChatApp

