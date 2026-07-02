/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Outfit", "sans-serif"],
        serif: ['"Playfair Display"', "serif"],
      },
      colors: {
        brand: {
          50:  "#fff1f2",
          100: "#ffe4e6",
          200: "#fecdd3",
          300: "#fda4af",
          400: "#fb7185",
          500: "#f43f5e",
          600: "#e11d48",
          700: "#be123c",
          800: "#9f1239",
          900: "#881337",
        },
        epic: {
          yellow: "#fde047",
          blue:   "#1e3a8a",
          dark:   "#0f172a",
        },
      },
      boxShadow: {
        "epic": "8px 8px 0px rgba(15,23,42,1)",
        "epic-red": "8px 8px 0px rgba(225,29,72,1)",
        "book": "-5px 5px 15px rgba(0,0,0,0.2), inset 3px 0px 5px rgba(255,255,255,0.4)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
};
