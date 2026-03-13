const STAGES = [
  { key: 'existence',   label: 'God',         display: 'Existence of God' },
  { key: 'prophethood', label: 'Prophethood',  display: 'Necessity of Prophethood' },
  { key: 'muhammad',    label: 'Muhammad ﷺ',   display: 'Prophethood of Muhammad ﷺ' },
  { key: 'invitation',  label: 'Islam',        display: 'Invitation to Islam' },
]

export default function StageProgressBar({ currentStage }) {
  const currentIdx = STAGES.findIndex(s => s.key === currentStage)
  const safeIdx = currentIdx === -1 ? 0 : currentIdx
  const current = STAGES[safeIdx]

  return (
    <div style={styles.wrapper}>
      {/* FIX: Single-row layout — dots and connectors rendered together so
          they're visually connected, not in two separate disconnected rows. */}
      <div style={styles.track}>
        {STAGES.map((stage, idx) => (
          <div key={stage.key} style={styles.stepGroup}>
            {/* Connector line before each step (except the first) */}
            {idx > 0 && (
              <div style={{
                ...styles.connector,
                background: idx <= safeIdx
                  ? 'linear-gradient(90deg, #2a9d8f, #38b2a3)'
                  : '#e2e8f0',
              }} />
            )}

            {/* Step dot */}
            <div style={{
              ...styles.dot,
              ...(idx < safeIdx  ? styles.dotDone :
                  idx === safeIdx ? styles.dotActive :
                                    styles.dotFuture),
            }}>
              {/* FIX: Only show ✓ for COMPLETED stages (idx < safeIdx),
                  not for all non-last stages as the original did. */}
              {idx < safeIdx ? '✓' : idx + 1}
            </div>

            {/* Label */}
            <span style={{
              ...styles.label,
              color: idx <= safeIdx ? '#1a2744' : '#94a3b8',
              fontWeight: idx === safeIdx ? '600' : '400',
            }}>
              {stage.label}
            </span>
          </div>
        ))}
      </div>

      <p style={styles.subtitle}>
        Discussing: <span style={styles.subtitleHighlight}>{current.display}</span>
      </p>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
      `}</style>
    </div>
  )
}

const styles = {
  wrapper: {
    background: '#fff',
    borderBottom: '1px solid #f1f5f9',
    padding: '10px 20px 8px',
    fontFamily: "'DM Sans', sans-serif",
  },
  track: {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    marginBottom: '5px',
  },
  stepGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  connector: {
    width: '32px',
    height: '2px',
    borderRadius: '2px',
    marginRight: '6px',
    transition: 'background 0.3s',
  },
  dot: {
    width: '22px',
    height: '22px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: '700',
    flexShrink: 0,
    transition: 'all 0.3s',
  },
  dotDone: {
    background: 'linear-gradient(135deg, #2a9d8f, #38b2a3)',
    color: '#fff',
    boxShadow: '0 1px 4px rgba(42,157,143,0.4)',
  },
  dotActive: {
    background: '#1a2744',
    color: '#fff',
    boxShadow: '0 2px 8px rgba(26,39,68,0.3)',
  },
  dotFuture: {
    background: '#f1f5f9',
    color: '#94a3b8',
  },
  label: {
    fontSize: '11px',
    whiteSpace: 'nowrap',
    transition: 'color 0.3s',
  },
  subtitle: {
    fontSize: '11px',
    color: '#94a3b8',
    margin: 0,
  },
  subtitleHighlight: {
    color: '#2a9d8f',
    fontWeight: '600',
  },
}