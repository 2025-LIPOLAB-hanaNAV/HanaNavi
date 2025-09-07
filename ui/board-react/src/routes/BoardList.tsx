import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { BOARD_BASE, PostItem } from './types'

const PAGE_SIZE = 10

const BoardList: React.FC = () => {
  const [all, setAll] = useState<PostItem[]>([])
  useEffect(() => {
    const fetchList = async () => {
      try {
        const res = await fetch(`${BOARD_BASE}/posts?page=1&page_size=500`)
        const data = await res.json()
        setAll((data.items || []) as PostItem[])
      } catch {
        setAll([])
      }
    }
    fetchList()
  }, [])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const filtered = all.filter(p =>
    p.title.toLowerCase().includes(q.toLowerCase()) ||
    p.tags.join(',').toLowerCase().includes(q.toLowerCase()) ||
    p.category.toLowerCase().includes(q.toLowerCase())
  )
  const total = filtered.length
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const items = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xl font-semibold">게시글 목록</div>
        <Link to="/new" className="bg-green-600 text-white px-3 py-2 rounded">새 글</Link>
      </div>
      <div className="mb-3 flex items-center gap-2">
        <input className="w-64" value={q} onChange={e => setQ(e.target.value)} placeholder="제목/태그/카테고리 검색" />
        <span className="text-sm text-gray-500">총 {total}건</span>
      </div>
      <div className="overflow-x-auto bg-white border rounded">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-100 text-gray-700">
              <th className="p-2 text-left">제목</th>
              <th className="p-2">카테고리</th>
              <th className="p-2">태그</th>
              <th className="p-2">첨부</th>
              <th className="p-2">작성일</th>
            </tr>
          </thead>
          <tbody>
            {items.map(p => (
              <tr key={p.id} className="border-t">
                <td className="p-2 text-left">
                  <Link to={`/post/${p.id}`} className="font-medium hover:underline">{p.title}</Link>
                </td>
                <td className="p-2 text-center">{p.category || '-'}</td>
                <td className="p-2 text-center">{p.tags.slice(0,3).map(t => <span key={t} className="inline-block bg-gray-100 px-2 py-1 rounded mr-1">#{t}</span>)}</td>
                <td className="p-2 text-center">{p.attachments.length}</td>
                <td className="p-2 text-center">{p.date || p.createdAt.slice(0,10)}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td className="p-6 text-center text-gray-500" colSpan={5}>등록된 게시글이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-center gap-2">
        <button disabled={page<=1} onClick={() => setPage(p => Math.max(1, p-1))}>이전</button>
        <span className="text-sm">{page} / {pageCount}</span>
        <button disabled={page>=pageCount} onClick={() => setPage(p => Math.min(pageCount, p+1))}>다음</button>
      </div>
    </div>
  )}

export default BoardList
