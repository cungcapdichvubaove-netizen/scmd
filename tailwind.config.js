// file: tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './*/static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          950: '#0f172a',
          900: '#16233a',
          800: '#20304d',
          700: '#29456f',
          600: '#31558c',
          500: '#3b82f6',
          400: '#60a5fa',
        },
        surface: {
          base: '#eef4f8',
          soft: '#f7fafc',
          card: '#ffffff',
        },
        state: {
          success: '#16a34a',
          info: '#2563eb',
          warning: '#d97706',
          danger: '#dc2626',
          neutral: '#64748b',
        },
      },
    },
  },
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
    themes: ["business", "corporate"], // Thêm business và corporate
    darkTheme: "business", // Quan trọng: Đặt business làm theme tối mặc định
  },
}
