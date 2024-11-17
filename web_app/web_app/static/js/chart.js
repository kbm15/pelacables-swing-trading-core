// Esperamos la carga completa del documento
document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('btcChart').getContext('2d');

    // Inicialización del gráfico
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],  // Inicialmente vacío, se actualizará con timestamps
            datasets: [{
                label: 'Precio',
                data: [],  // Inicialmente vacío, se actualizará con los precios
                borderColor: 'rgba(0, 123, 255, 1)',
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Tiempo'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Precio'
                    }
                }
            }
        }
    });

    // Establecer la conexión con el servidor WebSocket
    const socket = io.connect("http://localhost:5000");

    // Escuchar los eventos de actualización del gráfico
    socket.on('update_chart', function (data) {
        // Actualizar las etiquetas (timestamps) y los datos del gráfico
        chart.data.labels = data.timestamps;
        chart.data.datasets[0].data = data.prices;

        // Redibujar el gráfico
        chart.update();
    });
});
