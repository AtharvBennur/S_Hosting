import React, { useState, useEffect, useRef } from 'react';

interface VoiceDictationProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  id?: string;
  minHeight?: number;
  onSave?: () => void;
  isSaving?: boolean;
}

export function VoiceDictation({
  value,
  onChange,
  placeholder = 'Speak or type auditor observations, field inspection findings, or verification notes...',
  label,
  id = 'dictation-notes',
  minHeight = 110,
  onSave,
  isSaving = false,
}: VoiceDictationProps) {
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);
  const [micPermission, setMicPermission] = useState<'idle' | 'granted' | 'denied'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
    }
  }, []);

  const startListening = async () => {
    setErrorMessage('');
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    // Check microphone stream access
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        setMicPermission('granted');
      } catch (err: any) {
        console.warn('Microphone permission check warning:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setMicPermission('denied');
          setErrorMessage('Microphone access was denied. Please allow microphone permissions in your browser address bar.');
          return;
        }
      }
    }

    if (!SpeechRecognition) {
      setSpeechSupported(false);
      setErrorMessage('Browser native speech recognition is not supported in this browser. You can type notes or use the sample speech dictation.');
      return;
    }

    try {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-IN'; // Indian English / Global English standard

      recognition.onstart = () => {
        setIsListening(true);
        setInterimText('');
      };

      recognition.onresult = (event: any) => {
        let finalSegment = '';
        let currentInterim = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcriptChunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalSegment += transcriptChunk;
          } else {
            currentInterim += transcriptChunk;
          }
        }

        if (finalSegment.trim()) {
          const cleanSegment = finalSegment.trim();
          onChange(
            value
              ? `${value.trim()}${value.endsWith('.') || value.endsWith('\n') ? ' ' : '. '}${cleanSegment}`
              : cleanSegment
          );
        }

        setInterimText(currentInterim);
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          setMicPermission('denied');
          setErrorMessage('Microphone permission denied. Please allow microphone access.');
          stopListening();
        } else if (event.error === 'no-speech') {
          // Normal timeout if user was quiet for a while
        } else {
          setErrorMessage(`Audio recognition signal: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimText('');
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach(track => track.stop());
          mediaStreamRef.current = null;
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      console.error('Failed to start speech recognition', err);
      setIsListening(false);
      setErrorMessage('Could not initialize microphone speech recognition.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore if already stopped
      }
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    setIsListening(false);
    setInterimText('');
  };

  const insertSampleDictation = (text: string) => {
    onChange(value ? `${value.trim()}\n• ${text}` : `• ${text}`);
  };

  return (
    <div className="dictation-container">
      {label && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <label htmlFor={id} className="provision-label">
            {label}
          </label>
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>Voice dictation enabled</span>
        </div>
      )}

      {/* Toolbar with Microphone Toggle */}
      <div className="dictation-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {isListening ? (
            <button
              type="button"
              className="dictation-mic-btn listening"
              onClick={stopListening}
              title="Stop voice dictation"
            >
              <span className="mic-pulse-dot" />
              <div className="audio-sound-wave" aria-hidden="true">
                <span className="audio-sound-bar" />
                <span className="audio-sound-bar" />
                <span className="audio-sound-bar" />
                <span className="audio-sound-bar" />
              </div>
              <span>Listening... (Click to stop)</span>
            </button>
          ) : (
            <button
              type="button"
              className="dictation-mic-btn"
              onClick={startListening}
              title="Start voice dictation using your microphone"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--teal)' }}>
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
              <span>Dictate with voice</span>
            </button>
          )}

          {value && (
            <button
              type="button"
              className="button ghost"
              style={{ fontSize: 11, padding: '4px 8px', height: 'auto', minHeight: 28 }}
              onClick={() => onChange('')}
              title="Clear text"
            >
              Clear notes
            </button>
          )}

          {onSave && (
            <button
              type="button"
              className="button primary"
              style={{ fontSize: 11, padding: '4px 12px', height: 'auto', minHeight: 28 }}
              onClick={onSave}
              disabled={isSaving || !value.trim()}
            >
              {isSaving ? 'Saving...' : 'Save auditor notes'}
            </button>
          )}
        </div>

        {/* Quick sample prompt chips for auditors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>Insert quick note:</span>
          <button
            type="button"
            className="button ghost"
            style={{ fontSize: 10, padding: '2px 6px', height: 'auto', minHeight: 22 }}
            onClick={() => insertSampleDictation('Site inspection confirms delayed foundation works; contractor cited monsoon disruptions.')}
          >
            + Delay reason
          </button>
          <button
            type="button"
            className="button ghost"
            style={{ fontSize: 10, padding: '2px 6px', height: 'auto', minHeight: 22 }}
            onClick={() => insertSampleDictation('Vouchers and MB records verified against technical sanction ceiling.')}
          >
            + Vouchers verified
          </button>
          <button
            type="button"
            className="button ghost"
            style={{ fontSize: 10, padding: '2px 6px', height: 'auto', minHeight: 22 }}
            onClick={() => insertSampleDictation('Recommended for physical measurement verification by executive engineer.')}
          >
            + Escalation note
          </button>
        </div>
      </div>

      {/* Live Interim Transcript Badge */}
      {isListening && (
        <div className="dictation-live-card">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div>
            <strong>Speaking now:</strong> {interimText ? `"${interimText}"` : 'Listening for your voice... speak clearly into your microphone.'}
          </div>
        </div>
      )}

      {/* Error message */}
      {errorMessage && (
        <div className="provision-error-banner" style={{ marginTop: 2, padding: '8px 12px', fontSize: 11 }}>
          <span>{errorMessage}</span>
          <button
            type="button"
            style={{ marginLeft: 'auto', background: 'transparent', border: 0, cursor: 'pointer', fontWeight: 700 }}
            onClick={() => setErrorMessage('')}
          >
            ×
          </button>
        </div>
      )}

      {/* Textarea */}
      <textarea
        id={id}
        className="dictation-textarea"
        style={{ minHeight }}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
    </div>
  );
}
