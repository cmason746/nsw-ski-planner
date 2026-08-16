import styles from './TopBar.module.css'

export default function TopBar({ activeTab, onTabChange, onOpenPrefs }) {
  return (
    <header className={styles.topbar}>
      <div className={styles.brandWrap}>
        <div className={styles.brand}>
          <span className={styles.flake}>❄</span> Snowbound
        </div>
        <div className={styles.tagline}>Your guide to NSW's ski resorts</div>
      </div>

      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`${styles.tab} ${activeTab === 'overview' ? styles.active : ''}`}
          onClick={() => onTabChange('overview')}
        >
          Conditions Overview
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'recommend'}
          className={`${styles.tab} ${activeTab === 'recommend' ? styles.active : ''}`}
          onClick={() => onTabChange('recommend')}
        >
          Resort Recommendation
        </button>
      </div>

      <div className={styles.spacer} />

      <button type="button" className={styles.prefsBtn} onClick={onOpenPrefs}>
        🎯 What ski factors matter to you?
      </button>
    </header>
  )
}
