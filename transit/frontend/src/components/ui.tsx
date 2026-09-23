import React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const Text = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement> & { variant?: 'primary' | 'secondary' | 'muted', size?: 12 | 14 | 16 | 20 | 24, weight?: 'normal' | 'medium' | 'semibold' | 'bold' }>(
  ({ className, variant = 'primary', size = 14, weight = 'normal', ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn(
          {
            'text-text-primary': variant === 'primary',
            'text-text-secondary': variant === 'secondary',
            'text-text-muted': variant === 'muted',
            'text-12': size === 12,
            'text-14': size === 14,
            'text-16': size === 16,
            'text-20': size === 20,
            'text-24': size === 24,
            'font-normal': weight === 'normal',
            'font-medium': weight === 'medium',
            'font-semibold': weight === 'semibold',
            'font-bold': weight === 'bold',
          },
          className
        )}
        {...props}
      />
    )
  }
)
Text.displayName = 'Text'

export const Heading = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement> & { level?: 1 | 2 | 3 | 4 | 5 | 6, size?: 16 | 20 | 24 | 32 | 48, weight?: 'medium' | 'semibold' | 'bold' }>(
  ({ className, level = 2, size = 24, weight = 'semibold', ...props }, ref) => {
    const Component = `h${level}` as any
    return (
      <Component
        ref={ref}
        className={cn(
          'text-text-primary',
          {
            'text-16': size === 16,
            'text-20': size === 20,
            'text-24': size === 24,
            'text-32': size === 32,
            'text-48': size === 48,
            'font-medium': weight === 'medium',
            'font-semibold': weight === 'semibold',
            'font-bold': weight === 'bold',
          },
          className
        )}
        {...props}
      />
    )
  }
)
Heading.displayName = 'Heading'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'bg-surface-secondary border-1 border-border-default flex flex-col',
          className
        )}
        {...props}
      />
    )
  }
)
Card.displayName = 'Card'

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'outline' }>(
  ({ className, variant = 'primary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center text-14 font-medium transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:opacity-50 disabled:pointer-events-none',
          {
            'bg-accent text-surface-dominant hover:bg-opacity-90 px-4 py-2': variant === 'primary',
            'bg-surface-secondary text-text-primary hover:bg-surface-secondary/80 px-4 py-2': variant === 'secondary',
            'border-1 border-border-default text-text-primary hover:border-border-hover px-4 py-2': variant === 'outline',
          },
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
