import React, { useState } from 'react';
import { Copy, Check, Terminal, FileCode } from 'lucide-react';

interface CodeBlockProps {
  language: string;
  code: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const cleanLang = (language || 'code').trim().toLowerCase();

  // Basic lightweight syntax coloring for code blocks
  const renderHighlightedCode = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      // Tokenize line with regex for keywords, strings, comments, numbers
      const parts: React.ReactNode[] = [];
      let rem = line;
      let partIdx = 0;

      // Single line comments
      const commentMatch = rem.match(/^(\s*)(#|\/\/|--)(.*)$/);
      if (commentMatch) {
        return (
          <div key={lIdx} style={{ minHeight: '1.4em', color: '#64748b', fontStyle: 'italic' }}>
            <span>{commentMatch[1]}</span>
            <span>{commentMatch[2]}{commentMatch[3]}</span>
          </div>
        );
      }

      // Regex for keywords, string literals, and numbers
      const tokenRegex = /(["'`].*?["'`])|(\b(?:def|function|return|import|from|const|let|var|if|else|elif|for|while|try|except|catch|finally|class|async|await|switch|case|break|continue|print|echo|null|true|false|None|True|False)\b)|(\b\d+(?:\.\d+)?\b)/g;
      let lastIndex = 0;
      let match;

      while ((match = tokenRegex.exec(rem)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<span key={partIdx++}>{rem.substring(lastIndex, match.index)}</span>);
        }

        if (match[1]) {
          // String
          parts.push(<span key={partIdx++} style={{ color: '#86efac' }}>{match[1]}</span>);
        } else if (match[2]) {
          // Keyword
          parts.push(<span key={partIdx++} style={{ color: '#c084fc', fontWeight: 600 }}>{match[2]}</span>);
        } else if (match[3]) {
          // Number
          parts.push(<span key={partIdx++} style={{ color: '#f59e0b' }}>{match[3]}</span>);
        }

        lastIndex = tokenRegex.lastIndex;
      }

      if (lastIndex < rem.length) {
        parts.push(<span key={partIdx++}>{rem.substring(lastIndex)}</span>);
      }

      return (
        <div key={lIdx} style={{ minHeight: '1.4em' }}>
          {parts.length > 0 ? parts : ' '}
        </div>
      );
    });
  };

  return (
    <div
      style={{
        margin: '12px 0',
        borderRadius: 12,
        background: 'rgba(7, 7, 12, 0.94)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
        overflow: 'hidden',
        fontSize: 12.5,
        fontFamily: "'JetBrains Mono', 'Fira Code', ui-monospace, Menlo, Consolas, monospace",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '7px 14px',
          background: 'rgba(255, 255, 255, 0.03)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div style={{ display: 'flex', gap: 5 }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ef4444', opacity: 0.8 }} />
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#f59e0b', opacity: 0.8 }} />
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#10b981', opacity: 0.8 }} />
          </div>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: '#94a3b8',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              marginLeft: 6,
            }}
          >
            {cleanLang}
          </span>
        </div>

        <button
          onClick={handleCopy}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '3px 10px',
            borderRadius: 6,
            background: copied ? 'rgba(34, 197, 94, 0.18)' : 'rgba(255, 255, 255, 0.06)',
            border: copied ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
            color: copied ? '#86efac' : '#cbd5e1',
            fontSize: 11,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Скопировать весь код в буфер"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          <span>{copied ? 'Скопировано!' : 'Скопировать'}</span>
        </button>
      </div>

      {/* Code contents */}
      <div
        style={{
          padding: '12px 16px',
          overflowX: 'auto',
          lineHeight: 1.6,
          color: '#e2e8f0',
          whiteSpace: 'pre',
          fontVariantLigatures: 'none',
          userSelect: 'text',
        }}
      >
        {renderHighlightedCode(code)}
      </div>
    </div>
  );
};
