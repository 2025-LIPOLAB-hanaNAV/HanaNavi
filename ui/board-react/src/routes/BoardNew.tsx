import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Attachment, ETL_BASE, PostItem, loadPosts, savePosts } from './types'

type UploadInfo = {
  filename: string
  sha1: string
  url: string
  public_url: string
  size: number
  content_type: string
}

const BoardNew: React.FC = () => {
  const nav = useNavigate()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState('')
  const [category, setCategory] = useState('')
  const nowLocal = () => {
    const d = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const yyyy = d.getFullYear()
    const mm = pad(d.getMonth()+1)
    const dd = pad(d.getDate())
    const hh = pad(d.getHours())
    const mi = pad(d.getMinutes())
    return `${yyyy}-${mm}-${dd}T${hh}:${mi}`
  }
  const [date, setDate] = useState(nowLocal())
  const [severity, setSeverity] = useState<'low'|'medium'|'high'|''>('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [uploads, setUploads] = useState<UploadInfo[]>([])
  const [posting, setPosting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => setFiles(e.target.files)

  const uploadFile = async (file: File): Promise<UploadInfo> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${ETL_BASE}/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`upload failed: ${res.status}`)
    return res.json()
  }

  const submit = async () => {
    setError(null)
    setPosting(true)
    try {
      let atts: Attachment[] = []
      if (files && files.length > 0) {
        const results: UploadInfo[] = []
        for (let i=0;i<files.length;i++) {
          // eslint-disable-next-line no-await-in-loop
          const up = await uploadFile(files[i])
          results.push(up)
        }
        setUploads(results)
        atts = results.map(r => ({ filename: r.filename, url: r.url, public_url: r.public_url, sha1: r.sha1, size: r.size, content_type: r.content_type }))
      }

      const id = String(Date.now())
      const event = {
        action: 'post_created',
        post_id: Number(id),
        title, body,
        tags: tags ? tags.split(',').map(s => s.trim()).filter(Boolean) : [],
        category, date: (date || nowLocal()).replace('T', ' '), severity,
        attachments: atts,
      }

      // notify ETL (optional worker)
      await fetch(`${ETL_BASE}/ingest/webhook`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(event) }).catch(() => {})

      // save locally for board UI
      const post: PostItem = { id, title, body, tags: event.tags, category, date: event.date, severity, attachments: atts, createdAt: new Date().toISOString() }
      const current = loadPosts()
      current.unshift(post)
      savePosts(current)

      nav(`/post/${id}`)
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setPosting(false)
    }
  }

  return (
    <div className="bg-white border rounded p-4">
      <div className="text-lg font-semibold mb-3">새 글 작성</div>
      <div className="grid gap-3">
        <label className="grid gap-1">
          <span className="text-sm text-gray-600">제목</span>
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="제목을 입력" />
        </label>
        <label className="grid gap-1">
          <span className="text-sm text-gray-600">본문</span>
          <textarea rows={10} value={body} onChange={e=>setBody(e.target.value)} placeholder="내용을 입력" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">태그(쉼표 구분)</span>
            <input value={tags} onChange={e=>setTags(e.target.value)} placeholder="예: 보이스피싱,금융사기" />
          </label>
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">카테고리</span>
            <input value={category} onChange={e=>setCategory(e.target.value)} placeholder="예: 공지, 설문, 보안" />
          </label>
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">게시일</span>
            <input type="datetime-local" value={date} onChange={e=>setDate(e.target.value)} />
          </label>
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">중요도</span>
            <select value={severity} onChange={e=>setSeverity(e.target.value as any)}>
              <option value="">선택</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </label>
        </div>
        <label className="grid gap-1">
          <span className="text-sm text-gray-600">첨부파일</span>
          <input type="file" multiple onChange={onFileChange} />
        </label>
        <div className="flex gap-2">
          <button disabled={posting || !title.trim()} onClick={submit}>{posting ? '등록 중...' : '등록'}</button>
          <button className="bg-gray-200 text-gray-900" onClick={() => nav('/')}>취소</button>
        </div>
        {uploads.length>0 && (
          <div className="mt-2">
            <div className="text-sm font-medium">업로드된 첨부</div>
            <ul className="list-disc pl-6">
              {uploads.map((u,i) => (
                <li key={i}>{u.filename} <a href={u.public_url} target="_blank" rel="noreferrer" className="ml-1">열기</a></li>
              ))}
            </ul>
          </div>
        )}
        {error && <div className="text-red-600">에러: {error}</div>}
      </div>
    </div>
  )
}

export default BoardNew
