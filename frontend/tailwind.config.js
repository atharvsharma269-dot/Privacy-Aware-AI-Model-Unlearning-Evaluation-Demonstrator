/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['"Space Grotesk"', 'sans-serif'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        syne: ['"Syne"', 'sans-serif'],
      },
      colors: {
        // Brutalist Academia & Deep Terminal Palette
        paper: {
          DEFAULT: '#F4F4F0',
          50: '#FAFAFA',
          100: '#F4F4F0',
          200: '#E8E8E2',
          300: '#D5D5CC',
          dark: '#E0E0D8',
        },
        obsidian: {
          DEFAULT: '#0A0A0A',
          900: '#0A0A0A',
          800: '#141414',
          700: '#1F1F1F',
          600: '#2C2C2C',
        },
        acid: {
          DEFAULT: '#CCFF00',
          glow: '#D8FF24',
          neon: '#00FF66',
          orange: '#FF4D00',
        },
        // Re-mapped technical palette for high contrast
        teal: {
          50: '#F4F4F0',
          100: '#EAEAE4',
          200: '#D8D8D0',
          300: '#CCFF00', // Acid accent
          400: '#999999',
          500: '#666666',
          600: '#404040',
          700: '#262626',
          800: '#1A1A1A',
          850: '#121212',
          900: '#0A0A0A', // Pitch black
          950: '#000000', // Pure black
        },
        petrol: {
          DEFAULT: '#0A0A0A',
          dark: '#000000',
          surface: '#141414',
          light: '#262626',
        },
        aqua: {
          pale: '#F4F4F0',
          seaglass: '#CCFF00',
          turquoise: '#00FF66',
        },
        content: {
          bg: '#F4F4F0',
          text: '#0A0A0A',
          secondary: '#555555',
          panel: '#FFFFFF',
          darkText: '#FFFFFF',
        },
        navy: {
          50: '#F4F4F0',
          100: '#EAEAE4',
          200: '#D8D8D0',
          300: '#CCFF00',
          400: '#999999',
          500: '#666666',
          600: '#404040',
          700: '#262626',
          800: '#1A1A1A',
          850: '#121212',
          900: '#0A0A0A',
          950: '#000000',
        },
        ocean: {
          50: '#F4F4F0',
          100: '#EAEAE4',
          200: '#D8D8D0',
          300: '#CCFF00',
          400: '#999999',
          500: '#666666',
          600: '#1A1A1A',
          700: '#0A0A0A',
          800: '#000000',
        }
      },
      boxShadow: {
        'brutal': '3px 3px 0px 0px #000000',
        'brutal-sm': '2px 2px 0px 0px #000000',
        'brutal-lg': '5px 5px 0px 0px #000000',
        'brutal-acid': '3px 3px 0px 0px #CCFF00',
        'brutal-white': '3px 3px 0px 0px #FFFFFF',
        'tactile': '2px 2px 0px 0px #000000',
        'tactile-hover': '3px 3px 0px 0px #000000',
        'panel': '2px 2px 0px 0px #000000',
        'card': '3px 3px 0px 0px #000000',
        'card-hover': '4px 4px 0px 0px #000000',
        'pill': '2px 2px 0px 0px #000000',
      },
      borderRadius: {
        'geometric': '0px',
        'panel': '0px',
      }
    },
  },
  plugins: [],
}
