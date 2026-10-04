/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          500: '#0ea5e9',
          600: '#0284c7',
        },
        amazon: {
          bg: '#451a03',
          border: '#d97706',
          text: '#fbbf24',
        },
        myntra: {
          bg: '#500724',
          border: '#e11d48',
          text: '#fb7185',
        },
        flipkart: {
          bg: '#172554',
          border: '#2563eb',
          text: '#60a5fa',
        }
      },
    },
  },
  plugins: [],
}
