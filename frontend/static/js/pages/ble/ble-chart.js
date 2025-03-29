/**
 * BLE Chart module for data visualization
 */
export class BleChart {
    constructor(state = {}) {
        this.state = state;
        this.chartInstances = {};
    }

    /**
     * Initialize the chart module
     */
    async initialize() {
        console.log('Initializing BLE Chart module');
        // Any initialization logic
    }

    /**
     * Create a line chart
     * @param {string} elementId - Canvas element ID
     * @param {string} title - Chart title
     * @param {Array} labels - X-axis labels
     * @param {Array} data - Y-axis data
     * @param {string} color - Line color
     * @returns {Chart} - Chart instance
     */
    createLineChart(elementId, title, labels, data, color = 'rgba(75, 192, 192, 1)') {
        const ctx = document.getElementById(elementId);
        if (!ctx) return null;

        const chartConfig = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: data,
                    borderColor: color,
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        };

        const chart = new Chart(ctx, chartConfig);
        this.chartInstances[elementId] = chart;
        
        return chart;
    }

    /**
     * Create a gauge chart
     * @param {string} elementId - Canvas element ID
     * @param {string} title - Chart title
     * @param {number} value - Current value
     * @param {number} min - Minimum value
     * @param {number} max - Maximum value
     * @returns {Chart} - Chart instance
     */
    createGaugeChart(elementId, title, value, min = 0, max = 100) {
        const ctx = document.getElementById(elementId);
        if (!ctx) return null;

        const gaugeNeedle = function(chart) {
            const { ctx, chartArea, scales } = chart;
            const xCenter = (chartArea.left + chartArea.right) / 2;
            const yCenter = chartArea.bottom;
            const needleLength = chartArea.height * 0.8;
            const needleWidth = 5;
            
            // Get current value and convert to angle
            const value = chart.data.datasets[0].data[0];
            const range = scales.r.max - scales.r.min;
            const angleRange = Math.PI;
            const angle = Math.PI - (value - scales.r.min) / range * angleRange;
            
            // Draw needle
            ctx.save();
            ctx.translate(xCenter, yCenter);
            ctx.rotate(angle);
            ctx.beginPath();
            ctx.moveTo(0, -10);
            ctx.lineTo(-needleWidth, 0);
            ctx.lineTo(0, -needleLength);
            ctx.lineTo(needleWidth, 0);
            ctx.fillStyle = 'rgba(255, 99, 132, 1)';
            ctx.fill();
            ctx.restore();
            
            // Draw center circle
            ctx.beginPath();
            ctx.arc(xCenter, yCenter, 10, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fill();
        };

        const chartConfig = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, max - value],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(220, 220, 220, 0.3)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                circumference: 180,
                rotation: 270,
                cutout: '70%',
                plugins: {
                    tooltip: {
                        enabled: false
                    },
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: title,
                        position: 'bottom'
                    },
                    subtitle: {
                        display: true,
                        text: `${value}`,
                        position: 'center',
                        font: {
                            size: 24,
                            weight: 'bold'
                        }
                    }
                }
            },
            plugins: [{
                id: 'gaugeNeedle',
                afterDatasetDraw: gaugeNeedle
            }]
        };

        const chart = new Chart(ctx, chartConfig);
        this.chartInstances[elementId] = chart;
        
        return chart;
    }

    /**
     * Update chart data
     * @param {string} elementId - Canvas element ID
     * @param {Array} newData - New data points
     */
    updateChartData(elementId, newData) {
        const chart = this.chartInstances[elementId];
        if (!chart) return;

        chart.data.datasets[0].data = newData;
        chart.update();
    }

    /**
     * Add a data point to a chart
     * @param {string} elementId - Canvas element ID
     * @param {string|number} label - X-axis label
     * @param {number} value - Y-axis value
     * @param {number} maxPoints - Maximum number of points to show
     */
    addDataPoint(elementId, label, value, maxPoints = 20) {
        const chart = this.chartInstances[elementId];
        if (!chart) return;

        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);

        // Remove old data if exceeding maxPoints
        if (chart.data.labels.length > maxPoints) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update();
    }

    /**
     * Destroy a chart instance
     * @param {string} elementId - Canvas element ID
     */
    destroyChart(elementId) {
        const chart = this.chartInstances[elementId];
        if (chart) {
            chart.destroy();
            delete this.chartInstances[elementId];
        }
    }
}