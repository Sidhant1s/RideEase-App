function showSection(section) {
    document.getElementById('booking-section').style.display = section === 'booking' ? 'block' : 'none';
    document.getElementById('rental-section').style.display = section === 'rental' ? 'block' : 'none';
    document.getElementById('booking-form-container').innerHTML = '';
    document.getElementById('rental-form-container').innerHTML = '';
}

function toggleDeliveryOptions() {
    const el = document.getElementById('delivery-options');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function showBookingForm(category) {
    let subcategory = '';
    if (category.startsWith('Delivery-')) {
        subcategory = category.split('-')[1];
        category = 'Delivery';
    }
    const form = `
        <h3>Book a ${category}${subcategory ? ' - ' + subcategory : ''}</h3>
        <form onsubmit="submitBooking(event, '${category}', '${subcategory}')">
            <input type="text" name="user_name" placeholder="Your Name" required><br><br>
            <input type="text" name="contact" placeholder="Contact" required><br><br>
            <input type="date" name="start_date" required> to <input type="date" name="end_date" required><br><br>
            <button type="submit">Book</button>
        </form>
        <div id="booking-message"></div>
    `;
    document.getElementById('booking-form-container').innerHTML = form;
}

function showRentalForm(category) {
    const form = `
        <h3>Rent a ${category}</h3>
        <form onsubmit="submitRental(event, '${category}')">
            <input type="text" name="user_name" placeholder="Your Name" required><br><br>
            <input type="text" name="contact" placeholder="Contact" required><br><br>
            <input type="date" name="start_date" required> to <input type="date" name="end_date" required><br><br>
            <button type="submit">Rent</button>
        </form>
        <div id="rental-message"></div>
    `;
    document.getElementById('rental-form-container').innerHTML = form;
}

async function submitBooking(event, category, subcategory) {
    event.preventDefault();
    const form = event.target;
    // Fetch available vehicles for this category
    let url = `/vehicles?type=booking&category=${category}`;
    if (subcategory) url += `&subcategory=${subcategory}`;
    const vehicles = await fetch(url).then(r => r.json());
    if (!vehicles.length) {
        document.getElementById('booking-message').innerText = 'No vehicles available for this category.';
        return;
    }
    const vehicle = vehicles[0]; // Pick the first available
    const data = {
        user_name: form.user_name.value,
        contact: form.contact.value,
        vehicle_id: vehicle.id,
        start_date: form.start_date.value,
        end_date: form.end_date.value,
        type: 'booking'
    };
    fetch('/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(res => {
        document.getElementById('booking-message').innerText = res.message;
        form.reset();
    });
}

async function submitRental(event, category) {
    event.preventDefault();
    const form = event.target;
    // Fetch available vehicles for this category
    let url = `/vehicles?type=rental&category=${category.replace('Rented ', '')}`;
    const vehicles = await fetch(url).then(r => r.json());
    if (!vehicles.length) {
        document.getElementById('rental-message').innerText = 'No vehicles available for this category.';
        return;
    }
    const vehicle = vehicles[0]; // Pick the first available
    const data = {
        user_name: form.user_name.value,
        contact: form.contact.value,
        vehicle_id: vehicle.id,
        start_date: form.start_date.value,
        end_date: form.end_date.value,
        type: 'rental'
    };
    fetch('/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(res => {
        document.getElementById('rental-message').innerText = res.message;
        form.reset();
    });
}

// Battery settings logic
let batteryThreshold = 20;
let linkedNumber = '';
let userGender = 'male';

function saveBatterySettings(event) {
    event.preventDefault();
    batteryThreshold = parseInt(document.getElementById('battery-threshold').value);
    linkedNumber = document.getElementById('linked-number').value;
    userGender = document.getElementById('user-gender').value;
    document.getElementById('battery-settings-message').innerText = 'Settings saved!';
}

// Battery monitoring
if ('getBattery' in navigator) {
    navigator.getBattery().then(function(battery) {
        function checkBattery() {
            const percent = battery.level * 100;
            if ((userGender === 'female' && percent <= batteryThreshold) ||
                (userGender === 'male' && percent <= batteryThreshold && batteryThreshold > 0)) {
                // Send alert to backend
                fetch('/battery_alert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        number: linkedNumber,
                        percent: percent,
                        gender: userGender
                    })
                });
            }
        }
        battery.addEventListener('levelchange', checkBattery);
        setInterval(checkBattery, 60000); // check every minute
    });
}

// SOS logic
function triggerSOS() {
    // 1. Send alert to backend
    fetch('/sos', { method: 'POST' });

    // 2. Play help voice (in user's language if possible)
    const msg = new SpeechSynthesisUtterance("Help! I need assistance! Please send help immediately!");
    msg.lang = navigator.language || 'en-US';
    window.speechSynthesis.speak(msg);

    // 3. Record audio (5 seconds) and send to backend
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
            const mediaRecorder = new MediaRecorder(stream);
            let audioChunks = [];
            mediaRecorder.ondataavailable = function(e) {
                audioChunks.push(e.data);
            };
            mediaRecorder.onstop = function() {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', audioBlob, 'sos_audio.webm');
                fetch('/sos_audio', { method: 'POST', body: formData });
            };
            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 5000);
        });
    }

    // 4. Record video (5 seconds) and send to backend
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true }).then(function(stream) {
            const mediaRecorder = new MediaRecorder(stream);
            let videoChunks = [];
            mediaRecorder.ondataavailable = function(e) {
                videoChunks.push(e.data);
            };
            mediaRecorder.onstop = function() {
                const videoBlob = new Blob(videoChunks, { type: 'video/webm' });
                const formData = new FormData();
                formData.append('video', videoBlob, 'sos_video.webm');
                fetch('/sos_video', { method: 'POST', body: formData });
            };
            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 5000);
        });
    }

    alert("SOS sent to police station!");
} 