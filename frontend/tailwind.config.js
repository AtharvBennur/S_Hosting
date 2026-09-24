/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        slate: {
          950: '#06131f',
        },
      },
      boxShadow: {
        soft: '0 10px 30px rgba(15, 23, 42, 0.15)',
      },
    },
  },
  plugins: [],
};
