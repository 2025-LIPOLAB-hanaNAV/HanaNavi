import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Attachment, BOARD_BASE, PostItem } from './types'

const BoardEdit: React.FC = () => {
  const nav = useNavigate()
  const { id } = useParams()
  const [current, setCurrent] = useState<PostItem | null>(null)
  useEffect(() => {
    const fetchOne = async () => {
      try {
        const res = await fetch(`${BOARD_BASE}/posts/${id}`)
        if (!res.ok) { setCurrent(null); return }
        const data = await res.json()
        setCurrent(data as PostItem)
      } catch { setCurrent(null) }
    }
    fetchOne()
  }, [id])

  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState('')
  const [category, setCategory] = useState('')
  const [date, setDate] = useState('')
  const [severity, setSeverity] = useState<'low'|'medium'|'high'|''>('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (current) {
      setTitle(current.title)
      setBody(current.body)
      setTags(current.tags.join(','))
      setCategory(current.category)
      setDate(current.date || '')
      setSeverity(current.severity)
      setAttachments(current.attachments || [])
    }
  }, [current])

  if (!current) {
    return (
      <div className="bg-white border rounded p-4">
        <div className="mb-2">게시글을 찾을 수 없습니다.</div>
        <button className="bg-gray-200 text-gray-900" onClick={()=>nav('/')}>목록으로</button>
      </div>
    )
  }

  const save = async () => {
    setError(null)
    setSaving(true)
    try {
      const payload: any = {
        title,
        body,
        tags: tags ? tags.split(',').map((s: string)=>s.trim()).filter(Boolean) : [],
        category,
        date,
        severity,
        attachments,
      }
      const res = await fetch(`${BOARD_BASE}/posts/${current.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
      if (!res.ok) throw new Error(`update failed: ${res.status}`)
      nav(`/post/${current.id}`)
    } catch (e:any) {
      setError(e?.message || String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white border rounded p-4">
      <div className="text-lg font-semibold mb-3">게시글 수정</div>
      <div className="grid gap-3">
        <label className="grid gap-1">
          <span className="text-sm text-gray-600">제목</span>
          <input value={title} onChange={e=>setTitle(e.target.value)} />
        </label>
        <label className="grid gap-1">
          <span className="text-sm text-gray-600">본문</span>
          <textarea rows={10} value={body} onChange={e=>setBody(e.target.value)} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">태그(쉼표 구분)</span>
            <input value={tags} onChange={e=>setTags(e.target.value)} />
          </label>
          <label className="grid gap-1">
            <span className="text-sm text-gray-600">카테고리</span>
            <input value={category} onChange={e=>setCategory(e.target.value)} />
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
        {attachments && attachments.length>0 && (
          <div>
            <div className="text-sm text-gray-600">첨부 ({attachments.length})</div>
            <ul className="list-disc pl-6">
              {attachments.map((a,i)=>(
                <li key={i}><span className="font-medium">{a.filename}</span></li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex gap-2">
          <button disabled={saving || !title.trim()} onClick={save}>{saving? '저장 중...' : '저장'}</button>
          <button className="bg-gray-200 text-gray-900" onClick={()=>nav(`/post/${current.id}`)}>취소</button>
        </div>
        {error && <div className="text-red-600">에러: {error}</div>}
      </div>
    </div>
  )
}

export default BoardEdit
