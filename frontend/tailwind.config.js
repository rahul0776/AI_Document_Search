/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx,html}"],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Custom dark mode colors
        dark: {
          bg: '#1a1a1a',
          surface: '#2d2d2d',
          border: '#404040',
        }
      }
    }
  },
  plugins: [],
};
