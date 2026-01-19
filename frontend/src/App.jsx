import React, { useState, useEffect } from 'react'
import './App.css'

const API_BASE = window.DOCX_API_URL || 'http://localhost:8787/api'

function App() {
    const [suggestions, setSuggestions] = useState([])
    const [docId, setDocId] = useState(null)
    const [selectedSuggestions, setSelectedSuggestions] = useState(new Set())
    const [downloadUrl, setDownloadUrl] = useState(null)
    const [status, setStatus] = useState('idle')

    // Standalone mode state
    const [isStandalone, setIsStandalone] = useState(false)
    const [file, setFile] = useState(null)
    const [editRequest, setEditRequest] = useState('')
    const [uploading, setUploading] = useState(false)
    const [analyzing, setAnalyzing] = useState(false)
    const [progress, setProgress] = useState('')

    // Detect if running in standalone mode (no ChatGPT)
    useEffect(() => {
        setIsStandalone(!window.openai)
    }, [])

    // Initialize from ChatGPT's toolOutput
    useEffect(() => {
        const initialData = window.openai?.toolOutput
        if (initialData?.doc_id) {
            setDocId(initialData.doc_id)
        }
        if (initialData?.suggestions) {
            setSuggestions(initialData.suggestions)
        }
    }, [])

    // Listen for updates from ChatGPT
    useEffect(() => {
        const handleSetGlobals = (event) => {
            const globals = event.detail?.globals
            if (!globals?.toolOutput) return

            if (globals.toolOutput.doc_id) {
                setDocId(globals.toolOutput.doc_id)
            }

            if (globals.toolOutput.suggestions) {
                setSuggestions(globals.toolOutput.suggestions)
            }

            if (globals.toolOutput.download_url) {
                setDownloadUrl(globals.toolOutput.download_url)
                setStatus('completed')
            }
        }

        window.addEventListener('openai:set_globals', handleSetGlobals, {
            passive: true,
        })

        return () => {
            window.removeEventListener('openai:set_globals', handleSetGlobals)
        }
    }, [])

    // ... (handleFileUpload code omitted for brevity, keeping existing) ...

    // ... (handleApplyChanges code omitted for brevity) ...



    // Standalone mode: Upload file
    const handleFileUpload = async () => {
        if (!file || !editRequest) {
            alert('Please select a file and enter an edit request')
            return
        }

        setUploading(true)
        setStatus('idle')
        const formData = new FormData()
        formData.append('file', file)

        try {
            // Upload document
            const uploadRes = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData,
            }).catch(err => {
                throw new Error(`Network error: Unable to connect to server. Please ensure the backend is running on port 8787. Details: ${err.message}`)
            })

            const uploadData = await uploadRes.json().catch(() => {
                throw new Error('Invalid response from server during upload')
            })

            if (!uploadRes.ok) {
                throw new Error(uploadData.error || `Upload failed with status ${uploadRes.status}`)
            }

            setDocId(uploadData.doc_id)
            setUploading(false)
            setAnalyzing(true)
            setProgress('Analyzing document with AI... This may take 20-30 seconds for large documents.')

            // Analyze document
            const analyzeRes = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_id: uploadData.doc_id,
                    request: editRequest,
                }),
            }).catch(err => {
                throw new Error(`Network error during analysis: ${err.message}`)
            })

            const analyzeData = await analyzeRes.json().catch(() => {
                throw new Error('Invalid response from server during analysis')
            })

            if (!analyzeRes.ok) {
                throw new Error(analyzeData.error || `Analysis failed with status ${analyzeRes.status}`)
            }

            setSuggestions(analyzeData.suggestions)
            setAnalyzing(false)
            setStatus('completed')
            setProgress('')
        } catch (error) {
            console.error('Error:', error)
            // Display user-friendly error message
            const errorMessage = error.message.includes('CORS')
                ? 'Connection blocked by browser security. Please ensure the backend server is running and CORS is configured correctly.'
                : error.message
            alert(`❌ ${errorMessage}`)
            // Reset all loading states
            setUploading(false)
            setAnalyzing(false)
            setStatus('error')
            setProgress('')
        }
    }

    const toggleSuggestion = (suggestionId) => {
        setSelectedSuggestions((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(suggestionId)) {
                newSet.delete(suggestionId)
            } else {
                newSet.add(suggestionId)
            }
            return newSet
        })
    }

    const handleApplyChanges = async () => {
        if (!docId || selectedSuggestions.size === 0) return

        setStatus('applying')

        try {
            const response = await fetch(`${API_BASE}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_id: docId,
                    suggestion_ids: Array.from(selectedSuggestions),
                }),
            })
            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.error || 'Apply failed')
            }

            // Construct download URL using the current origin (API_BASE minus /api)
            // API_BASE is e.g. "https://ngrok-url/api"
            const baseUrl = API_BASE.replace(/\/api$/, '')
            setDownloadUrl(`${baseUrl}${data.download_url}`)
            setStatus('completed')
        } catch (error) {
            console.error('Error applying changes:', error)
            setStatus('error')
            alert(`Failed to apply changes: ${error.message}`)
        }
    }

    if (suggestions.length === 0) {
        return (
            <div className="container">
                <div className="empty-state">
                    <h2>📄 Document Editor</h2>

                    <p>Upload a Word document and request edits</p>
                    <div className="upload-form">
                        <input
                            type="file"
                            accept=".docx"
                            onChange={(e) => setFile(e.target.files[0])}
                            className="file-input"
                        />
                        <input
                            type="text"
                            placeholder="Enter edit request (e.g., 'make it more formal')"
                            value={editRequest}
                            onChange={(e) => setEditRequest(e.target.value)}
                            className="text-input"
                        />
                        <button
                            onClick={handleFileUpload}
                            disabled={!file || !editRequest || uploading || analyzing}
                            className="btn-primary"
                        >
                            {uploading ? 'Uploading...' : analyzing ? 'Analyzing... (20-30s)' : 'Upload & Analyze'}
                        </button>
                        {progress && (
                            <p style={{
                                marginTop: '12px',
                                fontSize: '0.9rem',
                                color: '#6366f1',
                                textAlign: 'center',
                                fontWeight: '500'
                            }}>
                                ⏳ {progress}
                            </p>
                        )}
                        {(!file || !editRequest) && (
                            <p style={{
                                marginTop: '12px',
                                fontSize: '0.85rem',
                                color: '#ef4444',
                                textAlign: 'center'
                            }}>
                                {!file && !editRequest && '⚠️ Please select a document and enter a request'}
                                {!file && editRequest && '⚠️ Please select a document'}
                                {file && !editRequest && '⚠️ Please enter an edit request'}
                            </p>
                        )}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="container">
            <header className="header">
                <h2>📝 Suggested Edits</h2>
                <p className="subtitle">
                    {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''} found
                </p>
            </header>

            <div className="suggestions-list">
                {suggestions.map((suggestion) => (
                    <div
                        key={suggestion.id}
                        className={`suggestion-card ${selectedSuggestions.has(suggestion.id) ? 'selected' : ''
                            }`}
                    >
                        <label className="suggestion-label">
                            <input
                                type="checkbox"
                                checked={selectedSuggestions.has(suggestion.id)}
                                onChange={() => toggleSuggestion(suggestion.id)}
                            />
                            <div className="suggestion-content">
                                <div className="text-comparison">
                                    <div className="text-block original">
                                        <span className="label">Original:</span>
                                        <p>{suggestion.original}</p>
                                    </div>
                                    <div className="arrow">→</div>
                                    <div className="text-block suggested">
                                        <span className="label">Suggested:</span>
                                        <p>{suggestion.suggested}</p>
                                    </div>
                                </div>
                                <div className="reason">
                                    <span className="reason-icon">💡</span>
                                    {suggestion.reason}
                                </div>
                            </div>
                        </label>
                    </div>
                ))}
            </div>

            <div className="action-bar">
                <button
                    className="btn-primary"
                    onClick={handleApplyChanges}
                    disabled={selectedSuggestions.size === 0 || status === 'applying'}
                >
                    {status === 'applying'
                        ? 'Applying Changes...'
                        : `Apply ${selectedSuggestions.size} Selected Change${selectedSuggestions.size !== 1 ? 's' : ''
                        }`}
                </button>

                {downloadUrl && (
                    <a href={downloadUrl} download className="btn-download">
                        ⬇️ Download Modified Document
                    </a>
                )}
            </div>

            {status === 'completed' && (
                <div className="success-message">
                    ✅ Changes applied successfully! Download your document above.
                </div>
            )}

            {status === 'error' && (
                <div className="error-message">
                    ❌ Error applying changes. Please try again.
                </div>
            )}
        </div>
    )
}

export default App

