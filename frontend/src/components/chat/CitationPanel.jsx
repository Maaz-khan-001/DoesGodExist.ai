
/**
 * FIX [FE-13]: Citations were returned by the API but never displayed.
 *
 * This component renders a list of citations below an assistant message.
 * It is toggled open/closed by clicking "📚 N sources" in ChatArea.
 */
export default function CitationPanel({ citations }) {
  if (!citations || citations.length === 0) return null

  const TYPE_ICONS = {
    quran:                '📖',
    hadith:               '📜',
    philosophy:           '🧠',
    scientific:           '🔬',
    comparative_religion: '⚖️',
    logic:                '📐',
    meta:                 '💡',
  }

  return (
    <div style={styles.panel}>
      <p style={styles.heading}>Sources Used in This Response</p>
      <div style={styles.list}>
        {citations.map((cite, i) => (
          <div key={i} style={styles.item}>
            <div style={styles.header}>
              <span style={styles.icon}>
                {TYPE_ICONS[cite.source_type] || '📄'}
              </span>
              <span style={styles.ref}>[{i + 1}] {cite.reference}</span>
              {cite.is_verified && (
                <span style={styles.verified} title="Verified source">✓ Verified</span>
              )}
            </div>
            {cite.content && (
              <p style={styles.preview}>{cite.content.slice(0, 200)}
                {cite.content.length > 200 ? '...' : ''}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  panel: {
    marginTop: 8,
    padding: '8px 0 0',
  },
  heading: {
    color: '#555',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    margin: '0 0 8px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  item: {
    background: '#13151e',
    border: '1px solid #2a2d38',
    borderRadius: 8,
    padding: '8px 10px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  icon: { fontSize: 14 },
  ref: {
    color: '#d4a853',
    fontSize: 12,
    fontWeight: 500,
    flex: 1,
  },
  verified: {
    color: '#4caf50',
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 5px',
    background: '#1a2e1a',
    borderRadius: 4,
  },
  preview: {
    color: '#8b8fa8',
    fontSize: 12,
    margin: 0,
    lineHeight: 1.5,
    fontStyle: 'italic',
  },
}
