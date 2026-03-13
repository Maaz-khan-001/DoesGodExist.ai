import { createContext, useContext, useEffect, useState, useCallback } from 'react'

const ThemeContext = createContext(null)

export const ThemeProvider = ({ children }) => {
  // Initialize theme from localStorage or system preference
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    
    const stored = localStorage.getItem('theme')
    if (stored === 'dark' || stored === 'light') return stored
    
    // Check system preference
    if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
    return 'dark'
  })

  const [isSystemPreference, setIsSystemPreference] = useState(() => {
    return !localStorage.getItem('theme')
  })

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement
    
    if (isSystemPreference) {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', theme)
    }
  }, [theme, isSystemPreference])

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)')
    
    const handleChange = (e) => {
      if (isSystemPreference) {
        setTheme(e.matches ? 'light' : 'dark')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [isSystemPreference])

  const setDarkMode = useCallback(() => {
    setTheme('dark')
    setIsSystemPreference(false)
    localStorage.setItem('theme', 'dark')
  }, [])

  const setLightMode = useCallback(() => {
    setTheme('light')
    setIsSystemPreference(false)
    localStorage.setItem('theme', 'light')
  }, [])

  const setSystemPreference = useCallback(() => {
    setIsSystemPreference(true)
    localStorage.removeItem('theme')
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches
    setTheme(prefersLight ? 'light' : 'dark')
  }, [])

  const toggleTheme = useCallback(() => {
    if (theme === 'dark') {
      setLightMode()
    } else {
      setDarkMode()
    }
  }, [theme, setDarkMode, setLightMode])

  const isDark = theme === 'dark'
  const isLight = theme === 'light'

  const value = {
    theme,
    isDark,
    isLight,
    isSystemPreference,
    setDarkMode,
    setLightMode,
    setSystemPreference,
    toggleTheme,
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export default ThemeContext
