import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
// FIX: Removed rehypeSanitize — it strips valid HTML attributes used by
// remark-gfm for tables (align, colspan) and breaks rendered output.
// react-markdown already sanitizes by default; rehypeSanitize is redundant
// and destructive here.
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useState } from 'react'

const T = '#2a9d8f'   // teal
const N = '#1a2744'   // navy

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      style={styles.copyBtn}
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

export default function MarkdownRenderer({ content }) {
  return (
    <>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        className="md-body"
        components={{
          h1: ({ children }) => <h1 style={styles.h1}>{children}</h1>,
          h2: ({ children }) => <h2 style={styles.h2}>{children}</h2>,
          h3: ({ children }) => <h3 style={styles.h3}>{children}</h3>,
          p:  ({ children }) => <p  style={styles.p}>{children}</p>,

          ul: ({ children }) => <ul style={styles.ul}>{children}</ul>,
          ol: ({ children }) => <ol style={styles.ol}>{children}</ol>,
          li: ({ children }) => (
            <li style={styles.li}>
              <span style={styles.liMarker}>▸</span>
              <span>{children}</span>
            </li>
          ),

          blockquote: ({ children }) => (
            <blockquote style={styles.blockquote}>{children}</blockquote>
          ),

          table: ({ children }) => (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>{children}</table>
            </div>
          ),
          th: ({ children }) => <th style={styles.th}>{children}</th>,
          td: ({ children }) => <td style={styles.td}>{children}</td>,

          // FIX: Removed deprecated `inline` prop destructuring — newer versions
          // of react-markdown no longer pass `inline`. Instead, check whether
          // the code element has a language class to determine block vs inline.
          code: ({ node, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            const isBlock = !!match
            const codeText = String(children).replace(/\n$/, '')

            if (isBlock) {
              return (
                <div style={styles.codeBlock}>
                  <div style={styles.codeHeader}>
                    <span style={styles.codeLang}>{match[1]}</span>
                    <CopyButton text={codeText} />
                  </div>
                  <SyntaxHighlighter
                    style={oneLight}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{ margin: 0, borderRadius: 0, fontSize: '12px' }}
                    {...props}
                  >
                    {codeText}
                  </SyntaxHighlighter>
                </div>
              )
            }

            return (
              <code style={styles.inlineCode} {...props}>
                {children}
              </code>
            )
          },

          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" style={styles.link}>
              {children}
            </a>
          ),

          strong: ({ children }) => <strong style={styles.strong}>{children}</strong>,
          em: ({ children }) => <em style={styles.em}>{children}</em>,
          hr: () => <hr style={styles.hr} />,
        }}
      />

      <style>{`
        .md-body { font-family: 'DM Sans', sans-serif; font-size: 14px; line-height: 1.7; color: #374151; }
        .md-body > *:first-child { margin-top: 0 !important; }
        .md-body > *:last-child  { margin-bottom: 0 !important; }
      `}</style>
    </>
  )
}

const styles = {
  h1: { fontSize: '17px', fontWeight: '700', color: N, margin: '18px 0 8px', paddingBottom: '6px', borderBottom: `2px solid ${T}22`, fontFamily: "'Lora', serif" },
  h2: { fontSize: '15px', fontWeight: '700', color: N, margin: '16px 0 6px' },
  h3: { fontSize: '13px', fontWeight: '600', color: '#4b5563', margin: '12px 0 4px' },
  p:  { margin: '0 0 12px', lineHeight: '1.75', color: '#374151' },

  ul: { margin: '0 0 12px', paddingLeft: 0, listStyle: 'none' },
  ol: { margin: '0 0 12px', paddingLeft: '20px' },
  li: { display: 'flex', alignItems: 'flex-start', gap: '6px', marginBottom: '4px', color: '#374151', lineHeight: '1.65' },
  liMarker: { color: T, fontWeight: '700', flexShrink: 0, marginTop: '2px', fontSize: '10px' },

  blockquote: {
    borderLeft: `3px solid ${T}`,   // FIX: was border-l-3 (invalid Tailwind)
    paddingLeft: '14px',
    paddingTop: '6px',
    paddingBottom: '6px',
    margin: '12px 0',
    background: `${T}0d`,           // FIX: was bg-teal-pale (undefined token)
    borderRadius: '0 8px 8px 0',
    fontStyle: 'italic',
    color: '#4b5563',
  },

  tableWrapper: { overflowX: 'auto', margin: '12px 0', borderRadius: '8px', border: '1px solid #e5e7eb' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: { background: `${T}18`, color: N, fontWeight: '600', padding: '8px 12px', textAlign: 'left', borderBottom: '2px solid #e5e7eb' },
  td: { padding: '7px 12px', borderBottom: '1px solid #f3f4f6', color: '#374151' },

  codeBlock: { margin: '12px 0', borderRadius: '8px', overflow: 'hidden', border: '1px solid #e5e7eb' },
  codeHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#1e293b', padding: '6px 12px' },
  codeLang: { fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' },
  copyBtn: { fontSize: '11px', color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px', borderRadius: '4px', transition: 'color 0.15s' },

  inlineCode: {
    background: `${T}15`,   // FIX: was bg-teal-dim (undefined token)
    color: T,               // FIX: was text-teal (undefined token)
    padding: '1px 6px',
    borderRadius: '4px',
    fontSize: '12px',
    fontFamily: 'monospace',
  },

  link: { color: T, textDecoration: 'underline', textDecorationStyle: 'dotted' },
  strong: { fontWeight: '700', color: N },
  em: { fontStyle: 'italic', color: '#4b5563' },
  hr: { border: 'none', borderTop: '1px solid #e5e7eb', margin: '16px 0' },
}