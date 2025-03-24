console.log("BLE.js loaded successfully!");

document.addEventListener('DOMContentLoaded', () => {
    console.log("BLE.js: DOM content loaded");

    const scanBtn = document.getElementById('scan-btn');
    if (scanBtn) {
        console.log("BLE.js: Found scan button");
        scanBtn.addEventListener('click', () => {
            console.log("BLE.js: Scan button clicked");
            alert("BLE.js: Scan initiated!");
        });
    } else {
        console.error("BLE.js: Scan button not found");
    }
});