// file: tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './*/static/**/*.js',
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
    themes: ["business", "corporate"], // Thêm business và corporate
    darkTheme: "business", // Quan trọng: Đặt business làm theme tối mặc định
  },
}