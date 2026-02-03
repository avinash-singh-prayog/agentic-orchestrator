/**
 * File Upload Component
 * 
 * Handles file selection, preview, and drag-and-drop functionality.
 */

import React, { useRef, useState, useCallback } from "react"
import { Paperclip, Loader2 } from "lucide-react"
import type { FileAttachment } from "@/types/message"
import { processFiles, validateFileSize } from "@/utils/fileExtractor"

interface FileUploadProps {
  onFilesSelected: (attachments: FileAttachment[]) => void
  onFilesRemoved: (attachmentIds: string[]) => void
  selectedFiles: FileAttachment[]
  maxFiles?: number
  disabled?: boolean
}

const MAX_FILES = 5
const ACCEPTED_TYPES = [
  // Text files
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
  'text/plain',
  'text/csv',
  'text/html',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.oasis.opendocument.spreadsheet',
  // Images
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'image/gif',
].join(',')

const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  onFilesRemoved: _onFilesRemoved,
  selectedFiles,
  maxFiles = MAX_FILES,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return

    setError(null)

    // Check file count limit
    if (selectedFiles.length + files.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed. You have ${selectedFiles.length} file(s) selected.`)
      return
    }

    // Convert FileList to Array
    const fileArray = Array.from(files)

    // Validate all files
    const validationErrors: string[] = []
    fileArray.forEach(file => {
      const validation = validateFileSize(file)
      if (!validation.valid) {
        validationErrors.push(validation.error || `File "${file.name}" is invalid`)
      }
    })

    if (validationErrors.length > 0) {
      setError(validationErrors.join('\n'))
      return
    }

    setIsProcessing(true)
    try {
      const attachments = await processFiles(fileArray)
      // Filter out any attachments that don't have a file object
      const validAttachments = attachments.filter(att => att.file)
      if (validAttachments.length > 0) {
        onFilesSelected(validAttachments)
      } else {
        setError('Failed to process files. Please try different files.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process files')
    } finally {
      setIsProcessing(false)
    }
  }, [selectedFiles.length, maxFiles, onFilesSelected])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files)
    // Reset input to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleButtonClick = () => {
    if (!disabled && !isProcessing) {
      fileInputRef.current?.click()
    }
  }

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled && !isProcessing) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    if (disabled || isProcessing) return

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileSelect(files)
    }
  }


  const buttonStyles: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: 36,
    height: 36,
    borderRadius: 10,
    background: disabled || isProcessing ? "var(--bg-panel)" : "var(--bg-input)",
    border: "1px solid var(--border-light)",
    cursor: disabled || isProcessing ? "not-allowed" : "pointer",
    opacity: disabled || isProcessing ? 0.5 : 1,
    transition: "all 0.2s ease",
  }

  return (
    <div style={{ position: "relative" }}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES}
        onChange={handleInputChange}
        style={{ display: "none" }}
        disabled={disabled || isProcessing}
      />

      <button
        onClick={handleButtonClick}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={buttonStyles}
        title="Attach files"
        disabled={disabled || isProcessing}
      >
        {isProcessing ? (
          <Loader2 style={{ width: 16, height: 16, color: "var(--text-secondary)", animation: "spin 1s linear infinite" }} />
        ) : (
          <Paperclip style={{ width: 16, height: 16, color: "var(--text-secondary)" }} />
        )}
      </button>

      {isDragging && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              padding: "24px 32px",
              background: "var(--bg-panel)",
              border: "2px dashed var(--border-light)",
              borderRadius: 12,
              fontSize: 16,
              color: "var(--text-primary)",
            }}
          >
            Drop files here
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            position: "absolute",
            bottom: "100%",
            left: 0,
            marginBottom: 8,
            padding: "8px 12px",
            background: "#ef4444",
            color: "white",
            borderRadius: 8,
            fontSize: 12,
            maxWidth: 300,
            zIndex: 100,
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 8,
              background: "transparent",
              border: "none",
              color: "white",
              cursor: "pointer",
              fontSize: 16,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
      )}

    </div>
  )
}

export default FileUpload
