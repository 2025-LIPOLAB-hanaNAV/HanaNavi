import React, { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ETL_BASE, PostItem, loadPosts } from './types'

const BoardView: React.FC = () => {
  const { id } = useParams()
  const post = useMemo(() => loadPosts().find(p => p.id === id), [id])

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
        <div className="text-sm text-gray-500">카테고리: {post.category || '-'} · 날짜: {post.date || post.createdAt.slice(0,10)} · 중요도: {post.severity || '-'}</div>
        <div className="mt-1 text-sm text-gray-600">{post.tags.map(t => <span key={t} className="inline-block bg-gray-100 px-2 py-0.5 rounded mr-1">#{t}</span>)}</div>
      </div>
      <div className="p-4 whitespace-pre-wrap leading-7">{post.body}</div>
      <div className="px-4 pb-4">
        <div className="text-sm font-medium mb-1">첨부파일 ({post.attachments.length})</div>
        {post.attachments.length === 0 && <div className="text-sm text-gray-500">첨부 없음</div>}
        <ul className="list-disc pl-6">
          {post.attachments.map((a, i) => (
            <li key={i}>
              <span className="font-medium">{a.filename}</span>
              {' '}
              <a href={a.public_url || a.url} target="_blank" rel="noreferrer">다운로드</a>
            </li>
          ))}
        </ul>
      </div>
      <div className="px-4 py-3 border-t bg-gray-50 flex items-center justify-between">
        <Link to="/" className="text-blue-600 hover:underline">← 목록으로</Link>
        <a className="text-sm text-gray-600" href={`${ETL_BASE}/files/`} onClick={e => e.preventDefault()}>ETL API</a>
      </div>
    </div>
  )
}

export default BoardView

