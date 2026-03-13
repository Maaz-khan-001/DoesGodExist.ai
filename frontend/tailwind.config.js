/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        teal: { DEFAULT: '#0D9488', hover: '#0F766E', dim: '#CCFBF1', pale: '#F0FDF4' },
        navy: '#1A1A2E',
      },
      fontFamily: {
        arabic: ['"Noto Naskh Arabic"', 'serif'],
      },
    },
  },
  plugins: [],
}
