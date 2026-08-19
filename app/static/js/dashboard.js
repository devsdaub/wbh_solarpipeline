const stil = getComputedStyle(document.documentElement);
const FARBE_PRODUKTION = stil.getPropertyValue("--color-data").trim();
const FARBE_EINSTRAHLUNG = stil.getPropertyValue("--color-data-2").trim();
const FARBE_DRITTE = stil.getPropertyValue("--color-data-3").trim();

let zeitreihe = null;

async function ladeJson(pfad) {
    const antwort = await fetch(pfad);
    if (!antwort.ok) {
        throw new Error(`Datenabruf fehlgeschlagen: ${antwort.status}`);
    }
    return antwort.json();
}

function zeichneZeitreihe(daten) {
    zeitreihe = new Chart(document.getElementById("chart-zeitreihe"), {
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

async function wechsleZeitraum(tage, knopf) {
    document.querySelectorAll(".zeitraum-knopf").forEach((element) => {
        element.classList.remove("aktiv");
    });
    knopf.classList.add("aktiv");
    document.getElementById("zeitraum-titel").textContent = knopf.dataset.titel;

    const daten = await ladeJson(`/api/data/daily?days=${tage}`);
    zeitreihe.data.labels = daten.labels;
    zeitreihe.data.datasets[0].data = daten.produktion;
    zeitreihe.data.datasets[1].data = daten.einstrahlung;
    zeitreihe.update();
}

function zeichneStreuung(daten) {
    new Chart(document.getElementById("chart-streuung"), {
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
                x: { beginAtZero: true, title: { display: true, text: "Einstrahlung kWh/m²" } },
                y: { beginAtZero: true, title: { display: true, text: "Produktion kWh" } },
            },
        },
    });
}

function zeichneMonate(daten) {
    const farben = [FARBE_PRODUKTION, FARBE_EINSTRAHLUNG, FARBE_DRITTE];

    new Chart(document.getElementById("chart-monate"), {
        type: "bar",
        data: {
            labels: daten.labels,
            datasets: daten.reihen.map((reihe, i) => ({
                label: String(reihe.jahr),
                data: reihe.werte,
                backgroundColor: farben[i % farben.length],
                tage: reihe.tage,
            })),
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: (punkt) => {
                            const anzahl = punkt.dataset.tage[punkt.dataIndex];
                            return anzahl ? `${anzahl} Messtage` : "";
                        },
                    },
                },
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: "kWh" } },
            },
        },
    });
}

async function start() {
    try {
        zeichneZeitreihe(await ladeJson("/api/data/daily?days=90"));
        zeichneStreuung(await ladeJson("/api/data/scatter"));
        zeichneMonate(await ladeJson("/api/data/monthly"));
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