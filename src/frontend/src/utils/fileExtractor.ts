/**
 * File Content Extractor Utility
 * 
 * Converts all files to base64. Backend handles all processing (text extraction, etc.).
 * Simple approach: frontend just uploads, backend processes.
 */

import type { FileAttachment } from "@/types/message"

// Supported file types
const TEXT_FILE_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // DOCX
  'application/msword', // DOC
  'text/plain', // TXT
  'text/csv', // CSV
  'text/html', // HTML
  'application/vnd.ms-excel', // XLS
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // XLSX
  'application/vnd.oasis.opendocument.spreadsheet', // ODS
]

const IMAGE_FILE_TYPES = [
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'image/gif',
]

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

/**
 * Classify file type as 'image' or 'text'
 */
export function classifyFileType(file: File): 'image' | 'text' {
  if (IMAGE_FILE_TYPES.includes(file.type)) {
    return 'image'
  }
  if (TEXT_FILE_TYPES.includes(file.type) || file.name.match(/\.(pdf|docx?|txt|csv|tsv|xlsx?|ods|html|htm)$/i)) {
    return 'text'
  }
  // Default to text for unknown types
  return 'text'
}

/**
 * Validate file size
 */
export function validateFileSize(file: File): { valid: boolean; error?: string } {
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File "${file.name}" exceeds maximum size of 10MB`
    }
  }
  return { valid: true }
}

/**
 * Convert file to base64 string
 */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Remove data URL prefix (e.g., "data:image/png;base64,")
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/**
 * Read text file content
 */
export function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

/**
 * Extract text from PDF using pdfjs-dist
 * Note: This requires pdfjs-dist to be installed
 */
export async function extractPDFText(file: File): Promise<string> {
  try {
    // Dynamic import to avoid issues if pdfjs-dist is not installed
    const pdfjsLib = await import('pdfjs-dist')
    
    // Use local worker from node_modules instead of CDN
    // This avoids CORS and network issues
    try {
      // Try to use the worker from node_modules
      pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
        'pdfjs-dist/build/pdf.worker.min.mjs',
        import.meta.url
      ).toString()
    } catch {
      // Fallback: use unpkg CDN with https
      pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`
    }
    
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    const numPages = pdf.numPages
    const textParts: string[] = []
    
    for (let i = 1; i <= numPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items
        .map((item: any) => item.str)
        .join(' ')
      textParts.push(pageText)
    }
    
    return textParts.join('\n\n')
  } catch (error) {
    console.error('Error extracting PDF text:', error)
    throw new Error(`Failed to extract text from PDF: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Extract text from DOCX using mammoth
 * Note: This requires mammoth to be installed
 */
export async function extractDOCXText(file: File): Promise<string> {
  try {
    // Dynamic import to avoid issues if mammoth is not installed
    const mammoth = await import('mammoth')
    
    const arrayBuffer = await file.arrayBuffer()
    const result = await mammoth.extractRawText({ arrayBuffer })
    return result.value
  } catch (error) {
    console.error('Error extracting DOCX text:', error)
    throw new Error(`Failed to extract text from DOCX: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Process file - just keep the File object. No conversion needed.
 * Backend will receive files directly via FormData.
 */
export async function processFile(file: File): Promise<FileAttachment> {
  // Validate file size
  const validation = validateFileSize(file)
  if (!validation.valid) {
    throw new Error(validation.error)
  }
  
  const fileType = classifyFileType(file)
  const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  
  // Create preview URL for images
  const url = fileType === 'image' ? URL.createObjectURL(file) : undefined
  
  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    fileType,
    file, // Store the actual File object - sent directly via FormData
    url,
  }
}

/**
 * Process multiple files
 */
export async function processFiles(files: File[]): Promise<FileAttachment[]> {
  const results = await Promise.allSettled(
    files.map(file => processFile(file))
  )
  
  const attachments: FileAttachment[] = []
  const errors: string[] = []
  
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      attachments.push(result.value)
    } else {
      errors.push(`Failed to process "${files[index].name}": ${result.reason?.message || 'Unknown error'}`)
    }
  })
  
  if (errors.length > 0 && attachments.length === 0) {
    throw new Error(errors.join('\n'))
  }
  
  if (errors.length > 0) {
    console.warn('Some files failed to process:', errors)
  }
  
  return attachments
}
