import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import BoardApp from './routes/BoardApp'
import BoardList from './routes/BoardList'
import BoardNew from './routes/BoardNew'
import BoardView from './routes/BoardView'

const router = createBrowserRouter([
  {
    path: '/',
    element: <BoardApp />,
    children: [
      { index: true, element: <BoardList /> },
      { path: 'new', element: <BoardNew /> },
      { path: 'post/:id', element: <BoardView /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(<RouterProvider router={router} />)
