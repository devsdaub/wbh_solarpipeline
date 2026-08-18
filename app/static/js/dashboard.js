const FARBE_PRODUKTION = "#f59e0b";
const FARBE_EINSTRAHLUNG = "#6b7280";

let zeitreihe = null;

async function ladeDaten(tage) {
    const antwort = await fetch(`/api/data/daily?days=${tage}`);
    if (!antwort.ok) {
        throw new Error(`Datenabruf fehlgeschlagen: ${antwort.status}`);
    }
    return antwort.json();
}

function zeichneZeitreihe(daten) {
    const canvas = document.getElementById("chart-zeitreihe");

    zeitreihe = new Chart(canvas, {
        type: "line",
        data: {
            labels: daten.labels,
            datasets: [
                {
                    label: "Produktion kWh",
                    data: daten.produktion,
                    borderColor: FARBE_PRODUKTION,
                    backgroundColor: FARBE_PRODUKTION,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                },
                {
                    label: "Einstrahlung kWh/m²",
                    data: daten.einstrahlung,
                    borderColor: FARBE_EINSTRAHLUNG,
                    backgroundColor: FARBE_EINSTRAHLUNG,
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: "kWh" } },
                x: { ticks: { maxTicksLimit: 12 } },
            },
        },
    });
}

function aktualisiereZeitreihe(daten) {
    zeitreihe.data.labels = daten.labels;
    zeitreihe.data.datasets[0].data = daten.produktion;
    zeitreihe.data.datasets[1].data = daten.einstrahlung;
    zeitreihe.update();
}

async function wechsleZeitraum(tage, knopf) {
    document.querySelectorAll(".zeitraum-knopf").forEach((element) => {
        element.classList.remove("aktiv");
    });
    knopf.classList.add("aktiv");

    document.getElementById("zeitraum-titel").textContent =
        knopf.dataset.titel;

    const daten = await ladeDaten(tage);
    aktualisiereZeitreihe(daten);
}


async function ladePunkte() {
    const antwort = await fetch("/api/data/scatter");
    if (!antwort.ok) {
        throw new Error(`Datenabruf fehlgeschlagen: ${antwort.status}`);
    }
    return antwort.json();
}


function zeichneStreuung(daten) {
    const canvas = document.getElementById("chart-streuung");

    new Chart(canvas, {
        type: "scatter",
        data: {
            datasets: [
                {
                    label: "Tageswerte",
                    data: daten.punkte,
                    backgroundColor: FARBE_PRODUKTION,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (punkt) => {
                            const wert = punkt.raw;
                            return `${wert.datum}: ${wert.y} kWh bei ${wert.x.toFixed(2)} kWh/m²`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: "Einstrahlung kWh/m²" },
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "Produktion kWh" },
                },
            },
        },
    });
}


async function start() {
    try {
        const daten = await ladeDaten(90);
        zeichneZeitreihe(daten);
        const punkte = await ladePunkte();
        zeichneStreuung(punkte);
    } catch (fehler) {
        console.error(fehler);
        return;
    }

    document.querySelectorAll(".zeitraum-knopf").forEach((knopf) => {
        knopf.addEventListener("click", () => {
            wechsleZeitraum(Number(knopf.dataset.tage), knopf).catch(console.error);
        });
    });
}

start();