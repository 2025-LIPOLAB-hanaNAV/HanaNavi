import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ETL_BASE, BOARD_BASE, PostItem } from './types'

const BoardView: React.FC = () => {
  const nav = useNavigate()
  const { id } = useParams()
  const [post, setPost] = useState<PostItem | null>(null)
  useEffect(() => {
    const fetchOne = async () => {
      try {
        const res = await fetch(`${BOARD_BASE}/posts/${id}`)
        if (!res.ok) { setPost(null); return }
        const data = await res.json()
        setPost(data as PostItem)
      } catch {
        setPost(null)
      }
    }
    fetchOne()
  }, [id])

  if (!post) {
    return (
      <div className="bg-white border rounded p-4">
        <div className="mb-2">게시글을 찾을 수 없습니다.</div>
        <Link to="/" className="text-blue-600 underline">목록으로</Link>
      </div>
    )
  }

  return (
    <div className="bg-white border rounded">
      <div className="px-4 py-3 border-b">
        <div className="text-xl font-semibold">{post.title}</div>
        <div className="text-sm text-gray-500">카테고리: {post.category || '-'} · 날짜: {post.date || '-'} · 중요도: {post.severity || '-'}</div>
        <div className="mt-1 text-sm text-gray-600">{post.tags.map(t => <span key={t} className="inline-block bg-gray-100 px-2 py-0.5 rounded mr-1">#{t}</span>)}</div>
      </div>
      <div className="p-4 whitespace-pre-wrap leading-7">{post.body}</div>
      <div className="px-4 pb-4">
        <div className="text-sm font-medium mb-1">첨부파일 ({post.attachments.length})</div>
        {post.attachments.length === 0 && <div className="text-sm text-gray-500">첨부 없음</div>}
        <ul className="list-disc pl-6 space-y-1">
          {post.attachments.map((a, i) => {
            const href = a.public_url || a.url
            return (
              <li key={i} className="flex items-center gap-2">
                <a href={href} download className="font-medium hover:underline" target="_blank" rel="noreferrer">{a.filename}</a>
                <a href={href} download className="bg-blue-600 text-white text-xs px-2 py-1 rounded hover:bg-blue-700" target="_blank" rel="noreferrer">다운로드</a>
              </li>
            )
          })}
        </ul>
      </div>
      <div className="px-4 py-3 border-t bg-gray-50 flex items-center justify-between">
        <Link to="/" className="text-blue-600 hover:underline">← 목록으로</Link>
        <a className="text-sm text-gray-600" href={`${ETL_BASE}/files/`} onClick={e => e.preventDefault()}>ETL API</a>
      </div>
      <div className="px-4 py-3 bg-gray-50 border-t flex items-center gap-2">
        <button onClick={()=>nav(`/post/${post.id}/edit`)}>수정</button>
        <button className="bg-red-600 text-white" onClick={async ()=>{
          if (!confirm('정말 삭제하시겠습니까?')) return
          await fetch(`${BOARD_BASE}/posts/${post.id}`, { method: 'DELETE' })
          nav('/')
        }}>삭제</button>
      </div>
    </div>
  )
}

export default BoardView
