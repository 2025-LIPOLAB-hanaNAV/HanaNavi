import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Citation = { id: string; title?: string; source?: string; post_id?: string | null; snippet?: string; highlighted_snippet?: string }
type Policy = { refusal: boolean; masked: boolean; pii_types: string[]; reason: string }

type Message = { role: 'user' | 'assistant'; content: string; citations?: Citation[]; policy?: Policy }

const ChatApp: React.FC = () => {
  const RAG_BASE = useMemo(() => import.meta.env.VITE_RAG_BASE || 'http://localhost:8001', [])
  const ETL_BASE = useMemo(() => import.meta.env.VITE_ETL_BASE || 'http://localhost:8002', [])
  const BOARD_BASE = useMemo(() => import.meta.env.VITE_BOARD_BASE || 'http://localhost:5173', [])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCitations, setShowCitations] = useState(true)
  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState<string>(() => localStorage.getItem('hn_model') || '')
  const [pullTarget, setPullTarget] = useState('')
  const [pulling, setPulling] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    const refresh = async () => {
      try {
        setLoadingModels(true)
        const r = await fetch(`${RAG_BASE}/llm/models`)
        if (r.ok) {
          const data = await r.json()
          const items = (data?.models || []) as string[]
          setModels(items)
          if (!selectedModel && items.length > 0) {
            setSelectedModel(items[0])
            localStorage.setItem('hn_model', items[0])
          }
        }
      } finally {
        setLoadingModels(false)
      }
    }
    refresh().catch(()=>{})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
      const history = messages
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(m => ({ role: m.role, content: m.content }))
      const res = await fetch(`${RAG_BASE}/rag/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: user.content, top_k: 8, enforce_policy: true, history, model: selectedModel || undefined }),
        signal: ctrl.signal,
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buffer = ''
      let pendingEvent: string | null = null
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += dec.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const ev of chunks) {
          const lines = ev.split('\n').map(l => l.trim()).filter(Boolean)
          let eventName: string | null = null
          let dataPayload: string | null = null
          for (const l of lines) {
            if (l.startsWith('event:')) eventName = l.slice(6).trim()
            if (l.startsWith('data:')) dataPayload = (dataPayload || '') + l.slice(5)
          }
          if (eventName) pendingEvent = eventName
          if (!dataPayload) continue
          // Citations event delivers JSON array; default data lines are text deltas
          if ((pendingEvent === 'citations') || (dataPayload.startsWith('[') || dataPayload.startsWith('{'))) {
            try {
              const obj = JSON.parse(dataPayload)
              if (Array.isArray(obj)) {
                setMessages(m => {
                  const copy = [...m]
                  const last = copy[copy.length - 1]
                  if (last && last.role === 'assistant') (last as any).citations = obj
                  return copy
                })
              }
            } catch {
              // ignore parse errors
            }
            pendingEvent = null
          } else {
            const data = dataPayload
            setMessages(m => {
              const copy = [...m]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') last.content += data
              return copy
            })
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
        <header className="bg-white border-b px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="font-semibold">HanaNavi Chatbot</div>
            <div className="text-sm text-gray-500">RAG • Policy Guard</div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="text-sm text-gray-600">모델</label>
            <select className="min-w-[200px]" value={selectedModel} onChange={e=>{ setSelectedModel(e.target.value); localStorage.setItem('hn_model', e.target.value) }}>
              <option value="">(직접 입력 또는 Pull)</option>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button className="bg-gray-600" onClick={async ()=>{
              try { setLoadingModels(true); const r = await fetch(`${RAG_BASE}/llm/models`); if(r.ok){ const d = await r.json(); setModels(d?.models||[]) } } finally { setLoadingModels(false) }
            }} disabled={loadingModels}>{loadingModels? '갱신중...' : '목록 갱신'}</button>
            <input className="w-64" placeholder="모델명 입력 (예: qwen2:7b)" value={pullTarget} onChange={e=>setPullTarget(e.target.value)} />
            <button onClick={async ()=>{
              if(!pullTarget.trim()) return
              setPulling(true); setError(null)
              try { const r = await fetch(`${RAG_BASE}/llm/pull`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ model: pullTarget.trim() }) }); if(!r.ok) throw new Error(`pull failed: ${r.status}`); setSelectedModel(pullTarget.trim()); localStorage.setItem('hn_model', pullTarget.trim()); } catch(e:any){ setError(e?.message||String(e)) } finally { setPulling(false) }
            }} disabled={pulling}>{pulling? 'Pull 중...' : 'Pull'}</button>
          </div>
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
                <ul className="space-y-3 text-sm">
                  {(m.citations||[]).map((c, j) => (
                    <li key={j} className="border-b border-gray-100 pb-2">
                      <div className="flex justify-between gap-2 mb-1">
                        <span className="truncate font-medium">[{j+1}] {c.title || c.id}</span>
                        {c.post_id && (
                          <div className="flex gap-1">
                            <a className="text-blue-600 text-xs" href={`${BOARD_BASE}/post/${c.post_id}`} target="_blank" rel="noreferrer">게시글</a>
                            <a className="text-blue-600 text-xs" href={`${ETL_BASE}/posts/${c.post_id}/attachments`} target="_blank" rel="noreferrer">첨부</a>
                          </div>
                        )}
                      </div>
                      {c.highlighted_snippet && (
                        <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                            p: ({children}) => <span>{children}</span>,
                            strong: ({children}) => <mark className="bg-yellow-200 px-1 rounded">{children}</mark>
                          }}>
                            {c.highlighted_snippet}
                          </ReactMarkdown>
                        </div>
                      )}
                      {c.source && (
                        <div className="text-xs text-gray-400 mt-1 truncate">{c.source}</div>
                      )}
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
