export type Attachment = {
  filename: string
  url: string
  public_url?: string
  sha1?: string
  size?: number
  content_type?: string
}

export type PostItem = {
  id: number
  title: string
  body: string
  tags: string[]
  category: string
  date: string
  severity: 'low' | 'medium' | 'high' | ''
  attachments: Attachment[]
  createdAt: string
}

export const ETL_BASE = import.meta.env.VITE_ETL_BASE || 'http://localhost:8002'
export const BOARD_BASE = import.meta.env.VITE_BOARD_BASE || 'http://localhost:8004'

