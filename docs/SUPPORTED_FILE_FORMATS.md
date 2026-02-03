# Supported File Formats

This document lists all file formats currently supported by the orchestrator system.

## Overview

The system supports two main categories of files:
1. **Text-based files**: Extracted as text content for LLM processing
2. **Image files**: Converted to base64 for Vision GPT processing

## Supported Formats

### Text Files (Text Extraction)

| Format | MIME Type | Extension | Status | Notes |
|--------|----------|-----------|--------|-------|
| PDF | `application/pdf` | `.pdf` | ✅ Full Support | Text extraction using PyPDF2/PyMuPDF. Handles multi-page documents. |
| Word Document | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` | ✅ Full Support | Text extraction using python-docx library. |
| Word Document (Legacy) | `application/msword` | `.doc` | ✅ Full Support | Text extraction using textract or docx2txt. |
| Plain Text | `text/plain` | `.txt` | ✅ Full Support | Direct text extraction with UTF-8 encoding. |
| CSV | `text/csv` | `.csv` | ✅ Full Support | Text extraction with automatic encoding detection (chardet or fallback to UTF-8). |
| TSV | `text/tab-separated-values` | `.tsv` | ✅ Full Support | Tab-separated values with encoding detection. |
| Excel (Modern) | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` | ✅ Full Support | Proper parsing using openpyxl. Extracts all sheets with structured data. |
| Excel (Legacy) | `application/vnd.ms-excel` | `.xls` | ✅ Full Support | Proper parsing using xlrd. Extracts all sheets with structured data. |
| OpenDocument Spreadsheet | `application/vnd.oasis.opendocument.spreadsheet` | `.ods` | ✅ Full Support | Text extraction using odfpy. Extracts all sheets. |
| HTML | `text/html` | `.html`, `.htm` | ✅ Full Support | Text extraction using BeautifulSoup. Removes scripts and styles. |

### Image Files (Vision Processing)

| Format | MIME Type | Extension | Status | Notes |
|--------|-----------|-----------|--------|-------|
| PNG | `image/png` | `.png` | ✅ Full Support | Converted to base64 for Vision GPT. |
| JPEG | `image/jpeg` | `.jpg`, `.jpeg` | ✅ Full Support | Converted to base64 for Vision GPT. |
| WebP | `image/webp` | `.webp` | ✅ Full Support | Converted to base64 for Vision GPT. |
| GIF | `image/gif` | `.gif` | ✅ Full Support | Converted to base64 for Vision GPT. |

## Processing Details

### Text Files
- **Input**: Files received as bytes via FormData
- **Processing**: 
  - **PDF**: Multi-method text extraction (PyPDF2 → PyMuPDF fallback)
  - **DOCX**: Paragraph-based text extraction using python-docx
  - **DOC**: Text extraction using textract or docx2txt
  - **XLSX**: Structured data extraction using openpyxl (all sheets)
  - **XLS**: Structured data extraction using xlrd (all sheets)
  - **ODS**: Structured data extraction using odfpy (all sheets)
  - **HTML**: Text extraction using BeautifulSoup with script/style removal
  - **CSV/TSV**: Encoding detection with chardet (if available) or UTF-8 fallback
  - **TXT**: UTF-8 decoding with error handling
- **Output**: Plain text string embedded in the prompt

### Image Files
- **Input**: Files received as bytes via FormData
- **Processing**: 
  - Convert bytes to base64
  - Validate using PIL (Python Imaging Library)
- **Output**: Base64-encoded string for Vision GPT API

## File Size Limits

- **Maximum file size**: 10 MB per file
- **Maximum files per message**: 5 files

## Encoding/Decoding Flow

### Current Implementation (Optimized)
1. **Frontend**: Sends files as **bytes** via FormData (no base64 conversion)
2. **Backend**: 
   - Receives bytes directly
   - For images: bytes → base64 (necessary for Vision GPT)
   - For text files: bytes → text (direct decoding, no unnecessary encoding)
   - Backward compatibility: Still handles base64 strings if needed

### No Unnecessary Encoding/Decoding
- ✅ Files sent as bytes (no frontend base64 conversion)
- ✅ Text files: Direct bytes → text decoding
- ✅ Images: bytes → base64 (only when needed for Vision GPT)
- ✅ Backward compatibility maintained for base64 strings

## Dependencies

The following Python libraries are used for file processing:

### Required
- `PyPDF2>=3.0.0` - PDF text extraction
- `pymupdf>=1.23.0` - PDF text extraction (fallback)
- `python-docx>=1.1.0` - DOCX text extraction
- `Pillow>=10.0.0` - Image validation
- `openpyxl>=3.1.0` - Excel XLSX parsing
- `xlrd>=2.0.0` - Excel XLS parsing
- `odfpy>=1.4.0` - OpenDocument Spreadsheet parsing
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=5.0.0` - HTML parsing (BeautifulSoup backend)
- `chardet>=5.0.0` - Encoding detection

### Optional (for legacy DOC files)
- `textract` - Alternative DOC extraction method
- `docx2txt` - Alternative DOC extraction method

## Known Limitations

1. **Scanned PDFs**: Image-based PDFs (scanned documents) may not extract text. The system will return an error message.

2. **Encrypted PDFs**: Password-protected PDFs cannot be processed.

3. **Complex Excel Files**: Very large Excel files (>10MB) or files with complex formulas may take longer to process.

4. **HTML with JavaScript**: Dynamic content generated by JavaScript is not extracted (only static HTML text).

## Future Enhancements

- [ ] Add support for PowerPoint files (.pptx)
- [ ] Add support for RTF files
- [ ] Improve handling of scanned PDFs (OCR integration)
- [ ] Add support for more image formats (BMP, TIFF, SVG, etc.)
- [ ] Add support for Markdown files (.md)
- [ ] Add support for JSON files (.json)
- [ ] Add support for XML files (.xml)
- [ ] Add support for LaTeX files (.tex)
- [ ] Add support for code files (.py, .js, .ts, .java, etc.)

## Suggested Additional Formats

Based on common use cases, the following formats would be valuable additions:

### Document Formats
- **PowerPoint (.pptx)**: For presentation content extraction
- **RTF (.rtf)**: Rich Text Format documents
- **Markdown (.md)**: Documentation and README files
- **EPUB (.epub)**: E-book format

### Data Formats
- **JSON (.json)**: Structured data files
- **XML (.xml)**: Structured markup files
- **YAML (.yaml, .yml)**: Configuration files
- **TOML (.toml)**: Configuration files

### Code Files
- **Python (.py)**: Source code files
- **JavaScript/TypeScript (.js, .ts)**: Web development files
- **Java (.java)**: Enterprise applications
- **C/C++ (.c, .cpp)**: System programming
- **Go (.go)**: Modern systems programming
- **Rust (.rs)**: Systems programming

### Archive Formats
- **ZIP (.zip)**: Extract and process contained files
- **TAR (.tar)**: Archive files

## Error Handling

The system provides clear error messages for:
- Unsupported file formats
- Corrupted files
- Files exceeding size limits
- Encoding issues (for text files)
- Empty or invalid files
- Missing dependencies (with installation instructions)