import React from 'react'
import { cn, Text } from './ui'

interface Column<T> {
  key: string
  header: string
  render?: (row: T) => React.ReactNode
}

interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  className?: string
}

export function DataTable<T extends { id?: string | number; [key: string]: any }>({ data, columns, className }: DataTableProps<T>) {
  return (
    <div className={cn("overflow-x-auto border-1 border-border-default bg-surface-secondary", className)}>
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b-1 border-border-default">
            {columns.map((col) => (
              <th key={col.key} className="p-4 font-medium">
                <Text size={14} variant="secondary" className="uppercase tracking-wide">{col.header}</Text>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.id || i} className="border-b-1 border-border-default last:border-b-0 hover:bg-surface-dominant/50 transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="p-4">
                  {col.render ? (
                    col.render(row)
                  ) : (
                    <Text size={14}>{row[col.key]}</Text>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
