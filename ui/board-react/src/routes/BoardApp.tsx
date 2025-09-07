import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

const NavLink: React.FC<{ to: string; label: string }> = ({ to, label }) => {
  const loc = useLocation()
  const active = loc.pathname === to || (to === '/' && loc.pathname === '')
  return (
    <Link to={to} className={`px-3 py-2 rounded ${active ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'}`}>
      {label}
    </Link>
  )
}

const BoardApp: React.FC = () => {
  return (
    <div className="min-h-screen">
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="font-bold text-lg">HanaNavi Board</div>
            <nav className="flex items-center gap-2">
              <NavLink to="/" label="목록" />
              <NavLink to="/new" label="새 글" />
            </nav>
          </div>
          <a className="text-sm text-gray-600" href="/" onClick={e => e.preventDefault()}>v0.2</a>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

export default BoardApp
