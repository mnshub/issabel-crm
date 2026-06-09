/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#ff4757',
          hover: '#e03746',
          dark: '#1a202c',
          surface: '#2d3748'
        }
      }
    },
  },
  plugins: [],
}