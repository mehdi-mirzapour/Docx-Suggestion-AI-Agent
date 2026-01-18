import { useState, useEffect } from 'react'
import './App.css'

function App() {
    const [suggestions, setSuggestions] = useState([])
    const [docId, setDocId] = useState(null)
    const [selectedSuggestions, setSelectedSuggestions] = useState(new Set())
    const [downloadUrl, setDownloadUrl] = useState(null)
    const [status, setStatus] = useState('idle')

    // Initialize from ChatGPT's toolOutput
    useEffect(() => {
        const initialData = window.openai?.toolOutput
        if (initialData?.suggestions) {
            setSuggestions(initialData.suggestions)
            setDocId(initialData.doc_id)
        }
    }, [])

    // Listen for updates from ChatGPT
    useEffect(() => {
        const handleSetGlobals = (event) => {
            const globals = event.detail?.globals
            if (!globals?.toolOutput) return

            if (globals.toolOutput.suggestions) {
                setSuggestions(globals.toolOutput.suggestions)
                setDocId(globals.toolOutput.doc_id)
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

        if (window.openai?.callTool) {
            try {
                const response = await window.openai.callTool('apply_changes', {
                    doc_id: docId,
                    suggestion_ids: Array.from(selectedSuggestions),
                })

                if (response?.structuredContent?.download_url) {
                    setDownloadUrl(response.structuredContent.download_url)
                    setStatus('completed')
                }
            } catch (error) {
                console.error('Error applying changes:', error)
                setStatus('error')
            }
        }
    }

    if (suggestions.length === 0) {
        return (
            <div className="container">
                <div className="empty-state">
                    <h2>📄 Document Editor</h2>
                    <p>Upload a Word document and ask ChatGPT to suggest edits!</p>
                    <p className="hint">
                        Try: "Make this document more formal" or "Fix grammar issues"
                    </p>
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
