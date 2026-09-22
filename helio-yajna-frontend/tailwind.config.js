/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                narvik: "#EAE7DD",
                sorrell: "#99775C",
                "sorrell-dark": "#7a5c43",
                "sorrell-light": "#bda086",
                "sorrell-dim": "rgba(153, 119, 92, 0.18)",
                "narvik-dim": "rgba(234, 231, 221, 0.12)",
                glass: "rgba(234, 231, 221, 0.08)",
                glassBorder: "rgba(153, 119, 92, 0.25)",
            },
            backdropBlur: {
                xs: '2px',
            }
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
