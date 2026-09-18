import { FileImage, FileText, RefreshCw, Upload, X } from 'lucide-react'
import { useId, useRef, useState, type DragEvent, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import { formatBytes } from '../lib/format'

const ACCEPT = '.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png'
const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png']
const ACCEPTED_EXT = /\.(pdf|jpe?g|png)$/i
const MAX_BYTES = 20 * 1024 * 1024

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type) && !ACCEPTED_EXT.test(file.name)) {
    return 'Please use a PDF, JPG or PNG file.'
  }
  if (file.size > MAX_BYTES) return `That file is ${formatBytes(file.size)}. The limit is 20 MB.`
  return null
}

export function Dropzone({
  label,
  hint,
  icon,
  required,
  file,
  onChange,
  disabled,
}: {
  label: string
  hint: string
  icon: ReactNode
  required?: boolean
  file: File | null
  onChange: (file: File | null) => void
  disabled?: boolean
}) {
  const inputId = useId()
  const hintId = useId()
  const errorId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const accept = (candidate: File | undefined) => {
    if (!candidate) return
    const problem = validateFile(candidate)
    setError(problem)
    if (!problem) onChange(candidate)
  }

  const onDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragging(false)
    if (disabled) return
    accept(event.dataTransfer.files?.[0])
  }

  const isImage = file ? file.type.startsWith('image/') || /\.(jpe?g|png)$/i.test(file.name) : false

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <label htmlFor={inputId} className="text-sm font-semibold text-stone-900">
          {label}
          {required ? (
            <span className="sr-only"> (required)</span>
          ) : (
            <span className="ml-1.5 text-xs font-normal text-stone-500">Optional</span>
          )}
        </label>
      </div>

      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={ACCEPT}
        className="peer sr-only"
        aria-describedby={cn(hintId, error && errorId) || undefined}
        aria-invalid={error ? true : undefined}
        required={required}
        disabled={disabled}
        onChange={(e) => {
          accept(e.target.files?.[0])
          e.target.value = ''
        }}
      />

      {file ? (
        <div className="flex items-center gap-3 rounded-xl border border-brand-200 bg-brand-50/60 p-3 pr-2">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-white text-brand-700 ring-1 ring-brand-100">
            {isImage ? <FileImage className="size-5" aria-hidden="true" /> : <FileText className="size-5" aria-hidden="true" />}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-stone-900" title={file.name}>
              {file.name}
            </span>
            <span className="text-xs text-stone-500">
              {formatBytes(file.size)} · {isImage ? 'Image' : 'PDF'}
            </span>
          </span>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="rounded-lg p-2 text-stone-500 transition-colors hover:bg-white hover:text-stone-900"
            aria-label={`Replace ${label.toLowerCase()}`}
            disabled={disabled}
          >
            <RefreshCw className="size-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => {
              setError(null)
              onChange(null)
            }}
            className="rounded-lg p-2 text-stone-500 transition-colors hover:bg-white hover:text-challenge-700"
            aria-label={`Remove ${label.toLowerCase()}`}
            disabled={disabled}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          className={cn(
            'flex min-h-[8.5rem] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-5 text-center transition-colors',
            'peer-focus-visible:border-brand-600 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-600/30',
            dragging ? 'border-brand-500 bg-brand-50' : 'border-line-strong bg-paper/60 hover:border-brand-400 hover:bg-white',
            error && 'border-challenge-500/70',
            disabled && 'cursor-not-allowed opacity-60 hover:border-line-strong hover:bg-paper/60',
          )}
        >
          <span className="flex size-10 items-center justify-center rounded-full bg-white text-brand-700 shadow-card ring-1 ring-line">
            {dragging ? <Upload className="size-5" aria-hidden="true" /> : icon}
          </span>
          <span className="text-sm text-stone-700">
            <span className="font-semibold text-brand-700">Choose a file</span> or drag it here
          </span>
          <span className="text-xs text-stone-500">PDF, JPG or PNG · up to 20 MB</span>
        </label>
      )}

      <p id={hintId} className="mt-2 text-[13px] leading-snug text-stone-500">
        {hint}
      </p>
      {error && (
        <p id={errorId} className="mt-1 text-[13px] font-medium text-challenge-700" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
