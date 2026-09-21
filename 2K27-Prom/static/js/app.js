// ================================
// PAGE NAVIGATION
// ================================

function goToRules() {
    const sound = new Audio("/static/assets/prom-whoosh.mp3");

    sound.volume = 0.8;
    sound.play().catch(() => {});

    document.body.classList.add("page-exit");

    setTimeout(() => {
        window.location.href = "/rules";
    }, 500);
}


function goToDetails() {
    document.body.classList.add("page-exit");

    setTimeout(() => {
        window.location.href = "/details";
    }, 500);
}


// ================================
// MULTIPLE GUESTS
// ================================

function goToMultipleGuests() {
    saveDetails();

    sessionStorage.setItem("multipleGuestsAccess", "true");

    window.location.href = "/multiple-guests";
}


function continueWithExtraGuest() {
    sessionStorage.setItem("multipleGuests", "true");

    window.location.href = "/details";
}


function forgetExtraGuest() {
    sessionStorage.removeItem("multipleGuests");

    window.location.href = "/details";
}


// ================================
// FORM MEMORY
// ================================

function saveDetails() {
    const form = document.getElementById("details-form");

    if (!form) return;

    const data = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        phone: document.getElementById("phone").value,
        guestName: document.getElementById("guestName").value
    };

    sessionStorage.setItem(
        "promDetails",
        JSON.stringify(data)
    );
}


function restoreDetails() {
    const saved = sessionStorage.getItem("promDetails");

    if (!saved) return;

    const data = JSON.parse(saved);

    const name = document.getElementById("name");
    const email = document.getElementById("email");
    const phone = document.getElementById("phone");
    const guestName = document.getElementById("guestName");

    if (name) {
        name.value = data.name || "";
    }

    if (email) {
        email.value = data.email || "";
    }

    if (phone) {
        phone.value = data.phone || "";
    }

    if (guestName) {
        guestName.value = data.guestName || "";
    }
}


// ================================
// REVIEW PAGE
// ================================

function loadReviewDetails() {
    const saved = sessionStorage.getItem("promDetails");

    if (!saved) {
        console.log("No saved registration details found.");
        window.location.href = "/details";
        return;
    }

    const data = JSON.parse(saved);

    console.log("Saved registration data:", data);

    const name = document.getElementById("review-name");
    const email = document.getElementById("review-email");
    const phone = document.getElementById("review-phone");
    const guest = document.getElementById("review-guest");

    if (name) {
        name.textContent = data.name || "—";
    }

    if (email) {
        email.textContent = data.email || "—";
    }

    if (phone) {
        phone.textContent = data.phone || "—";
    }

    if (guest) {
        guest.textContent = data.guestName || "No guest";
    }
}


function editDetails() {
    window.location.href = "/details";
}


function submitRegistration() {
    const saved = sessionStorage.getItem("promDetails");

    if (!saved) {
        window.location.href = "/details";
        return;
    }

    const data = JSON.parse(saved);

    const form = document.createElement("form");

    form.method = "POST";
    form.action = "/register";

    const fields = {
        name: data.name || "",
        email: data.email || "",
        phone: data.phone || "",
        guestName: data.guestName || ""
    };

    for (const [key, value] of Object.entries(fields)) {

        const input = document.createElement("input");

        input.type = "hidden";
        input.name = key;
        input.value = value;

        form.appendChild(input);
    }

    document.body.appendChild(form);

    form.submit();
}


function paymentMade() {
    sessionStorage.setItem("paymentSubmitted", "true");

    window.location.href = "/payment-pending";
}

// ================================
// PAGE LOAD
// ================================

window.addEventListener("DOMContentLoaded", () => {

    // Restore details when returning to Page 3
    restoreDetails();


    // Details form
    const form = document.getElementById("details-form");

    if (form) {

        form.addEventListener("input", saveDetails);

        form.addEventListener("submit", (event) => {

            event.preventDefault();

            saveDetails();

            window.location.href = "/review";
        });
    }


    // Review page
    if (window.location.pathname === "/review") {
        loadReviewDetails();
    }


    // Multiple guest page protection
    if (window.location.pathname === "/multiple-guests") {

        const allowed =
            sessionStorage.getItem("multipleGuestsAccess");

        if (allowed !== "true") {

            window.location.href = "/details";

            return;
        }

        sessionStorage.removeItem(
            "multipleGuestsAccess"
        );
    }
});


// ================================
// BACK / FORWARD FIX
// ================================

window.addEventListener("pageshow", () => {
    document.body.classList.remove("page-exit");
});