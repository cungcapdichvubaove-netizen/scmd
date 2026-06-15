// file: tailwind.config.js

<<<<<<< HEAD
const scmdVar = (token) => `rgb(var(${token}) / <alpha-value>)`;

const SCMD_BRAND_SCALE = Object.freeze({
  950: scmdVar("--scmd-navy-950-rgb"),
  900: scmdVar("--scmd-navy-900-rgb"),
  800: scmdVar("--scmd-navy-800-rgb"),
  700: scmdVar("--scmd-blue-700-rgb"),
  600: scmdVar("--scmd-blue-600-rgb"),
  500: scmdVar("--scmd-blue-500-rgb"),
  400: scmdVar("--scmd-blue-400-rgb"),
});

const SCMD_STATE_COLORS = Object.freeze({
  success: scmdVar("--scmd-success-rgb"),
  info: scmdVar("--scmd-info-rgb"),
  warning: scmdVar("--scmd-warning-rgb"),
  danger: scmdVar("--scmd-danger-rgb"),
  neutral: "#64748b",
});

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
    "./*/static/**/*.js",
=======
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './*/static/**/*.js',
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
  ],
  theme: {
    extend: {
      colors: {
<<<<<<< HEAD
        navy: {
          950: SCMD_BRAND_SCALE[950],
          900: SCMD_BRAND_SCALE[900],
          800: SCMD_BRAND_SCALE[800],
        },
        blue: {
          700: SCMD_BRAND_SCALE[700],
          600: SCMD_BRAND_SCALE[600],
          500: SCMD_BRAND_SCALE[500],
          400: SCMD_BRAND_SCALE[400],
        },
        neutral: {
          50: "#f8fbfd",
          100: "#f7fafc",
          150: "#eef4f8",
          200: "#f1f5f9",
          300: "#d8e2ec",
          400: "#c4d2df",
          500: "#7e8ca3",
          600: "#64748b",
          700: "#5f6f86",
          900: "#162033",
        },
        brand: SCMD_BRAND_SCALE,
        surface: {
          base: "#eef4f8",
          soft: "#f7fafc",
          card: "#ffffff",
        },
        state: SCMD_STATE_COLORS,
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
      },
    },
  },
  plugins: [
<<<<<<< HEAD
    require("daisyui"),
  ],
  daisyui: {
    themes: ["business", "corporate"],
    darkTheme: "business",
  },
};
=======
    require('daisyui'),
  ],
  daisyui: {
    themes: ["business", "corporate"], // Thêm business và corporate
    darkTheme: "business", // Quan trọng: Đặt business làm theme tối mặc định
  },
}
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
