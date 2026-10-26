/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        display: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Master Deep-Teal Retro-Futuristic Research Palette
        teal: {
          50: '#F1F5F2',   // Light page background
          100: '#DDF2EE',  // Pale aqua panels
          200: '#C2EAE3',
          300: '#9EDBD0',  // Sea-glass accent
          400: '#6CB5AC',
          500: '#3E8F89',  // Muted turquoise
          600: '#26736D',
          700: '#155B58',
          800: '#0B4B49',  // Main teal surface
          850: '#093F3E',
          900: '#073D3C',  // Deep teal
          950: '#052E30',  // Dark petrol
        },
        petrol: {
          DEFAULT: '#052E30',
          dark: '#031E20',
          surface: '#073D3C',
          light: '#0B4B49',
        },
        aqua: {
          pale: '#DDF2EE',
          seaglass: '#9EDBD0',
          turquoise: '#3E8F89',
        },
        content: {
          bg: '#F1F5F2',
          text: '#153D3B',
          secondary: '#72918B',
          panel: '#DDF2EE',
          darkText: '#E5F5F1',
        },
        // Backwards compatibility mappings ensuring existing components shift to the retro-teal palette
        navy: {
          50: '#F1F5F2',
          100: '#DDF2EE',
          200: '#C2EAE3',
          300: '#9EDBD0',
          400: '#6CB5AC',
          500: '#3E8F89',
          600: '#155B58',
          700: '#0B4B49',
          800: '#0B4B49',
          850: '#093F3E',
          900: '#073D3C',
          950: '#052E30',
        },
        ocean: {
          50: '#F1F5F2',
          100: '#DDF2EE',
          200: '#C2EAE3',
          300: '#9EDBD0',
          400: '#6CB5AC',
          500: '#3E8F89',
          600: '#0B4B49',
          700: '#073D3C',
          800: '#052E30',
          900: '#031E20',
        }
      },
      boxShadow: {
        'tactile': '0 2px 8px -1px rgba(7, 61, 60, 0.08), 0 1px 3px -1px rgba(7, 61, 60, 0.05)',
        'tactile-hover': '0 8px 20px -2px rgba(7, 61, 60, 0.12), 0 3px 6px -1px rgba(7, 61, 60, 0.06)',
        'panel': '0 1px 4px rgba(7, 61, 60, 0.06)',
        'card': '0 2px 10px -1px rgba(7, 61, 60, 0.07), 0 1px 4px -1px rgba(7, 61, 60, 0.04)',
        'card-hover': '0 8px 24px -3px rgba(7, 61, 60, 0.12), 0 3px 8px -2px rgba(7, 61, 60, 0.06)',
        'pill': '0 2px 8px rgba(11, 75, 73, 0.18)',
      },
      borderRadius: {
        'geometric': '1.25rem',
        'panel': '1rem',
      }
    },
  },
  plugins: [],
}
