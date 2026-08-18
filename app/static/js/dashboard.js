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

async function start() {
    try {
        const daten = await ladeDaten(90);
        zeichneZeitreihe(daten);
    } catch (fehler) {
        console.error(fehler);
    }
}

start();