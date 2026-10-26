import React from 'react';
import { CodeBlock } from './CodeBlock';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  if (!content) return null;

  // Auto-close open code fences so unclosed blocks always render cleanly as CodeBlocks
  let safeContent = content;
  const fenceMatches = safeContent.match(/```/g);
  if (fenceMatches && fenceMatches.length % 2 !== 0) {
    safeContent += '\n```';
  }

  // Split content into blocks: code blocks vs text blocks
  const parts: { type: 'code' | 'text'; lang?: string; text: string }[] = [];
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(safeContent)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        text: safeContent.substring(lastIndex, match.index),
      });
    }
    parts.push({
      type: 'code',
      lang: match[1] || 'code',
      text: match[2].replace(/\n$/, ''),
    });
    lastIndex = codeBlockRegex.lastIndex;
  }

  if (lastIndex < safeContent.length) {
    parts.push({
      type: 'text',
      text: safeContent.substring(lastIndex),
    });
  }

  // Format inline markdown (bold, italic, inline code)
  const renderInline = (str: string) => {
    // Regex matches inline code `...`, bold **...**, italic *...*
    const tokens = [];
    const inlineRegex = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)/g;
    let idx = 0;
    let m;

    while ((m = inlineRegex.exec(str)) !== null) {
      if (m.index > idx) {
        tokens.push(str.substring(idx, m.index));
      }
      if (m[1]) {
        // `inline code`
        tokens.push(
          <code
            key={idx}
            style={{
              padding: '2px 6px',
              borderRadius: 5,
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              fontSize: '0.88em',
              fontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
              color: '#38bdf8',
            }}
          >
            {m[1].slice(1, -1)}
          </code>
        );
      } else if (m[2]) {
        // **bold**
        tokens.push(
          <strong key={idx} style={{ color: '#ffffff', fontWeight: 700 }}>
            {m[2].slice(2, -2)}
          </strong>
        );
      } else if (m[3]) {
        // *italic*
        tokens.push(
          <em key={idx} style={{ color: '#cbd5e1' }}>
            {m[3].slice(1, -1)}
          </em>
        );
      }
      idx = inlineRegex.lastIndex;
    }
    if (idx < str.length) {
      tokens.push(str.substring(idx));
    }
    return tokens;
  };

  // Render text block lines with headings, lists, quotes
  const renderTextBlock = (text: string, bIdx: number) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];

    lines.forEach((line, lIdx) => {
      const key = `${bIdx}-${lIdx}`;
      const trimmed = line.trim();

      if (!trimmed) {
        elements.push(<div key={key} style={{ height: 6 }} />);
        return;
      }

      // H1 (# )
      if (trimmed.startsWith('# ')) {
        elements.push(
          <h1
            key={key}
            style={{
              fontSize: 18,
              fontWeight: 800,
              color: '#ffffff',
              margin: '12px 0 6px 0',
              letterSpacing: '-0.01em',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              paddingBottom: 4,
            }}
          >
            {renderInline(trimmed.substring(2))}
          </h1>
        );
        return;
      }

      // H2 (## )
      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2
            key={key}
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: '#ffffff',
              margin: '10px 0 4px 0',
            }}
          >
            {renderInline(trimmed.substring(3))}
          </h2>
        );
        return;
      }

      // H3 (### )
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3
            key={key}
            style={{
              fontSize: 14.5,
              fontWeight: 700,
              color: '#e2e8f0',
              margin: '8px 0 3px 0',
            }}
          >
            {renderInline(trimmed.substring(4))}
          </h3>
        );
        return;
      }

      // Blockquote (> )
      if (trimmed.startsWith('> ')) {
        elements.push(
          <blockquote
            key={key}
            style={{
              margin: '6px 0',
              padding: '6px 14px',
              borderLeft: '3px solid var(--accent, #ffffff)',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '0 8px 8px 0',
              color: '#cbd5e1',
              fontStyle: 'italic',
            }}
          >
            {renderInline(trimmed.substring(2))}
          </blockquote>
        );
        return;
      }

      // Bullet List (- or *)
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        elements.push(
          <div
            key={key}
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 8,
              margin: '3px 0',
              paddingLeft: 4,
            }}
          >
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: '50%',
                background: 'var(--accent, #ffffff)',
                flexShrink: 0,
                marginTop: 6,
              }}
            />
            <div style={{ flex: 1 }}>{renderInline(trimmed.substring(2))}</div>
          </div>
        );
        return;
      }

      // Numbered List (1. )
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (numMatch) {
        elements.push(
          <div
            key={key}
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 8,
              margin: '3px 0',
              paddingLeft: 4,
            }}
          >
            <span
              style={{
                fontSize: 11.5,
                fontWeight: 700,
                color: 'var(--accent, #cbd5e1)',
                fontFamily: 'ui-monospace, monospace',
                flexShrink: 0,
              }}
            >
              {numMatch[1]}.
            </span>
            <div style={{ flex: 1 }}>{renderInline(numMatch[2])}</div>
          </div>
        );
        return;
      }

      // Normal paragraph line
      elements.push(
        <div key={key} style={{ margin: '2px 0' }}>
          {renderInline(line)}
        </div>
      );
    });

    return elements;
  };

  return (
    <div style={{ lineHeight: 1.6, wordBreak: 'break-word' }}>
      {parts.map((p, idx) => {
        if (p.type === 'code') {
          return <CodeBlock key={idx} language={p.lang || 'code'} code={p.text} />;
        }
        return <React.Fragment key={idx}>{renderTextBlock(p.text, idx)}</React.Fragment>;
      })}
    </div>
  );
};
