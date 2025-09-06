import React, { useMemo, useState } from 'react'

type UploadInfo = {
  filename: string
  sha1: string
  url: string
  public_url: string
  size: number
  content_type: string
}

type Attachment = {
  filename: string
  url: string
  sha1?: string
}

const App: React.FC = () => {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState('')
  const [category, setCategory] = useState('')
  const [date, setDate] = useState('')
  const [severity, setSeverity] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [uploads, setUploads] = useState<UploadInfo[]>([])
  const [posting, setPosting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ETL_BASE = useMemo(() => import.meta.env.VITE_ETL_BASE || 'http://localhost:8002', [])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFiles(e.target.files)
  }

  const uploadFile = async (file: File): Promise<UploadInfo> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${ETL_BASE}/upload`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) throw new Error(`upload failed: ${res.status}`)
    return res.json()
  }

  const submitPost = async () => {
    setError(null)
    setTaskId(null)
    setPosting(true)
    try {
      let atts: Attachment[] = []
      if (files && files.length > 0) {
        const results: UploadInfo[] = []
        for (let i = 0; i < files.length; i++) {
          // eslint-disable-next-line no-await-in-loop
          const up = await uploadFile(files[i])
          results.push(up)
        }
        setUploads(results)
        atts = results.map(r => ({ filename: r.filename, url: r.url, sha1: r.sha1 }))
      }

      const event = {
        action: 'post_created',
        post_id: Date.now(),
        title,
        body,
        tags: tags ? tags.split(',').map(s => s.trim()).filter(Boolean) : [],
        category,
        date,
        severity,
        attachments: atts,
      }

      const res = await fetch(`${ETL_BASE}/ingest/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      })
      if (!res.ok) throw new Error(`post failed: ${res.status}`)
      const data = await res.json()
      setTaskId(data.task_id || null)
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setPosting(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '20px auto', fontFamily: 'sans-serif' }}>
      <h2>게시판 글 작성 (MVP)</h2>
      <div style={{ display: 'grid', gap: 12 }}>
        <label>
          제목
          <input value={title} onChange={e => setTitle(e.target.value)} style={{ width: '100%' }} />
        </label>
        <label>
          본문
          <textarea value={body} onChange={e => setBody(e.target.value)} rows={8} style={{ width: '100%' }} />
        </label>
        <label>
          태그(쉼표 구분)
          <input value={tags} onChange={e => setTags(e.target.value)} style={{ width: '100%' }} />
        </label>
        <label>
          카테고리
          <input value={category} onChange={e => setCategory(e.target.value)} style={{ width: '100%' }} />
        </label>
        <label>
          게시일(YYYY-MM-DD)
          <input value={date} onChange={e => setDate(e.target.value)} placeholder="2025-09-06" />
        </label>
        <label>
          중요도(severity)
          <input value={severity} onChange={e => setSeverity(e.target.value)} placeholder="low|medium|high" />
        </label>
        <label>
          첨부파일
          <input type="file" multiple onChange={onFileChange} />
        </label>
        <button disabled={posting} onClick={submitPost}>{posting ? '전송 중...' : '등록'}</button>
      </div>

      {uploads.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3>업로드된 첨부</h3>
          <ul>
            {uploads.map((u, i) => (
              <li key={i}>
                {u.filename} ({Math.round(u.size / 1024)} KB)
                {' '}<a href={u.public_url} target="_blank" rel="noreferrer">열기</a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {taskId && <p>작업이 큐에 등록되었습니다. task_id: <code>{taskId}</code></p>}
      {error && <p style={{ color: 'red' }}>에러: {error}</p>}
    </div>
  )
}

export default App

